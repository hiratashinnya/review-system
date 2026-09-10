from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from issue_start import codex_launch_control as control
from issue_start import codex_launch_intent, codex_supervisor, worktree_ledger


ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 9, 1, 2, 3, tzinfo=timezone.utc)


class LaunchControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.main = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-b", "main", str(self.main)], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(self.main), "config", "user.email", "t@example.com"],
                       check=True)
        subprocess.run(["git", "-C", str(self.main), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.main), "remote", "add", "origin",
                        "https://github.com/example/project.git"], check=True)
        for relative in ("issue_start", ".codex/agents", ".ai/agents"):
            (self.main / relative).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "issue_start/managed-entrypoints-v2.json",
                     self.main / "issue_start/managed-entrypoints-v2.json")
        for role in ("issue-implementer", "issue-fixer"):
            (self.main / f".codex/agents/{role}.toml").write_text("name='x'\n", encoding="utf-8")
            (self.main / f".ai/agents/{role}.md").write_text("# x\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.main), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.main), "commit", "-m", "base"], check=True,
                       capture_output=True)
        (self.main / ".worktrees").mkdir()
        self.workspace = self.main / ".worktrees/issue-10"
        subprocess.run(["git", "-C", str(self.main), "worktree", "add", "-b", "issue-10",
                        str(self.workspace)], check=True, capture_output=True)
        self.inputs = Path(self.temp.name) / "inputs"
        self.inputs.mkdir(mode=0o700)
        self.issue_file = self.inputs / "issue.json"
        self._write_source(self.issue_file, {
            "schema_version": "codex-issue-snapshot/2", "repository": "example/project",
            "issue": 10, "url": "https://github.com/example/project/issues/10",
            "title": "Issue ten", "body": "Body as captured", "acceptance_criteria": ["AC-1"],
            "capture": {"captured_at": "2026-09-08T23:00:00Z",
                        "captured_by": "capture-operator", "capture_method": "github-api"},
        })

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write_source(path: Path, value: object):
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o600)

    def request(self, **changes):
        values = dict(issue=10, role="issue-implementer", change_plan_id="cp-10",
                      workspace=self.workspace, issue_snapshot_file=self.issue_file,
                      approved_by="owner", protected_paths=())
        values.update(changes)
        return control.IssueRequest(**values)

    def _manifest_patch(self):
        original = codex_launch_intent._validate_manifest

        def validate(value):
            with mock.patch.object(codex_launch_intent, "_stable_executable_evidence",
                                   side_effect=[("/usr/bin/bwrap", {}), ("/usr/bin/codex", {})]):
                return original(value)
        return mock.patch.object(control.codex_launch_intent, "_validate_manifest",
                                 side_effect=validate)

    def issue(self, request=None, now=NOW):
        with self._manifest_patch():
            return control.issue(request or self.request(), now=now)

    def test_issues_plan_sources_and_complete_canonical_entry(self):
        plan = self.issue()
        entry = worktree_ledger.read_ledger(self.main)["entries"][0]
        self.assertEqual(entry["platform"], "codex-supervisor")
        self.assertEqual(entry["issuance_status"], "complete")
        self.assertEqual(entry["change_plan_id"], "cp-10")
        self.assertEqual(plan["ledger_entry_id"], entry["entry_id"])
        self.assertEqual(plan["owner_approval"], {
            "status": "approved", "actor": "owner", "recorded_at": "2026-09-09T01:02:03Z",
        })
        self.assertEqual(plan["issue_source"]["provenance"], {
            "source_type": "github-issue-snapshot",
            "captured_at": "2026-09-08T23:00:00Z",
            "captured_by": "capture-operator", "capture_method": "github-api",
        })
        root = self.main / "tmp/_codex_control"
        self.assertEqual(root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((root / "sources/cp-10-issue.json").stat().st_mode & 0o777, 0o600)
        self.assertTrue((root / "change-plans/cp-10.json").is_file())

    def test_retry_at_different_time_is_idempotent(self):
        first = self.issue()
        second = self.issue(now=datetime(2026, 9, 10, tzinfo=timezone.utc))
        self.assertEqual(first, second)
        self.assertEqual(second["issue_source"]["provenance"]["captured_at"],
                         "2026-09-08T23:00:00Z")
        self.assertEqual(second["owner_approval"]["recorded_at"],
                         "2026-09-09T01:02:03Z")
        self.assertEqual(len(worktree_ledger.read_ledger(self.main)["entries"]), 1)

    def test_legacy_or_invalid_capture_provenance_is_rejected(self):
        original = json.loads(self.issue_file.read_text())
        variants = []
        legacy = dict(original)
        legacy["schema_version"] = "codex-issue-snapshot/1"
        legacy.pop("capture")
        variants.append(legacy)
        for capture in (
                {"captured_at": "2026-09-08T23:00:00Z", "captured_by": "operator"},
                {"captured_at": "not-a-time", "captured_by": "operator",
                 "capture_method": "github-api"},
                {"captured_at": "2026-09-08T23:00:00Z", "captured_by": "operator",
                 "capture_method": "free-form"},
                {"captured_at": "2026-09-10T00:00:00Z", "captured_by": "operator",
                 "capture_method": "github-api"},
                {"captured_at": "2026-09-08T23:00:00Z", "captured_by": "bad\nactor",
                 "capture_method": "github-api"},
        ):
            changed = dict(original)
            changed["capture"] = capture
            variants.append(changed)
        for value in variants:
            with self.subTest(value=value):
                self._write_source(self.issue_file, value)
                with self.assertRaises(control.LaunchControlError):
                    self.issue()
        self._write_source(self.issue_file, original)

    def test_unsafe_tmp_ancestors_are_rejected_before_private_publication(self):
        tmp = self.main / "tmp"
        tmp.mkdir()
        tmp.chmod(0o777)
        with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_ROOT_INVALID"):
            self.issue()
        self.assertFalse((tmp / "_codex_control").exists())
        tmp.chmod(0o770)
        self.main.chmod(0o755)
        with mock.patch.object(control.codex_launch_intent,
                               "_group_is_exclusive_to_current_uid", return_value=False):
            with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_ROOT_INVALID"):
                control._open_control_tree(self.main)
        self.assertFalse((tmp / "_codex_control").exists())

    def test_control_directory_identity_swap_fails_without_redirected_publication(self):
        outside = self.inputs / "outside"
        outside.mkdir(mode=0o700)
        detached = self.inputs / "detached-control"
        original_assert = control._ControlTree.assert_attached
        calls = 0

        def swap(tree):
            nonlocal calls
            calls += 1
            if calls == 3:
                canonical = self.main / "tmp/_codex_control"
                canonical.rename(detached)
                canonical.symlink_to(outside, target_is_directory=True)
            return original_assert(tree)

        with mock.patch.object(control._ControlTree, "assert_attached", swap):
            with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_ROOT_CHANGED"):
                self.issue()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list((detached / "sources").iterdir()), [])
        self.assertEqual(list((detached / "change-plans").iterdir()), [])

    def test_tmp_directory_identity_swap_fails_without_redirected_publication(self):
        outside = self.inputs / "outside-tmp"
        outside.mkdir(mode=0o700)
        detached = self.inputs / "detached-tmp"
        original_assert = control._ControlTree.assert_attached
        calls = 0

        def swap(tree):
            nonlocal calls
            calls += 1
            if calls == 3:
                canonical = self.main / "tmp"
                canonical.rename(detached)
                canonical.symlink_to(outside, target_is_directory=True)
            return original_assert(tree)

        with mock.patch.object(control._ControlTree, "assert_attached", swap):
            with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_ROOT_CHANGED"):
                self.issue()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list((detached / "_codex_control/sources").iterdir()), [])
        self.assertEqual(list((detached / "_codex_control/change-plans").iterdir()), [])

    def test_conflicting_published_leaf_is_no_clobber_rejected(self):
        sources = self.main / "tmp/_codex_control/sources"
        plans = self.main / "tmp/_codex_control/change-plans"
        sources.mkdir(parents=True, mode=0o700)
        plans.mkdir(mode=0o700)
        (self.main / "tmp").chmod(0o755)
        (self.main / "tmp/_codex_control").chmod(0o700)
        sources.chmod(0o700)
        plans.chmod(0o700)
        collision = sources / "cp-10-issue.json"
        collision.write_bytes(b"different")
        collision.chmod(0o600)
        with self.assertRaisesRegex(control.LaunchControlError,
                                    "CONTROL_ISSUE_PUBLICATION_INVALID"):
            self.issue()
        self.assertEqual(collision.read_bytes(), b"different")
        self.assertFalse((plans / "cp-10.json").exists())

    def test_publication_failure_cleans_unique_temp_in_same_directory(self):
        with self._manifest_patch(), mock.patch.object(
                control.os, "link", side_effect=OSError(errno.EIO, "injected")):
            with self.assertRaisesRegex(control.LaunchControlError,
                                        "CONTROL_ISSUE_PUBLICATION_INVALID"):
                control.issue(self.request(), now=NOW)
        sources = self.main / "tmp/_codex_control/sources"
        self.assertEqual(list(sources.iterdir()), [])

    def test_post_link_directory_swap_removes_only_our_published_inode(self):
        outside = self.inputs / "outside-source"
        outside.mkdir(mode=0o700)
        detached = self.inputs / "detached-source"
        original_assert = control._ControlTree.assert_attached
        calls = 0

        def swap_after_link(tree):
            nonlocal calls
            calls += 1
            if calls == 5:
                canonical = self.main / "tmp/_codex_control/sources"
                canonical.rename(detached)
                canonical.symlink_to(outside, target_is_directory=True)
            return original_assert(tree)

        with mock.patch.object(control._ControlTree, "assert_attached", swap_after_link):
            with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_ROOT_CHANGED"):
                self.issue()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list(detached.iterdir()), [])

    def _assert_exact_retry_repairs_directory_barrier(
            self, *, directory_name: str, initial_failure: str) -> None:
        directory = self.main / f"tmp/_codex_control/{directory_name}"
        leaf = "cp-10-issue.json" if directory_name == "sources" else "cp-10.json"
        reason = ("CONTROL_ISSUE_PUBLICATION_INVALID" if directory_name == "sources"
                  else "CONTROL_PLAN_PUBLICATION_INVALID")
        original_fsync = os.fsync
        original_unlink = os.unlink
        injected = False

        def fail_initial_fsync_once(fd):
            nonlocal injected
            target = os.readlink(f"/proc/self/fd/{fd}")
            if target.endswith(f"/_codex_control/{directory_name}") and not injected:
                injected = True
                raise OSError(errno.EIO, "injected initial directory fsync failure")
            return original_fsync(fd)

        def fail_initial_unlink_once(path, *args, **kwargs):
            nonlocal injected
            if (isinstance(path, str) and path.startswith(f".{leaf}.new.")
                    and not injected):
                injected = True
                raise OSError(errno.EIO, "injected post-publication unlink failure")
            return original_unlink(path, *args, **kwargs)

        fault = (mock.patch.object(control.os, "fsync", side_effect=fail_initial_fsync_once)
                 if initial_failure == "fsync"
                 else mock.patch.object(control.os, "unlink",
                                        side_effect=fail_initial_unlink_once))
        with self._manifest_patch(), fault:
            with self.assertRaisesRegex(control.LaunchControlError, reason):
                control.issue(self.request(), now=NOW)
        self.assertTrue(injected)
        self.assertTrue((directory / leaf).is_file())

        retry_directory_fsyncs = 0

        def fail_retry_directory_fsync(fd):
            nonlocal retry_directory_fsyncs
            target = os.readlink(f"/proc/self/fd/{fd}")
            if target.endswith(f"/_codex_control/{directory_name}"):
                retry_directory_fsyncs += 1
                raise OSError(errno.EIO, "injected retry directory fsync failure")
            return original_fsync(fd)

        with self._manifest_patch(), mock.patch.object(
                control.os, "fsync", side_effect=fail_retry_directory_fsync):
            with self.assertRaisesRegex(control.LaunchControlError, reason):
                control.issue(self.request(), now=datetime(2026, 9, 10, tzinfo=timezone.utc))
        self.assertEqual(retry_directory_fsyncs, 1)
        self.assertTrue((directory / leaf).is_file())

        self.issue(now=datetime(2026, 9, 11, tzinfo=timezone.utc))
        self.assertTrue((directory / leaf).is_file())
        self.assertTrue((self.main / "tmp/_codex_control/change-plans/cp-10.json").is_file())

    def test_source_directory_fsync_failure_retry_repairs_barrier(self):
        self._assert_exact_retry_repairs_directory_barrier(
            directory_name="sources", initial_failure="fsync")

    def test_source_post_publication_unlink_failure_retry_repairs_barrier(self):
        self._assert_exact_retry_repairs_directory_barrier(
            directory_name="sources", initial_failure="unlink")

    def test_plan_directory_fsync_failure_retry_repairs_barrier(self):
        self._assert_exact_retry_repairs_directory_barrier(
            directory_name="change-plans", initial_failure="fsync")

    def test_plan_post_publication_unlink_failure_retry_repairs_barrier(self):
        self._assert_exact_retry_repairs_directory_barrier(
            directory_name="change-plans", initial_failure="unlink")

    def test_plan_publication_crash_leaves_complete_entry_and_retry_repairs(self):
        original = control._write_once_or_exact

        def fail_plan(directory, name, raw, *, reason):
            if directory.name == "change-plans":
                raise control.LaunchControlError("TEST_CRASH")
            return original(directory, name, raw, reason=reason)

        with self._manifest_patch(), mock.patch.object(control, "_write_once_or_exact",
                                                       side_effect=fail_plan):
            with self.assertRaisesRegex(control.LaunchControlError, "TEST_CRASH"):
                control.issue(self.request(), now=NOW)
        entry = worktree_ledger.read_ledger(self.main)["entries"][0]
        self.assertEqual(entry["issuance_status"], "complete")
        self.assertFalse((self.main / "tmp/_codex_control/change-plans/cp-10.json").exists())
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                cwd=self.workspace,
            )
        self.issue(now=datetime(2026, 9, 10, tzinfo=timezone.utc))
        self.assertTrue((self.main / "tmp/_codex_control/change-plans/cp-10.json").is_file())

    def test_source_publication_crash_leaves_pending_entry_and_retry_repairs(self):
        with self._manifest_patch(), mock.patch.object(
                control, "_write_once_or_exact",
                side_effect=control.LaunchControlError("TEST_SOURCE_CRASH")):
            with self.assertRaisesRegex(control.LaunchControlError, "TEST_SOURCE_CRASH"):
                control.issue(self.request(), now=NOW)
        entry = worktree_ledger.read_ledger(self.main)["entries"][0]
        self.assertEqual(entry["issuance_status"], "pending")
        self.assertFalse((self.main / "tmp/_codex_control/change-plans/cp-10.json").exists())
        self.issue(now=datetime(2026, 9, 10, tzinfo=timezone.utc))
        entry = worktree_ledger.read_ledger(self.main)["entries"][0]
        self.assertEqual(entry["issuance_status"], "complete")

    def test_runtime_loader_accepts_issuer_fixture(self):
        self.issue()
        original = codex_launch_intent._validate_manifest

        def validate(value):
            with mock.patch.object(codex_launch_intent, "_stable_executable_evidence",
                                   side_effect=[("/usr/bin/bwrap", {}), ("/usr/bin/codex", {})]):
                return original(value)
        with mock.patch.object(codex_launch_intent, "_validate_manifest", side_effect=validate):
            intent = codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                cwd=self.workspace,
            )
        self.assertEqual(intent.issue, 10)
        self.assertEqual(intent.ledger_entry_id,
                         worktree_ledger.read_ledger(self.main)["entries"][0]["entry_id"])

    def test_runtime_loader_rejects_plan_capture_that_differs_from_snapshot_v2(self):
        self.issue()
        plan_path = self.main / "tmp/_codex_control/change-plans/cp-10.json"
        plan = json.loads(plan_path.read_text())
        plan["issue_source"]["provenance"]["captured_by"] = "different-captor"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_path.chmod(0o600)
        with self._manifest_patch():
            with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                        "ISSUE_SOURCE_INVALID"):
                codex_launch_intent.load_launch_intent(
                    codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                    cwd=self.workspace,
                )

    def test_issuer_fixture_reaches_supervisor_run_pre_stage(self):
        self.issue()
        sentinel = object()
        with self._manifest_patch(), mock.patch.object(
                codex_supervisor, "run_supervised", return_value=sentinel) as run:
            result = codex_supervisor.execute_launch_request(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                mode="run", now=NOW, cwd=self.workspace,
            )
        self.assertIs(result, sentinel)
        spec = run.call_args.args[0]
        self.assertEqual(spec.workspace, self.workspace)
        self.assertEqual(spec.task_key, "issue_10")
        entry = worktree_ledger.read_ledger(self.main)["entries"][0]
        with self._manifest_patch():
            reloaded = codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(
                    10, "issue-implementer", "cp-10"), cwd=self.workspace,
            )
        self.assertEqual(entry["launch_intent_digest"],
                         codex_launch_intent.intent_digest(reloaded))
        self.assertEqual(entry["supervisor_attempts"][-1]["state"], "reserved")

    def test_pending_entry_is_rejected_by_runtime_loader(self):
        self.issue()
        ledger = worktree_ledger.read_ledger(self.main)
        ledger["entries"][0]["issuance_status"] = "pending"
        worktree_ledger.update_ledger(self.main, lambda doc: doc.update(ledger))
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CANONICAL_LEDGER_MISMATCH"):
            codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                cwd=self.workspace,
            )

    def test_post_issuance_source_and_plan_tamper_fail_closed(self):
        self.issue()
        source = self.main / "tmp/_codex_control/sources/cp-10-issue.json"
        original = source.read_bytes()
        source.write_bytes(original + b" ")
        source.chmod(0o600)
        with self._manifest_patch(), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, "ISSUE_SOURCE_INVALID"):
            codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                cwd=self.workspace,
            )
        source.write_bytes(original)
        source.chmod(0o600)
        plan_path = self.main / "tmp/_codex_control/change-plans/cp-10.json"
        plan = json.loads(plan_path.read_text())
        plan["protected_plan"] = [{"path": ".codex/hooks.json", "base_sha256": "a" * 64}]
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_path.chmod(0o600)
        with self._manifest_patch(), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, "CANONICAL_LEDGER_MISMATCH"):
            codex_launch_intent.load_launch_intent(
                codex_launch_intent.LaunchRequest(10, "issue-implementer", "cp-10"),
                cwd=self.workspace,
            )

    def test_different_plan_id_or_content_collides_with_active_workspace(self):
        self.issue()
        with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_LEDGER_COLLISION"):
            self.issue(self.request(change_plan_id="other"))
        changed = json.loads(self.issue_file.read_text())
        changed["body"] = "changed"
        self._write_source(self.issue_file, changed)
        with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_LEDGER_COLLISION"):
            self.issue()

    def test_exact_retry_rejects_an_additional_active_identity_collision(self):
        self.issue()

        def add_conflict(document):
            original = document["entries"][0]
            conflict = dict(original)
            conflict.update({
                "entry_id": "wl-111111111111", "change_plan_id": "other-plan",
                "issuance_spec_digest": "a" * 64,
            })
            document["entries"].append(conflict)

        worktree_ledger.update_ledger(self.main, add_conflict)
        with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_LEDGER_COLLISION"):
            self.issue()

    def test_exact_retry_revalidates_canonical_entry_fields_not_only_stored_digest(self):
        self.issue()

        def tamper(document):
            document["entries"][0]["approved_by"] = "different-owner"

        worktree_ledger.update_ledger(self.main, tamper)
        with self.assertRaisesRegex(control.LaunchControlError, "CONTROL_LEDGER_COLLISION"):
            self.issue()

    def test_fixer_derives_finding_ids_and_exact_round(self):
        karte = self.inputs / "karte.json"
        self._write_source(karte, {
            "schema_version": "codex-karte-snapshot/2", "issue": 10, "round": 2,
            "open_findings": [{"id": "F-10-01", "status": "open", "summary": "Fix it"}],
            "capture": {"captured_at": "2026-09-08T23:30:00Z",
                        "captured_by": "karte-exporter", "capture_method": "karte-cli"},
        })
        plan = self.issue(self.request(role="issue-fixer", change_plan_id="cp-fix",
                                       fixer_round=2, karte_snapshot_file=karte))
        self.assertEqual(plan["finding_ids"], ["F-10-01"])
        self.assertEqual(plan["fixer_round"], 2)
        self.assertEqual(plan["karte_source"]["provenance"], {
            "source_type": "finding-karte-snapshot",
            "captured_at": "2026-09-08T23:30:00Z",
            "captured_by": "karte-exporter", "capture_method": "karte-cli",
        })

    def test_empty_ac_wrong_repo_and_karte_mismatch_fail_closed(self):
        value = json.loads(self.issue_file.read_text())
        for field, replacement in (("acceptance_criteria", []), ("repository", "other/repo")):
            changed = dict(value)
            changed[field] = replacement
            self._write_source(self.issue_file, changed)
            with self.assertRaises(control.LaunchControlError):
                self.issue()
        self._write_source(self.issue_file, value)
        karte = self.inputs / "karte.json"
        self._write_source(karte, {"schema_version": "codex-karte-snapshot/2", "issue": 10,
                                   "round": 3, "open_findings": [],
                                   "capture": {"captured_at": "2026-09-08T23:30:00Z",
                                               "captured_by": "karte-exporter",
                                               "capture_method": "karte-cli"}})
        with self.assertRaises(control.LaunchControlError):
            self.issue(self.request(role="issue-fixer", change_plan_id="fix", fixer_round=2,
                                    karte_snapshot_file=karte))

    def test_source_symlink_hardlink_and_mode_are_rejected(self):
        alias = self.inputs / "alias.json"
        alias.symlink_to(self.issue_file)
        hard = self.inputs / "hard.json"
        os.link(self.issue_file, hard)
        for path in (alias, hard):
            with self.subTest(path=path), self.assertRaises(control.LaunchControlError):
                self.issue(self.request(issue_snapshot_file=path))
        hard.unlink()
        self.issue_file.chmod(0o644)
        with self.assertRaises(control.LaunchControlError):
            self.issue()

    def test_foreign_or_unresolvable_group_writable_source_ancestor_is_rejected(self):
        self.inputs.chmod(0o770)
        with mock.patch.object(control.codex_launch_intent,
                               "_group_is_exclusive_to_current_uid", return_value=False):
            with self.assertRaises(control.LaunchControlError):
                self.issue()

    def test_protected_path_digest_is_derived_from_main_content(self):
        plan = self.issue(self.request(protected_paths=(".codex/agents/issue-implementer.toml",)))
        expected = control._sha((self.main / ".codex/agents/issue-implementer.toml").read_bytes())
        self.assertEqual(plan["protected_plan"], [{
            "path": ".codex/agents/issue-implementer.toml", "base_sha256": expected,
        }])

    def test_protected_path_change_between_reads_is_rejected(self):
        path = ".codex/agents/issue-implementer.toml"
        original = control._protected
        calls = 0

        def changing(main, paths):
            nonlocal calls
            result = original(main, paths)
            calls += 1
            if calls == 1:
                (main / path).write_text("name='changed'\n", encoding="utf-8")
            return result

        with mock.patch.object(control, "_protected", side_effect=changing):
            with self.assertRaisesRegex(control.LaunchControlError,
                                        "CONTROL_PROTECTED_PATH_CHANGED"):
                self.issue(self.request(protected_paths=(path,)))

    def test_concurrent_identical_issuers_create_one_entry(self):
        original = codex_launch_intent._validate_manifest

        def validate(value):
            with mock.patch.object(codex_launch_intent, "_stable_executable_evidence",
                                   side_effect=[("/usr/bin/bwrap", {}), ("/usr/bin/codex", {})]):
                return original(value)

        with mock.patch.object(control.codex_launch_intent, "_validate_manifest",
                               side_effect=validate):
            with ThreadPoolExecutor(max_workers=2) as pool:
                plans = list(pool.map(lambda _: control.issue(self.request(), now=NOW), range(2)))
        self.assertEqual(plans[0], plans[1])
        self.assertEqual(len(worktree_ledger.read_ledger(self.main)["entries"]), 1)


if __name__ == "__main__":
    unittest.main()
