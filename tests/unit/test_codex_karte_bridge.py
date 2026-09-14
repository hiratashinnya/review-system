"""TD-issue-start-452-f17: model-free host transaction/recovery tests."""
from dataclasses import replace
from datetime import timedelta
import json
import os
import subprocess
import unittest
from unittest import mock

from issue_start import codex_karte_bridge as bridge, codex_supervisor as supervisor
from issue_start import codex_supervisor_workspace as workspace, worktree_ledger
from karte import model, paths
from tests.unit import test_codex_supervisor as fixtures


class KarteBridgeTests(unittest.TestCase):
    def setUp(self):
        fixtures.CodexSupervisorTests.setUp(self)
        self.spec = replace(self.spec, role="issue-fixer", round_number=2,
                            task_key="issue_10_fix_r2", finding_ids=("F-10-01",),
                            handoff_path="tmp/_handoff/issue-fixer--issue-10-r2.yaml")
        self.central = paths.karte_path(10, self.main, create_dir=True)
        self.central.write_text(model.dumps(model.Karte(10, findings=[model.Finding(
            "F-10-01", summary="fixture", harm_detail="fixture harm", locus=["seed.txt"],
            evidence="fixture evidence", expected="fixed", recheck="test", rounds=[2],
            disposition="fix-here")])), encoding="utf-8")
        self.baseline = self.central.read_text()
        self.proposal = bridge.proposal_path(self.spec)
        self.handoff = self.workspace / self.spec.handoff_path
        self.published = []

    def entry(self):
        return workspace.one_by_task(self.main, self.spec.task_key)[1]

    def proposal_runner(self, command, **kwargs):
        record = self.entry()["karte_bridge"]
        self.proposal.parent.mkdir(parents=True, exist_ok=True)
        self.proposal.write_text(json.dumps({
            "schema_version": 1, "phase": "diagnosis_proposal", "identity": record["identity"],
            "finding_ids": record["finding_ids"], "karte_sha256": record["before_sha256"],
            "root_cause": "fixture", "change_kind": "logic", "targets": ["seed.txt"],
            "diagnosis": "fixture cause and expected correction",
        }))
        return fixtures.FakeRunner(fixtures.CodexSupervisorTests.success_lines("thread-fixer"))(
            command, **kwargs)

    def launch(self, runner=None, resume=None):
        return supervisor.run_supervised(
            self.spec, prompt="fix fixture", now=fixtures.NOW + timedelta(seconds=1),
            bwrap_executable=self.bwrap, codex_executable=self.codex,
            runner=runner or self.proposal_runner, resume_thread=resume,
            compatibility_checker=lambda _command: None, broker_checker=lambda _command: None)

    def register(self):
        observed = self.launch()
        self.assertEqual(observed.status, "paused_karte_registered")
        return self.entry()["karte_bridge"]

    def fix_runner(self, command, **kwargs):
        (self.workspace / "seed.txt").write_text("fixed\n")
        record = self.entry()["karte_bridge"]
        attempt = record["attempt"]
        self.handoff.parent.mkdir(parents=True, exist_ok=True)
        self.handoff.write_text(json.dumps({
            "schema_version": 1, "phase": "pre_publish", "status": "ready",
            "role": "issue-fixer", "issue": 10, "task_key": self.spec.task_key,
            "branch": self.spec.branch_name, "head_oid": self.spec.expected_oid,
            "result": {"round": 2, "pr_url": "https://github.com/example/repo/pull/9",
                       "finding_ids": ["F-10-01"],
                       "diagnosis": {"root_cause": attempt["root_cause"],
                                     "change_kind": attempt["change_kind"],
                                     "targets": attempt["targets"], "karte_attempt": attempt["number"]},
                       "outcome": "fixed", "changed_files": ["seed.txt"],
                       "tests": {"command": "python3 -m unittest", "result": "pass", "summary": "ok"},
                       "unresolved_findings": [], "out_of_scope_findings": [], "protected_patch": None}}))
        return fixtures.FakeRunner(fixtures.CodexSupervisorTests.success_lines("thread-fixer"))(
            command, **kwargs)

    def publish_runner(self, command, **kwargs):
        self.published.append(command)
        if command[-3:-1] == ["gitgate", "add"]:
            fixtures.git(self.workspace, "add", "seed.txt")
        elif command[-3:-1] == ["gitgate", "commit"]:
            fixtures.git(self.workspace, "commit", "-F", command[-1])
        elif command[-1] == "push":
            branch = self.spec.branch_name
            fixtures.git(self.workspace, "config", f"branch.{branch}.remote", "origin")
            fixtures.git(self.workspace, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")
            fixtures.git(self.workspace, "update-ref", f"refs/remotes/origin/{branch}",
                         fixtures.git(self.workspace, "rev-parse", "HEAD"))
        else:
            self.fail(f"unexpected external action: {command}")
        return subprocess.CompletedProcess(command, 0, "ok\n", "")

    def publish(self, action, args=()):
        return supervisor.execute_publish_action(self.spec, action=action,
                                                 action_args=args, runner=self.publish_runner)

    def ready_to_push(self):
        self.register()
        observed = self.launch(self.fix_runner, resume="thread-fixer")
        self.assertEqual(observed.status, "succeeded")
        self.publish("gitgate.add", ("seed.txt",))
        message = self.workspace / "tmp/message.txt"
        message.write_text("fix fixture\n")
        self.publish("gitgate.commit", (str(message),))

    def test_normal_proposal_append_same_thread_push_close_final(self):
        self.ready_to_push()
        self.publish("gitgate.push")
        self.assertEqual(json.loads(self.handoff.read_text())["phase"], "pre_publish")
        self.assertFalse(model.parse(self.central.read_text()).results)
        self.publish("karte.close-attempt")
        final = json.loads(self.handoff.read_text())
        self.assertEqual((final["phase"], final["status"]), ("final", "fixed"))
        karte = model.parse(self.central.read_text())
        self.assertEqual((len(karte.attempts), len(karte.results)), (1, 1))
        self.assertEqual(karte.results[0].touched, ["seed.txt"])
        before = self.central.read_bytes()
        self.publish("karte.close-attempt")
        self.assertEqual(self.central.read_bytes(), before)
        self.assertEqual(len(self.published), 3)

    def test_append_crash_before_and_after_atomic_replace_is_idempotent(self):
        original = bridge._replace
        for point in ("before", "after"):
            with self.subTest(point=point):
                # Each subtest owns an independent fixture/identity.
                if point == "after":
                    self.doCleanups()
                    self.setUp()
                def crash(path, text):
                    if point == "after":
                        original(path, text)
                    raise RuntimeError("append crash")
                with mock.patch.object(bridge, "_replace", side_effect=crash):
                    with self.assertRaisesRegex(RuntimeError, "append crash"):
                        self.launch()
                self.assertEqual(self.entry()["supervisor_attempts"][-1]["state"], "diagnosis_ready")
                bridge.register_diagnosis(self.spec, git_snapshot=supervisor._publish_git_snapshot(self.workspace))
                bridge.register_diagnosis(self.spec, git_snapshot=supervisor._publish_git_snapshot(self.workspace))
                self.assertEqual(len(model.parse(self.central.read_text()).attempts), 1)

    def test_diagnosis_dirty_tree_never_registers(self):
        def dirty(command, **kwargs):
            value = self.proposal_runner(command, **kwargs)
            (self.workspace / "seed.txt").write_text("too soon")
            return value
        with self.assertRaisesRegex(bridge.KarteBridgeError, "EDIT_BEFORE_DIAGNOSIS"):
            self.launch(dirty)
        self.assertEqual(self.central.read_text(), self.baseline)

    def test_proposal_schema_identity_digest_targets_and_hardlink_rejected(self):
        cases = {"identity": {}, "finding_ids": ["F-10-99"], "karte_sha256": "0" * 64,
                 "phase": "pre_publish", "targets": ["../outside::symbol"]}
        for key, value in cases.items():
            with self.subTest(key=key):
                if self.entry_exists():
                    self.doCleanups()
                    self.setUp()
                def invalid(command, **kwargs):
                    output = self.proposal_runner(command, **kwargs)
                    document = json.loads(self.proposal.read_text())
                    document[key] = value
                    self.proposal.write_text(json.dumps(document))
                    return output
                with self.assertRaises(bridge.KarteBridgeError):
                    self.launch(invalid)
                self.assertEqual(self.central.read_text(), self.baseline)
        self.doCleanups()
        self.setUp()
        def hardlinked(command, **kwargs):
            output = self.proposal_runner(command, **kwargs)
            os.link(self.proposal, self.proposal.with_suffix(".alias"))
            return output
        with self.assertRaisesRegex(bridge.KarteBridgeError, "FILE_INVALID"):
            self.launch(hardlinked)

    def entry_exists(self):
        return bool(worktree_ledger.read_ledger(self.main)["entries"])

    def test_registered_stale_karte_proposal_and_attempt_replay_rejected(self):
        self.register()
        original = self.central.read_text()
        self.central.write_text(original + "\n")
        with self.assertRaisesRegex(bridge.KarteBridgeError, "STALE_DIGEST"):
            self.launch(self.fix_runner, resume="thread-fixer")
        self.central.write_text(original)
        proposal = json.loads(self.proposal.read_text())
        proposal["diagnosis"] = "substitute"
        self.proposal.write_text(json.dumps(proposal))
        with self.assertRaisesRegex(bridge.KarteBridgeError, "PROPOSAL_REPLAY"):
            bridge.verify_registered(self.entry())

    def test_fresh_or_different_thread_cannot_consume_registered_pause(self):
        self.register()
        with self.assertRaisesRegex(workspace.SupervisorWorkspaceError, "RESUME_REQUIRED"):
            workspace.reserve_launch_attempt(
                repo_root=self.main, workspace=self.workspace, issue=10, round_number=2,
                repository=self.spec.repository, branch_name=self.spec.branch_name,
                expected_oid=self.spec.expected_oid, role=self.spec.role, task_key=self.spec.task_key,
                handoff_path=self.spec.handoff_path, protected_paths=self.spec.protected_paths, attempt_id="fresh",
                resume_thread=None, owner_pid=os.getpid(), owner_start_token="1",
                now=fixtures.NOW, lease_seconds=60)
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "RESUME_STATE_INVALID"):
            self.launch(self.fix_runner, resume="other-thread")

    def test_diagnosis_mount_only_proposal_is_writable(self):
        command = supervisor.build_codex_command(
            self.spec, bwrap_executable=self.bwrap, codex_executable=self.codex, diagnosis_only=True)
        triplets = list(zip(command, command[1:], command[2:]))
        self.assertIn(("--ro-bind", str(self.workspace), str(self.workspace)), triplets)
        self.assertIn(("--bind", str(self.proposal.parent), str(self.proposal.parent)), triplets)
        self.assertNotIn(("--bind", str(self.workspace), str(self.workspace)), triplets)

    def test_canonical_resume_consumes_registered_pause_and_rechecks_before_spawn(self):
        self.register()
        entry = self.entry()
        owner = os.getpid()
        token = supervisor._process_start_token(owner)
        reserved, thread = workspace.reserve_canonical_launch_attempt(
            repo_root=self.main, ledger_entry_id=entry["entry_id"], workspace=self.workspace,
            issue=10, round_number=2, repository=self.spec.repository, branch_name=self.spec.branch_name,
            expected_oid=self.spec.expected_oid, role=self.spec.role, task_key=self.spec.task_key,
            handoff_path=self.spec.handoff_path, protected_paths=self.spec.protected_paths,
            intent_digest="a" * 64, attempt_id="resume-canonical", mode="resume",
            owner_pid=owner, owner_start_token=token, now=fixtures.NOW, lease_seconds=60)
        self.assertEqual(thread, "thread-fixer")
        self.assertEqual(reserved["entry_id"], entry["entry_id"])
        self.central.write_text(self.central.read_text() + "\n")
        with self.assertRaisesRegex(bridge.KarteBridgeError, "STALE_DIGEST"):
            workspace.verify_canonical_launch_reservation(
                repo_root=self.main, ledger_entry_id=entry["entry_id"], attempt_id="resume-canonical",
                intent_digest="a" * 64, owner_pid=owner, owner_start_token=token,
                workspace=self.workspace, repository=self.spec.repository,
                branch_name=self.spec.branch_name, expected_oid=self.spec.expected_oid)

    def test_malformed_duplicate_key_and_symlink_proposals_are_rejected(self):
        for content in ("{", '{"schema_version":1,"schema_version":1}', "symlink"):
            with self.subTest(content=content):
                if self.entry_exists():
                    self.doCleanups()
                    self.setUp()
                def invalid(command, **kwargs):
                    output = self.proposal_runner(command, **kwargs)
                    if content == "symlink":
                        self.proposal.unlink()
                        self.proposal.symlink_to(self.central)
                    else:
                        self.proposal.write_text(content)
                    return output
                with self.assertRaises((bridge.KarteBridgeError, workspace.SupervisorWorkspaceError)):
                    self.launch(invalid)
                self.assertEqual(self.central.read_text(), self.baseline)

    def test_active_diagnosis_probe_requires_code_read_only_and_proposal_write(self):
        observed = {
            "workspace": {"read": True, "write": False, "exec": True},
            "proposal": {"read": True, "write": True, "exec": True},
            **{key: {"read": False, "write": False, "exec": False}
               for key in ("runtime", "runtime_auth", "host_auth", "install")},
            "network": {"tcp": False, "unix": False},
            "environment": {"HOME": None, "CODEX_HOME": None, "TMPDIR": None, "PATH": "/usr/bin:/bin"},
            "inherited_fds": [], "proc": {"self_status": True, "pid1": True}}
        supervisor._validate_active_boundary_probe(json.dumps(observed), 0,
            workspace=self.workspace, runtime_home=self.main, diagnosis_only=True)
        for key, value in (("workspace", True), ("proposal", False)):
            bad = json.loads(json.dumps(observed))
            bad[key]["write"] = value
            with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PROBE_BOUNDARY_MISMATCH"):
                supervisor._validate_active_boundary_probe(json.dumps(bad), 0,
                    workspace=self.workspace, runtime_home=self.main, diagnosis_only=True)

    def test_handoff_diagnosis_substitution_is_rejected(self):
        self.register()
        def substituted(command, **kwargs):
            output = self.fix_runner(command, **kwargs)
            document = json.loads(self.handoff.read_text())
            document["result"]["diagnosis"]["karte_attempt"] = 99
            self.handoff.write_text(json.dumps(document))
            return output
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "KARTE_HANDOFF_MISMATCH"):
            self.launch(substituted, resume="thread-fixer")

    def test_push_crash_recovery_does_not_repeat_push_or_finalize_early(self):
        self.ready_to_push()
        handoff = json.loads(self.handoff.read_text())
        supervisor._reserve_publish_action(
            self.spec, action="gitgate.push", sequence=supervisor._publish_sequence(self.spec.role, handoff),
            snapshot=supervisor._publish_git_snapshot(self.workspace), initial_head_oid=handoff["head_oid"],
            action_args_sha256=supervisor._action_args_sha256(()),
            handoff_sha256=supervisor._canonical_json_sha256(handoff), handoff_document=handoff,
            now=fixtures.NOW)
        self.publish_runner(["python3", "-m", "gitgate", "push"])
        self.expire_publish()
        self.publish("gitgate.push")
        self.assertEqual(len(self.published), 3)
        self.assertEqual(json.loads(self.handoff.read_text())["phase"], "pre_publish")
        self.publish("karte.close-attempt")
        self.assertEqual(len(model.parse(self.central.read_text()).results), 1)

    def expire_publish(self):
        def mutate(document):
            entry = next(item for item in document["entries"] if item.get("task_key") == self.spec.task_key)
            entry["publish_attempts"][-1].update(owner_pid=99999999, owner_start_token="1",
                                                lease_expires_at="2026-08-30T00:00:00Z")
        worktree_ledger.update_ledger(self.main, mutate)

    def test_close_and_final_crashes_converge_to_single_result(self):
        for point in ("before-replace", "after-replace", "after-close", "before-final", "after-final"):
            with self.subTest(point=point):
                if self.entry_exists():
                    self.doCleanups()
                    self.setUp()
                self.ready_to_push()
                self.publish("gitgate.push")
                if point in {"before-replace", "after-replace"}:
                    original = bridge._replace
                    def crash(path, text):
                        if point == "after-replace":
                            original(path, text)
                        raise RuntimeError(point)
                    patch = mock.patch.object(bridge, "_replace", side_effect=crash)
                elif point == "after-close":
                    original = bridge.close_attempt
                    def crash(*args, **kwargs):
                        original(*args, **kwargs)
                        raise RuntimeError(point)
                    patch = mock.patch.object(bridge, "close_attempt", side_effect=crash)
                else:
                    original = supervisor._write_final_handoff
                    def crash(*args, **kwargs):
                        if point == "after-final":
                            original(*args, **kwargs)
                        raise RuntimeError(point)
                    patch = mock.patch.object(supervisor, "_write_final_handoff", side_effect=crash)
                with patch, self.assertRaisesRegex(RuntimeError, point):
                    self.publish("karte.close-attempt")
                self.publish("karte.close-attempt")
                self.publish("karte.close-attempt")
                self.assertEqual(len(model.parse(self.central.read_text()).results), 1)
                self.assertEqual(json.loads(self.handoff.read_text())["status"], "fixed")
                self.assertEqual(len(self.published), 3)

    def test_final_and_result_tamper_and_close_arguments_fail_closed(self):
        self.ready_to_push()
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PUBLISH_ORDER_INVALID"):
            self.publish("karte.close-attempt")
        self.publish("gitgate.push")
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PUBLISH_ARGS_INVALID"):
            self.publish("karte.close-attempt", ("--attempt", "99"))
        self.publish("karte.close-attempt")
        final = json.loads(self.handoff.read_text())
        final["tests"]["summary"] = "tampered"
        self.handoff.write_text(json.dumps(final))
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "FINAL_INTENT_MISMATCH"):
            self.publish("karte.close-attempt")
        self.central.write_text(self.central.read_text() + "\n")
        with self.assertRaisesRegex(bridge.KarteBridgeError, "STALE_DIGEST"):
            self.publish("karte.close-attempt")

    def test_writer_lock_rejects_symlink_and_hardlink(self):
        lock = self.central.parent / ".writer.lock"
        for alias in ("symlink", "hardlink"):
            with self.subTest(alias=alias):
                if alias == "symlink":
                    lock.symlink_to(self.central)
                else:
                    os.link(self.central, lock)
                with self.assertRaises((OSError, paths.KartePathError)):
                    with paths.writer_lock(self.main):
                        self.fail("unsafe lock accepted")
                lock.unlink()
