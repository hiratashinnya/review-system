"""Issue #297 managed Issue-start adapter/hook tests（Issue #309 で台帳起票を追加）。"""

import io
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from blocker_gate.model import POLICY_VERSION
from issue_start import worktree_ledger
from issue_start import codex_launch_intent
from issue_start.codex_supervisor_workspace import GitFacts
from issue_start.gate import (
    BINDING_MARKER,
    FIX_BINDING_MARKER,
    IsolationOnlyAck,
    IssueStartError,
    IssueStartRequest,
    _require_transport_available,
    _validate_tool_input_shape,
    assert_no_worktree_residue,
    evaluate_issue_start,
    parse_dispatch_payload,
    record_open_entry,
)
from issue_start.hook import run as run_hook


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures" / "blocker_gate"
OID = "a" * 40
LEDGER_NOW = datetime(2026, 8, 19, 4, 11, 7, tzinfo=timezone.utc)
ISSUE_SNAPSHOT = json.dumps({
    "schema_version": "codex-issue-snapshot/2", "repository": "example/repo",
    "issue": 10, "url": "https://github.com/example/repo/issues/10",
    "title": "Issue 10", "body": "Implement the requested boundary.",
    "acceptance_criteria": ["implement safely"],
    "capture": {"captured_at": "2026-09-06T23:00:00Z",
                "captured_by": "capture-operator", "capture_method": "github-api"},
}, sort_keys=True)
KARTE_SNAPSHOT = json.dumps({
    "schema_version": "codex-karte-snapshot/2", "issue": 10, "round": 3,
    "open_findings": [{"id": "F-10-01", "status": "open", "summary": "fix this"}],
    "capture": {"captured_at": "2026-09-06T23:30:00Z",
                "captured_by": "karte-exporter", "capture_method": "karte-cli"},
}, sort_keys=True)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def codex_change_plan(root, *, issue=10, role="issue-implementer", fixer_round=None,
                      change_plan_id="plan-10", approved=True):
    repository = "example/repo"
    return {
        "schema_version": "codex-change-plan/2",
        "change_plan_id": change_plan_id,
        "owner_approval": {
            "status": "approved" if approved else "draft", "actor": "repo-owner",
            "recorded_at": "2026-09-07T00:00:00Z",
        },
        "issue": issue,
        "role": role,
        "fixer_round": fixer_round,
        "ledger_entry_id": "wl-123456789abc",
        "issue_source": {
            "path": f"tmp/_codex_control/sources/issue-{issue}.json",
            "sha256": digest(ISSUE_SNAPSHOT),
            "provenance": {
                "source_type": "github-issue-snapshot",
                **json.loads(ISSUE_SNAPSHOT)["capture"],
            },
        },
        "finding_ids": [] if role == "issue-implementer" else [f"F-{issue}-01"],
        "karte_source": None if role == "issue-implementer" else {
            "path": f"tmp/_codex_control/sources/karte-{issue}-r{fixer_round}.json",
            "sha256": digest(KARTE_SNAPSHOT),
            "provenance": {
                "source_type": "finding-karte-snapshot",
                **json.loads(KARTE_SNAPSHOT)["capture"],
            },
        },
        "protected_plan": [{"path": ".codex/hooks.json", "base_sha256": "b" * 64}],
    }


class CodexLaunchIntentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = json.loads(
            (ROOT / "issue_start/managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        manifest = self.root / "issue_start/managed-entrypoints-v2.json"
        manifest.parent.mkdir(parents=True)
        manifest.parent.chmod(0o755)
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        manifest.chmod(0o644)
        for relative in (".codex/agents/issue-implementer.toml",
                         ".ai/agents/issue-implementer.md",
                         ".codex/agents/issue-fixer.toml",
                         ".ai/agents/issue-fixer.md"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())

    def facts(self):
        workspace = self.root / ".worktrees/issue-10"
        return GitFacts(str(workspace), str(self.root), ".worktrees/issue-10",
                        "example/repo", "codex/issue-10", OID)

    def ledger_entry(self, *, role="issue-implementer", round_number=None):
        facts = self.facts()
        return {
            "entry_id": "wl-123456789abc", "issue": 10, "agent_type": role,
            "platform": "codex-supervisor",
            "round": round_number, "repository": facts.repository,
            "workspace": facts.workspace, "branch_name": facts.branch_name,
            "initial_oid": facts.head_oid, "status": "open",
            "change_plan_id": "plan-10", "issuance_status": "complete",
            "approved_by": "repo-owner", "approval_recorded_at": "2026-09-07T00:00:00Z",
            "task_key": ("issue_10" if role == "issue-implementer" else
                         f"issue_10_fix_r{round_number}"),
            "handoff_path": ("tmp/_handoff/issue-implementer--issue-10.yaml"
                             if role == "issue-implementer" else
                             f"tmp/_handoff/issue-fixer--issue-10-r{round_number}.yaml"),
            "protected_plan": [{"path": ".codex/hooks.json", "base_sha256": "b" * 64}],
        }

    def generate(self, request, *, plan=None, source_material=None, manifest=None,
                 entry=None, facts=None):
        return codex_launch_intent.generate_launch_intent(
            request, plan=plan or codex_change_plan(
                self.root, role=request.role, fixer_round=request.fixer_round),
            manifest=manifest or self.manifest, repo_root=self.root,
            source_material=source_material or {"issue": ISSUE_SNAPSHOT},
            canonical_facts=facts or self.facts(),
            canonical_entry=entry or self.ledger_entry(
                role=request.role, round_number=request.fixer_round),
        )

    def request(self, **changes):
        values = {
            "issue": 10, "role": "issue-implementer",
            "change_plan_id": "plan-10", "fixer_round": None,
        }
        values.update(changes)
        return codex_launch_intent.LaunchRequest(**values)

    def test_pure_generator_derives_every_non_owner_input(self):
        intent = self.generate(self.request())
        self.assertEqual(intent.schema_version, "codex-launch-intent/1")
        self.assertEqual(intent.task_key, "issue_10")
        self.assertEqual(intent.handoff_path,
                         "tmp/_handoff/issue-implementer--issue-10.yaml")
        self.assertEqual((intent.model, intent.reasoning_effort), ("gpt-5.6-sol", "xhigh"))
        self.assertEqual(intent.bwrap_executable, "/usr/bin/bwrap")
        self.assertTrue(Path(intent.codex_executable).is_absolute())
        self.assertEqual(set(intent.executable_evidence), {"bwrap", "codex"})
        self.assertEqual(intent.permission_profile, "issue-supervised")
        self.assertEqual(intent.runtime_root,
                         "tmp/_codex_sessions/issue_10/runtime-home")
        self.assertIn("Acceptance criteria", intent.prompt)
        self.assertEqual(intent.source_provenance["issue"]["url"],
                         "https://github.com/example/repo/issues/10")
        self.assertEqual(intent.source_provenance["issue"]["sha256"], digest(ISSUE_SNAPSHOT))
        self.assertEqual(intent.protected_paths,
                         (f".codex/hooks.json={'b' * 64}",))

    def test_fixer_derives_round_findings_karte_and_prompt(self):
        request = self.request(role="issue-fixer", fixer_round=3)
        intent = self.generate(
            request, source_material={"issue": ISSUE_SNAPSHOT, "karte": KARTE_SNAPSHOT}
        )
        self.assertEqual(intent.task_key, "issue_10_fix_r3")
        self.assertEqual(intent.handoff_path,
                         "tmp/_handoff/issue-fixer--issue-10-r3.yaml")
        self.assertIn("F-10-01", intent.prompt)
        self.assertIn("tmp/_codex_control/sources/karte-10-r3.json", intent.prompt)
        self.assertIn("fix this", intent.prompt)

    def test_source_digest_and_provenance_are_fail_closed(self):
        plan = codex_change_plan(self.root)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "ISSUE_SOURCE_INVALID"):
            self.generate(self.request(), plan=plan,
                          source_material={"issue": ISSUE_SNAPSHOT + "tampered"})
        plan = codex_change_plan(self.root)
        plan["issue_source"]["provenance"]["source_type"] = "handwritten"
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "ISSUE_SOURCE_INVALID"):
            self.generate(self.request(), plan=plan)

    def test_manual_input_types_ranges_and_role_round_are_fail_closed(self):
        cases = [
            (self.request(issue=True), "ISSUE_INVALID"),
            (self.request(issue=0), "ISSUE_INVALID"),
            (self.request(role="pr-reviewer"), "ROLE_INVALID"),
            (self.request(change_plan_id="../escape"), "CHANGE_PLAN_ID_INVALID"),
            (self.request(fixer_round=1), "FIXER_ROUND_FORBIDDEN"),
            (self.request(role="issue-fixer"), "FIXER_ROUND_INVALID"),
            (self.request(role="issue-fixer", fixer_round=0), "FIXER_ROUND_INVALID"),
        ]
        for request, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, reason
            ):
                self.generate(request, plan=codex_change_plan(self.root))

    def test_plan_approval_identity_and_sources_must_match_request(self):
        mutations = [
            ({"owner_approval": {"status": "draft", "actor": "repo-owner",
                                  "recorded_at": "2026-09-07T00:00:00Z"}}, "CHANGE_PLAN"),
            ({"issue": 11}, "CHANGE_PLAN_MISMATCH"),
            ({"role": "issue-fixer"}, "CHANGE_PLAN_MISMATCH"),
            ({"change_plan_id": "other"}, "CHANGE_PLAN_MISMATCH"),
            ({"issue_source": {"number": 10, "url": "https://evil.invalid/10"}},
             "ISSUE_SOURCE"),
            ({"finding_ids": ["F-11-01"]}, "IMPLEMENTER_SOURCE"),
            ({"karte_source": codex_change_plan(
                self.root, role="issue-fixer", fixer_round=1)["karte_source"]},
             "IMPLEMENTER_SOURCE"),
        ]
        for changes, reason in mutations:
            plan = codex_change_plan(self.root)
            plan.update(changes)
            with self.subTest(reason=reason), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, reason
            ):
                self.generate(self.request(), plan=plan)

    def test_ledger_and_protected_plan_are_strict(self):
        plans = []
        bad_path = codex_change_plan(self.root)
        bad_path["protected_plan"][0]["path"] = "src/app.py"
        plans.append((bad_path, "PROTECTED_PLAN_INVALID"))
        duplicate = codex_change_plan(self.root)
        duplicate["protected_plan"] *= 2
        plans.append((duplicate, "PROTECTED_PLAN_INVALID"))
        duplicate_digest = codex_change_plan(self.root)
        duplicate_digest["protected_plan"].append(
            {"path": ".codex/hooks.json", "base_sha256": "c" * 64}
        )
        plans.append((duplicate_digest, "PROTECTED_PLAN_INVALID"))
        for plan, reason in plans:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, reason
            ):
                self.generate(self.request(), plan=plan)

        stale = self.ledger_entry()
        stale["initial_oid"] = "c" * 40
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CANONICAL_LEDGER_MISMATCH"):
            self.generate(self.request(), entry=stale)

    def test_manifest_semantic_values_are_exact(self):
        mutations = [
            ("roles", lambda value: value["roles"]["issue-implementer"].update(
                reasoning_effort="low")),
            ("permission_profile", lambda value: value.update(permission_profile="legacy")),
            ("runtime_root_template", lambda value: value.update(
                runtime_root_template="../../escape/{task_key}")),
            ("executables", lambda value: value["executables"]["codex"].update(
                lookup_name="../codex")),
        ]
        for label, mutate in mutations:
            manifest = json.loads(json.dumps(self.manifest))
            mutate(manifest["codex_supervisor_launch"])
            with self.subTest(label=label), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, "MANIFEST_INVALID"
            ):
                self.generate(self.request(), manifest=manifest)

    def test_executable_evidence_rejects_foreign_owner_or_writable_by_others(self):
        executable = self.root / "test-codex"
        executable.write_text("#!/bin/sh\necho test-codex-1\n", encoding="utf-8")
        executable.chmod(0o755)
        with patch("issue_start.codex_launch_intent.os.getuid",
                   return_value=os.getuid() + 10000), self.assertRaisesRegex(
                       codex_launch_intent.LaunchIntentError,
                       "TEST_EXECUTABLE_INVALID",
                   ):
            codex_launch_intent._executable_evidence(
                str(executable), reason="TEST_EXECUTABLE_INVALID",
            )
        executable.chmod(0o775)
        with patch(
            "issue_start.codex_launch_intent._group_is_exclusive_to_current_uid",
            return_value=False,
        ), self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                  "TEST_EXECUTABLE_INVALID"):
            codex_launch_intent._executable_evidence(
                str(executable), reason="TEST_EXECUTABLE_INVALID",
            )
        executable.chmod(0o757)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "TEST_EXECUTABLE_INVALID"):
            codex_launch_intent._executable_evidence(
                str(executable), reason="TEST_EXECUTABLE_INVALID",
            )

    def test_installed_codex_is_accepted_with_stable_evidence(self):
        path, evidence = codex_launch_intent._stable_executable_evidence(
            "codex", reason="CODEX_EXECUTABLE_INVALID",
        )
        self.assertTrue(Path(path).is_absolute())
        self.assertEqual(evidence["path"], path)
        self.assertRegex(evidence["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(evidence["version"])

    def test_executable_evidence_rechecks_path_digest_and_version(self):
        first = self.root / "first-codex"
        second = self.root / "second-codex"
        for path, version in ((first, "first-1"), (second, "second-2")):
            path.write_text(f"#!/bin/sh\necho {version}\n", encoding="utf-8")
            path.chmod(0o755)
        with patch("issue_start.codex_launch_intent.shutil.which",
                   side_effect=[str(first), str(second)]), self.assertRaisesRegex(
                       codex_launch_intent.LaunchIntentError,
                       "executable evidence changed",
                   ):
            codex_launch_intent._stable_executable_evidence(
                "codex", reason="CODEX_EXECUTABLE_INVALID",
            )
        baseline = {
            "path": str(first), "sha256": "a" * 64, "version": "codex 1",
            "uid": os.getuid(), "mode": "0755",
        }
        for field, changed in (("sha256", "b" * 64), ("version", "codex 2")):
            replacement = dict(baseline)
            replacement[field] = changed
            with self.subTest(field=field), patch(
                "issue_start.codex_launch_intent._executable_evidence",
                side_effect=[(str(first), baseline), (str(first), replacement)],
            ), self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                      "executable evidence changed"):
                codex_launch_intent._stable_executable_evidence(
                    "codex", reason="CODEX_EXECUTABLE_INVALID",
                )

    def test_group_writable_parent_requires_an_exclusive_current_uid_group(self):
        directory = self.root / "shared-by-current-user-only"
        directory.mkdir()
        directory.chmod(0o770)
        codex_launch_intent._check_directory(
            directory.stat(), private=False, reason="TEST_DIRECTORY_INVALID",
        )
        with patch(
            "issue_start.codex_launch_intent._group_is_exclusive_to_current_uid",
            return_value=False,
        ), self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                  "unsafe group-writable directory"):
            codex_launch_intent._check_directory(
                directory.stat(), private=False, reason="TEST_DIRECTORY_INVALID",
            )

    def test_actual_project_trust_path_accepts_its_exclusive_group_parents(self):
        raw = codex_launch_intent._read_same_fd(
            ROOT, PurePosixPath("issue_start/managed-entrypoints-v2.json"),
            reason="MANIFEST_INVALID", leaf_private=False,
        )
        self.assertIn(b'"codex_supervisor_launch"', raw)

    def test_additional_nss_group_principal_is_rejected(self):
        uid = os.getuid()
        gid = os.getgid()
        current = SimpleNamespace(pw_uid=uid, pw_gid=gid, pw_name="current")
        other = SimpleNamespace(pw_uid=uid + 1, pw_gid=gid + 1, pw_name="other")
        group = SimpleNamespace(gr_gid=gid, gr_mem=["current", "other"])
        accounts = {"current": current, "other": other}
        with patch("issue_start.codex_launch_intent.pwd.getpwuid", return_value=current), \
                patch("issue_start.codex_launch_intent.pwd.getpwall",
                      return_value=[current, other]), \
                patch("issue_start.codex_launch_intent.pwd.getpwnam",
                      side_effect=lambda name: accounts[name]), \
                patch("issue_start.codex_launch_intent.grp.getgrgid", return_value=group):
            self.assertFalse(codex_launch_intent._group_is_exclusive_to_current_uid(gid))

    def test_group_membership_lookup_fails_closed(self):
        with patch("issue_start.codex_launch_intent.grp.getgrgid",
                   side_effect=OSError("NSS unavailable")):
            self.assertFalse(
                codex_launch_intent._group_is_exclusive_to_current_uid(os.getgid())
            )

    def test_structured_issue_requires_matching_issue_and_nonempty_ac(self):
        for field, value in (("issue", 11), ("acceptance_criteria", [])):
            snapshot = json.loads(ISSUE_SNAPSHOT)
            snapshot[field] = value
            raw = json.dumps(snapshot, sort_keys=True)
            plan = codex_change_plan(self.root)
            plan["issue_source"]["sha256"] = digest(raw)
            with self.subTest(field=field), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, "ISSUE_SOURCE_INVALID"
            ):
                self.generate(self.request(), plan=plan, source_material={"issue": raw})

    def test_fixer_karte_exactly_binds_round_status_and_open_ids(self):
        request = self.request(role="issue-fixer", fixer_round=3)
        for label, change in (
            ("round", lambda value: value.update(round=2)),
            ("resolved", lambda value: value["open_findings"][0].update(status="resolved")),
            ("extra", lambda value: value["open_findings"].append(
                {"id": "F-10-02", "status": "open", "summary": "unexpected"})),
        ):
            snapshot = json.loads(KARTE_SNAPSHOT)
            change(snapshot)
            raw = json.dumps(snapshot, sort_keys=True)
            plan = codex_change_plan(self.root, role="issue-fixer", fixer_round=3)
            plan["karte_source"]["sha256"] = digest(raw)
            with self.subTest(label=label), self.assertRaisesRegex(
                codex_launch_intent.LaunchIntentError, "KARTE_SOURCE_INVALID"
            ):
                self.generate(request, plan=plan,
                              source_material={"issue": ISSUE_SNAPSHOT, "karte": raw})

    def write_plan(self, plan=None, *, write_karte=False):
        plan = plan or codex_change_plan(self.root)
        control = self.root / "tmp/_codex_control"
        sources = control / "sources"
        plans = control / "change-plans"
        for directory in (control, sources, plans):
            directory.mkdir(parents=True, exist_ok=True)
            directory.chmod(0o700)
        (self.root / "tmp").chmod(0o755)
        source = self.root / plan["issue_source"]["path"]
        source.write_text(ISSUE_SNAPSHOT, encoding="utf-8")
        source.chmod(0o600)
        if write_karte:
            karte = self.root / plan["karte_source"]["path"]
            karte.write_text(KARTE_SNAPSHOT, encoding="utf-8")
            karte.chmod(0o600)
        target = plans / "plan-10.json"
        target.write_text(json.dumps(plan), encoding="utf-8")
        target.chmod(0o600)
        ledger_dir = self.root / "tmp/_worktree"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        ledger_dir.chmod(0o755)
        ledger = ledger_dir / "ledger.json"
        ledger.write_text(json.dumps({"schema_version": "worktree-ledger/1",
                                      "entries": [self.ledger_entry(
                                          role=plan["role"], round_number=plan["fixer_round"])]}),
                          encoding="utf-8")
        ledger.chmod(0o600)
        workspace = Path(self.facts().workspace)
        for relative in (".codex/agents/issue-implementer.toml",
                         ".ai/agents/issue-implementer.md",
                         ".codex/agents/issue-fixer.toml",
                         ".ai/agents/issue-fixer.md"):
            target_role = workspace / relative
            target_role.parent.mkdir(parents=True, exist_ok=True)
            target_role.write_bytes((self.root / relative).read_bytes())
        return target

    def load(self, request):
        with patch("issue_start.codex_launch_intent.inspect_git_facts",
                   return_value=self.facts()):
            return codex_launch_intent.load_launch_intent(request, cwd=self.root)

    def test_loader_requires_existing_secure_owner_plan(self):
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            self.load(self.request())
        target = self.write_plan()
        self.assertEqual(self.load(self.request()).task_key, "issue_10")
        target.chmod(0o666)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            self.load(self.request())

    def test_private_control_state_rejects_writable_parent_symlink_and_hardlink(self):
        target = self.write_plan()
        control = self.root / "tmp/_codex_control"
        control.chmod(0o770)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            self.load(self.request())
        control.chmod(0o700)

        alternate = target.with_name("alternate.json")
        target.rename(alternate)
        target.symlink_to(alternate.name)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            self.load(self.request())
        target.unlink()
        os.link(alternate, target)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "CHANGE_PLAN_MISSING"):
            self.load(self.request())

    def test_secure_reader_keeps_the_fstat_checked_fd_during_rename_swap(self):
        target = self.write_plan()
        original = target.read_bytes()
        real_read = os.read
        swapped = False

        def swap_after_first_read(fd, count):
            nonlocal swapped
            chunk = real_read(fd, count)
            if chunk and not swapped:
                swapped = True
                target.rename(target.with_suffix(".original"))
                target.write_text('{"attacker": true}', encoding="utf-8")
                target.chmod(0o600)
            return chunk

        with patch("issue_start.codex_launch_intent.os.read", side_effect=swap_after_first_read):
            actual = codex_launch_intent._read_same_fd(
                self.root, PurePosixPath("tmp/_codex_control/change-plans/plan-10.json"),
                reason="CHANGE_PLAN_MISSING",
                private_from=PurePosixPath("tmp/_codex_control"),
            )
        self.assertTrue(swapped)
        self.assertEqual(actual, original)

    def test_child_workspace_plan_cannot_replace_main_control_state(self):
        self.write_plan()
        child = self.root / ".worktrees/attacker"
        fake = child / "tmp/_codex_control/change-plans"
        fake.mkdir(parents=True)
        fake_plan = codex_change_plan(self.root)
        fake_plan["owner_approval"]["actor"] = "inner-self-claim"
        (fake / "plan-10.json").write_text(json.dumps(fake_plan), encoding="utf-8")
        with patch("issue_start.codex_launch_intent.worktree_ledger.main_worktree_root",
                   return_value=self.root), patch(
                       "issue_start.codex_launch_intent.inspect_git_facts",
                       return_value=self.facts()):
            intent = codex_launch_intent.load_launch_intent(self.request(), cwd=child)
        self.assertEqual(intent.change_plan_id, "plan-10")
        self.assertNotIn("inner-self-claim", intent.prompt)

    def test_loader_observes_live_git_for_the_canonical_ledger_workspace(self):
        self.write_plan()
        with patch("issue_start.codex_launch_intent.inspect_git_facts",
                   return_value=self.facts()) as inspect:
            codex_launch_intent.load_launch_intent(self.request(), cwd=self.root)
        inspect.assert_called_once_with(self.facts().workspace)

    def test_fixer_loader_requires_karte(self):
        request = self.request(role="issue-fixer", fixer_round=3)
        plan = codex_change_plan(self.root, role="issue-fixer", fixer_round=3)
        self.write_plan(plan)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "KARTE_SOURCE_INVALID"):
            self.load(request)
        self.write_plan(plan, write_karte=True)
        self.assertEqual(self.load(request).round_number, 3)

    def test_loader_rejects_tampered_issue_snapshot(self):
        self.write_plan()
        source = self.root / "tmp/_codex_control/sources/issue-10.json"
        source.write_text(ISSUE_SNAPSHOT + "tampered", encoding="utf-8")
        source.chmod(0o600)
        with self.assertRaisesRegex(codex_launch_intent.LaunchIntentError,
                                    "ISSUE_SOURCE_INVALID"):
            self.load(self.request())

    def test_nonprivate_manifest_and_ledger_leaf_modes_fail_closed(self):
        cases = (
            ("manifest-foreign-group", "manifest", 0o660, False, "MANIFEST_INVALID"),
            ("manifest-world-write", "manifest", 0o646, True, "MANIFEST_INVALID"),
            ("ledger-foreign-group", "ledger", 0o660, False, "CANONICAL_LEDGER_INVALID"),
            ("ledger-world-write", "ledger", 0o606, True, "CANONICAL_LEDGER_INVALID"),
        )
        for label, leaf, mode, group_is_exclusive, reason in cases:
            with self.subTest(label=label):
                self.write_plan()
                target = (self.root / "issue_start/managed-entrypoints-v2.json"
                          if leaf == "manifest"
                          else self.root / "tmp/_worktree/ledger.json")
                target.chmod(mode)
                with patch(
                    "issue_start.codex_launch_intent._group_is_exclusive_to_current_uid",
                    return_value=group_is_exclusive,
                ), self.assertRaisesRegex(codex_launch_intent.LaunchIntentError, reason):
                    self.load(self.request())
                target.chmod(0o644 if leaf == "manifest" else 0o600)

    def test_nonprivate_manifest_and_ledger_leaf_reject_nss_lookup_failure(self):
        for leaf, reason in (("manifest", "MANIFEST_INVALID"),
                             ("ledger", "CANONICAL_LEDGER_INVALID")):
            with self.subTest(leaf=leaf):
                self.write_plan()
                target = (self.root / "issue_start/managed-entrypoints-v2.json"
                          if leaf == "manifest"
                          else self.root / "tmp/_worktree/ledger.json")
                target.chmod(0o660)
                with patch("issue_start.codex_launch_intent.grp.getgrgid",
                           side_effect=OSError("NSS unavailable")), self.assertRaisesRegex(
                               codex_launch_intent.LaunchIntentError, reason,
                           ):
                    self.load(self.request())
                target.chmod(0o644 if leaf == "manifest" else 0o600)

    def hook(self, command):
        stdout = io.StringIO()
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        with patch("issue_start.codex_launch_intent.inspect_git_facts",
                   return_value=self.facts()):
            rc = codex_launch_intent.run_hook(
                stdin=io.StringIO(json.dumps(payload)), stdout=stdout, cwd=self.root
            )
        return rc, stdout.getvalue()

    def test_hook_dry_runs_same_generator_and_leaves_no_receipt(self):
        self.write_plan()
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        command = ("python3 -m issue_start.codex_supervisor run --issue 10 "
                   "--role issue-implementer --change-plan-id plan-10")
        rc, output = self.hook(command)
        self.assertEqual((rc, output), (0, ""))
        self.assertEqual(sorted(path.relative_to(self.root).as_posix()
                                for path in self.root.rglob("*")), before)

    def test_hook_denies_noncanonical_supervisor_and_missing_plan(self):
        absolute_python = str(Path(sys.executable).resolve())
        commands = [
            ("python3 -m issue_start.codex_supervisor run --issue 10", "COMMAND_INVALID"),
            ("rtk python3 -m issue_start.codex_supervisor run --issue 10", "COMMAND_INVALID"),
            (f"{absolute_python} -m issue_start.codex_supervisor run --issue 10",
             "COMMAND_INVALID"),
            (f"env {absolute_python} -m issue_start.codex_supervisor run --issue 10",
             "COMMAND_INVALID"),
            ("python3 -m issue_start.codex_supervisor run --issue 10 "
             "--role issue-implementer --change-plan-id missing", "CHANGE_PLAN_MISSING"),
            ("python3 -m issue_start.codex_supervisor run --issue 10 "
             "--role issue-implementer --change-plan-id plan-10 --workspace /tmp/x",
             "COMMAND_INVALID"),
            ("python3 -m issue_start.codex_supervisor run --issue 10 "
             "--role issue-implementer --change-plan-id plan-10; true", "COMMAND_INVALID"),
            ("python3 -m issue_start.codex_supervisor run --issue 01 "
             "--role issue-implementer --change-plan-id plan-10", "COMMAND_INVALID"),
            ("python3 -m issue_start.codex_supervisor run --issue 10 --issue 11 "
             "--role issue-implementer --change-plan-id plan-10", "COMMAND_INVALID"),
        ]
        for command, reason in commands:
            with self.subTest(reason=reason):
                rc, output = self.hook(command)
                self.assertEqual(rc, 0)
                decision = json.loads(output)["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn(reason, decision["permissionDecisionReason"])

    def test_hook_applies_identical_validation_to_raw_and_rtk_launch(self):
        self.write_plan()
        raw = ("python3 -m issue_start.codex_supervisor run --issue 10 "
               "--role issue-implementer --change-plan-id plan-10")
        absolute = str(Path(sys.executable).resolve()) + raw.removeprefix("python3")
        for command in (raw, "rtk " + raw):
            with self.subTest(command=command):
                self.assertEqual(self.hook(command), (0, ""))
        for command in (raw + " --workspace /tmp/x",
                        "rtk " + raw + " --workspace /tmp/x"):
            with self.subTest(command=command):
                decision = json.loads(self.hook(command)[1])["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("COMMAND_INVALID", decision["permissionDecisionReason"])
        for command in ("env " + raw, "env PYTHONPATH=/tmp " + raw,
                        "rtk env -i " + absolute):
            with self.subTest(command=command):
                decision = json.loads(self.hook(command)[1])["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("COMMAND_INVALID", decision["permissionDecisionReason"])

    def test_hook_accepts_exact_fixer_resume_and_requires_round(self):
        plan = codex_change_plan(self.root, role="issue-fixer", fixer_round=3)
        self.write_plan(plan, write_karte=True)
        exact = ("python3 -m issue_start.codex_supervisor resume --issue 10 "
                 "--role issue-fixer --change-plan-id plan-10 --fixer-round 3")
        self.assertEqual(self.hook(exact), (0, ""))
        decision = json.loads(self.hook(exact.removesuffix(" --fixer-round 3"))[1])[
            "hookSpecificOutput"
        ]
        self.assertIn("FIXER_ROUND_INVALID", decision["permissionDecisionReason"])
    def test_hook_classifies_relevance_before_rejecting_compound_commands(self):
        self.assertEqual(self.hook("git status && git diff"), (0, ""))
        self.assertEqual(self.hook("git status\ngit diff"), (0, ""))
        command = ("git status && python3 -m issue_start.codex_supervisor run "
                   "--issue 10 --role issue-implementer --change-plan-id plan-10")
        decision = json.loads(self.hook(command)[1])["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("COMMAND_INVALID", decision["permissionDecisionReason"])
        self.assertEqual(self.hook("git status\ncodex exec -C /tmp/worktree task"), (0, ""))
        decision = json.loads(self.hook(
            "git status\npython3 -m issue_start.codex_supervisor run --issue 10"
        )[1])["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("COMMAND_INVALID", decision["permissionDecisionReason"])

    def test_hook_ignores_unrelated_bash_and_rejects_invalid_payload(self):
        self.assertEqual(self.hook("python3 -m unittest")[1], "")
        self.assertEqual(self.hook("env codex exec -C /tmp/worktree task"), (0, ""))
        self.assertEqual(self.hook("sh -c 'codex exec -C /tmp/worktree task'"), (0, ""))
        stdout = io.StringIO()
        codex_launch_intent.run_hook(
            stdin=io.StringIO("[]"), stdout=stdout, cwd=self.root
        )
        self.assertIn("HOOK_PAYLOAD_INVALID", stdout.getvalue())


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Collector:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.waiver_calls = 0

    def collect_issue(self, repository, number):
        return self.snapshot

    def collect_waiver_materials(self, repository, refs):
        self.waiver_calls += 1
        raise AssertionError("#299前に waiver provider を呼んではならない")

    def issue_metadata(self, repository, number):
        return {
            "number": number,
            "title": f"blocker {number}",
            "html_url": f"https://github.com/{repository}/issues/{number}",
        }


def request(repository="example/repo", issue=10):
    return IssueStartRequest("issue-pipeline", repository, issue)


def claude_binding():
    return {
        "entrypoint": "issue-pipeline",
        "repository": "example/repo",
        "issue": 10,
        "branch_name": "issue-297",
        "base_ref": "main",
        "base_oid": OID,
        "base_pr": None,
    }


class FakeCompleted:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def git_runner(*, origin="https://github.com/example/repo.git", inside="true", top=ROOT):
    def run(argv, **kwargs):
        if argv == ["git", "rev-parse", "--is-inside-work-tree"]:
            return FakeCompleted(inside + "\n")
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return FakeCompleted(str(top) + "\n")
        if argv == ["git", "remote", "get-url", "origin"]:
            return FakeCompleted(origin + "\n")
        raise AssertionError(f"unexpected git argv: {argv}")
    return run


def fake_codex_binding(payload, tool_input, *, agent_type, cwd, now, runner):
    """旧 parser 単体テストを durable ledger の I/O から分離する seam。"""
    from issue_start.gate import _codex_repository

    task_key = tool_input["task_name"]
    repository = _codex_repository(payload, cwd=cwd, runner=runner)
    issue = int(task_key.split("_")[1])
    round_number = 1 if agent_type == "issue-implementer" else int(task_key.rsplit("r", 1)[1])
    return {
        "entry_id": "wl-000000000001",
        "issue": issue,
        "round": round_number,
        "repository": repository,
        "workspace": str(cwd),
        "branch_name": "codex/issue-bound",
        "expected_oid": OID,
        "handoff_path": (
            f"tmp/_handoff/issue-implementer--issue-{issue}.yaml"
            if agent_type == "issue-implementer"
            else f"tmp/_handoff/issue-fixer--issue-{issue}-r{round_number}.yaml"
        ),
        "task_key": task_key,
    }


class DispatchPayloadMixin:
    def setUp(self):
        availability = patch("issue_start.gate._require_transport_available")
        availability.start()
        self.addCleanup(availability.stop)

    """Codex/Claude の正規 dispatch payload を組み立てる共通ヘルパ（テストは持たない）。"""

    def codex_payload(self, *, task_name="issue_10", tool="collaborationspawn_agent", cwd=ROOT):
        return {
            "cwd": str(cwd),
            "tool_name": tool,
            "tool_input": {
                "agent_type": "issue-implementer",
                "fork_turns": "all",
                "task_name": task_name,
                # Codex 0.146.0 の実測では message は暗号化値。binding に使わない。
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }

    def claude_payload(self, binding=None, *, tool="Task", isolation="worktree"):
        raw = claude_binding() if binding is None else binding
        tool_input = {
            "subagent_type": "issue-implementer",
            "prompt": BINDING_MARKER + json.dumps(raw, separators=(",", ":")),
            "description": "hook deny probe",
        }
        # Issue #350: 正規の dispatch は必ず `isolation: "worktree"` を伴う。
        if isolation is not None:
            tool_input["isolation"] = isolation
        return {"tool_name": tool, "tool_input": tool_input}


class DispatchPayloadTests(DispatchPayloadMixin, unittest.TestCase):
    @unittest.skip("Codex prepare/binding transport retired by Issue #452")
    def test_codex_encrypted_message_uses_task_name_and_worktree_origin(self):
        for tool_name in ("spawn_agent", "collaborationspawn_agent"):
            with self.subTest(tool_name=tool_name):
                actual = parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
                self.assertEqual((actual.entrypoint, actual.repository, actual.issue),
                                 ("issue-pipeline", "example/repo", 10))
                self.assertEqual(actual.task_key, "issue_10")
                self.assertEqual(actual.ledger_entry_id, "wl-000000000001")

    @unittest.skip("Codex prepare/binding transport retired by Issue #452")
    def test_codex_accepts_strict_github_https_and_ssh_origins(self):
        for origin in (
            "https://github.com/example/repo.git",
            "git@github.com:example/repo.git",
            "ssh://git@github.com/example/repo.git",
        ):
            with self.subTest(origin=origin):
                actual = parse_dispatch_payload(
                    self.codex_payload(), cwd=ROOT, runner=git_runner(origin=origin)
                )
                self.assertEqual(actual.repository, "example/repo")

    @unittest.skip("Codex payload details are intentionally not parsed")
    def test_codex_bad_or_missing_task_name_is_fail_close(self):
        for task_name in (None, "", "issue_0", "issue_01", "issue-10", "issue_10_more", "xissue_10"):
            payload = self.codex_payload()
            if task_name is None:
                del payload["tool_input"]["task_name"]
            else:
                payload["tool_input"]["task_name"] = task_name
            with self.subTest(task_name=task_name), self.assertRaisesRegex(
                IssueStartError,
                "ISSUE_START_(TOOL_INPUT_SHAPE_INVALID|TASK_NAME_INVALID)",
            ):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())

    @unittest.skip("Codex payload details are intentionally not parsed")
    def test_codex_bad_cwd_worktree_and_origin_are_fail_close(self):
        cases = [
            (self.codex_payload(cwd=ROOT.parent), git_runner(), "ISSUE_START_CWD_MISMATCH"),
            (self.codex_payload(), git_runner(inside="false"), "ISSUE_START_NOT_WORKTREE"),
            (self.codex_payload(), git_runner(top=ROOT.parent), "ISSUE_START_WORKTREE_ROOT_MISMATCH"),
            (self.codex_payload(), git_runner(origin="https://evil.example/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="http://github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="https://user@github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
        ]
        for payload, runner, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(payload, cwd=ROOT, runner=runner)

    def test_claude_task_and_runtime_agent_alias_use_marker_contract(self):
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )
        bad = claude_binding()
        bad.pop("base_oid")
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_UNKNOWN_FIELD"):
            parse_dispatch_payload(self.claude_payload(bad))
        wrong_entrypoint = claude_binding()
        wrong_entrypoint["entrypoint"] = "other-pipeline"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"):
            parse_dispatch_payload(self.claude_payload(wrong_entrypoint))

    def test_codex_agent_matcher_alias_is_not_a_codex_payload_alias(self):
        with self.assertRaisesRegex(
            IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"
        ):
            parse_dispatch_payload(
                self.codex_payload(tool="Agent"), cwd=ROOT, runner=git_runner()
            )

    def test_claude_shape_rejects_codex_field_mixing(self):
        for field, value in (
            ("agent_type", "issue-implementer"),
            ("message", "ENC[AQICAH-encrypted-prompt]"),
            ("task_name", "issue_10"),
        ):
            payload = self.claude_payload(tool="Agent")
            payload["tool_input"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_(TARGET_UNKNOWN|TOOL_INPUT_SHAPE_INVALID)"
            ):
                parse_dispatch_payload(payload)

    def test_unknown_or_similar_tool_names_are_not_payload_aliases(self):
        for tool_name in (
            "collaboration.spawn_agent",
            "evil.spawn_agent",
            "evilspawn_agent",
            "collaborationspawn_agent_extra",
            "collaborationspawn_agents",
        ):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
        for tool_name in ("agent", "Agents", "TaskAgent", "Agent_extra"):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(self.claude_payload(tool=tool_name))

    def test_non_issue_agent_is_explicitly_unmanaged(self):
        payload = self.codex_payload()
        payload["tool_input"]["agent_type"] = "explorer"
        self.assertIsNone(parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner()))

    def test_missing_or_ambiguous_target_is_fail_close(self):
        missing = self.codex_payload()
        del missing["tool_input"]["agent_type"]
        ambiguous = self.codex_payload()
        ambiguous["tool_input"]["subagent_type"] = "issue-implementer"
        for payload, reason in ((missing, "TARGET_UNKNOWN"), (ambiguous, "TRANSPORT_UNAVAILABLE")):
            with self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())


class IsolationContractTests(DispatchPayloadMixin, unittest.TestCase):
    """Issue #350: Claude dispatch は `isolation: "worktree"` を欠くと deny される。

    分離は role 側では実現できない（gitgate に worktree を作成・移動する verb が無く、
    agent-command-gate の
    層2 が `cd` を deny する）ので、dispatch 側の指定だけが「isolated worktree」契約を
    成立させる唯一の手段。欠落は fail-close で拒否する。

    Codex の局所 isolation parser は availability 検査より後にある。この class は setUp で
    availability gate を差し替えて parser 単体を検証するが、本番の Codex implementer/fixer は
    ``ISSUE_START_TRANSPORT_UNAVAILABLE`` で先に拒否され、all-tool hook も
    ``CODEX_BINDING_TRANSPORT_UNAVAILABLE`` で fail-close する。
    """

    def test_claude_dispatch_with_worktree_isolation_is_bound(self):
        payload = self.claude_payload()
        self.assertEqual(payload["tool_input"]["isolation"], "worktree")
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )

    def test_claude_dispatch_without_worktree_isolation_is_denied(self):
        # None＝field 自体が無い（isolation を渡し忘れた dispatch）。
        for isolation in (None, "remote", "", "Worktree", "worktree ", 1, True, ["worktree"]):
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ISOLATION_NOT_WORKTREE"
            ):
                parse_dispatch_payload(self.claude_payload(isolation=isolation))

    def test_isolation_check_does_not_mask_more_fundamental_shape_errors(self):
        # required field 欠落は isolation より先に報告する（直す順序を誤らせない）。
        payload = self.claude_payload(isolation=None)
        del payload["tool_input"]["prompt"]
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"):
            parse_dispatch_payload(payload)

    @unittest.skip("Codex prepare/binding parser retired by Issue #452")
    def test_codex_local_parser_carries_no_isolation_requirement_after_availability_gate(self):
        # setUp で availability gate を差し替えた局所契約。現行 production dispatch の
        # availability: unavailable を解除したり、保護済み transport の稼働を示したりしない。
        self.assertEqual(
            parse_dispatch_payload(self.codex_payload(), cwd=ROOT, runner=git_runner()).task_key,
            "issue_10",
        )

    def test_unmanaged_agents_are_never_required_to_declare_isolation(self):
        # unmanaged な dispatch を巻き込むと全委譲が壊れる。素通し（None）を固定する。
        # **`issue-fixer` は Issue #354 PR-4 で `isolation_only` へ移ったのでここには入らない**
        # （IsolationOnlyContractTests が別途 deny 側を固定する）。
        for agent in ("pr-reviewer", "general-purpose", "dsv2-lookup"):
            payload = self.claude_payload(isolation=None)
            payload["tool_input"]["subagent_type"] = agent
            with self.subTest(agent=agent):
                self.assertIsNone(parse_dispatch_payload(payload))

    def test_broken_manifest_isolation_value_fails_close(self):
        # manifest 破損（非文字列・空）を「要求なし」と誤読して素通ししない。
        for broken in ("", None, 1, True, ["worktree"]):
            transport = {
                "required_tool_input_fields": ["subagent_type", "prompt"],
                "forbidden_tool_input_fields": ["agent_type"],
                "required_isolation": broken,
            }
            with self.subTest(broken=broken), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                _validate_tool_input_shape(
                    {"subagent_type": "issue-implementer", "prompt": "x", "isolation": "worktree"},
                    transport,
                )

def fix_binding(**overrides):
    raw = {
        "issue": 354,
        "round": 1,
        "branch_name": "claude/issue-354-pr4",
        "repository": "example/repo",
        "expected_oid": "b" * 40,
        "handoff_path": "tmp/_handoff/issue-fixer--issue-354-fix1.yaml",
    }
    raw.update(overrides)
    return raw


def fixer_payload(binding=None, *, tool="Task", isolation="worktree", agent="issue-fixer"):
    raw = fix_binding() if binding is None else binding
    tool_input = {
        "subagent_type": agent,
        "prompt": "fix findings\n"
        + FIX_BINDING_MARKER
        + json.dumps(raw, separators=(",", ":")),
        "description": "remediation round",
    }
    if isolation is not None:
        tool_input["isolation"] = isolation
    return {"tool_name": tool, "tool_input": tool_input}


class IsolationOnlyContractTests(unittest.TestCase):
    """Issue #354 PR-4: `issue-fixer` は「分離だけを課す」区分として dispatch を検証される。

    managed（`issue-implementer`）との差は **GitHub API を叩かないこと**であって、
    shape / isolation / marker の厳しさではない。緩んでいないことをここで固定する。
    """

    def test_valid_fixer_dispatch_returns_an_isolation_only_ack(self):
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                ack = parse_dispatch_payload(fixer_payload(tool=tool_name))
                self.assertEqual(
                    ack,
                    IsolationOnlyAck(
                        entrypoint="issue-pipeline",
                        agent_type="issue-fixer",
                        issue=354,
                        round=1,
                        branch_name="claude/issue-354-pr4",
                        handoff_path="tmp/_handoff/issue-fixer--issue-354-fix1.yaml",
                        expected_oid="b" * 40,
                        repository="example/repo",
                    ),
                )

    def test_missing_or_wrong_isolation_is_denied(self):
        for isolation in (None, "remote", "", "Worktree", "worktree ", 1, True, ["worktree"]):
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ISOLATION_NOT_WORKTREE"
            ):
                parse_dispatch_payload(fixer_payload(isolation=isolation))

    def test_missing_or_duplicated_marker_is_fail_close(self):
        payload = fixer_payload()
        payload["tool_input"]["prompt"] = "fix findings without a marker"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(payload)
        duplicated = fixer_payload()
        line = FIX_BINDING_MARKER + json.dumps(fix_binding(), separators=(",", ":"))
        duplicated["tool_input"]["prompt"] = line + "\n" + line
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(duplicated)

    def test_invalid_json_marker_is_fail_close(self):
        payload = fixer_payload()
        payload["tool_input"]["prompt"] = FIX_BINDING_MARKER + "{not json"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_INVALID_JSON"):
            parse_dispatch_payload(payload)
        not_object = fixer_payload()
        not_object["tool_input"]["prompt"] = FIX_BINDING_MARKER + "[1,2]"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_INVALID_JSON"):
            parse_dispatch_payload(not_object)

    def test_field_set_must_be_exact(self):
        extra = fix_binding()
        extra["base_pr"] = None
        missing = fix_binding()
        del missing["expected_oid"]
        missing_repository = fix_binding()
        del missing_repository["repository"]
        for raw in (extra, missing, missing_repository):
            with self.subTest(raw=sorted(raw)), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_BINDING_UNKNOWN_FIELD"
            ):
                parse_dispatch_payload(fixer_payload(raw))

    def test_field_values_are_validated(self):
        cases = [
            ({"issue": 0}, "ISSUE_START_ISSUE_INVALID"),
            ({"issue": "354"}, "ISSUE_START_ISSUE_INVALID"),
            ({"issue": True}, "ISSUE_START_ISSUE_INVALID"),
            ({"round": 0}, "ISSUE_START_ROUND_INVALID"),
            ({"round": None}, "ISSUE_START_ROUND_INVALID"),
            ({"round": "1"}, "ISSUE_START_ROUND_INVALID"),
            ({"branch_name": "-evil"}, "ISSUE_START_BRANCH_INVALID"),
            ({"branch_name": ""}, "ISSUE_START_BRANCH_INVALID"),
            ({"repository": ""}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": "no-slash"}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": "owner/repo/extra"}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": None}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"expected_oid": "b" * 39}, "ISSUE_START_EXPECTED_OID_INVALID"),
            ({"expected_oid": "B" * 40}, "ISSUE_START_EXPECTED_OID_INVALID"),
            ({"expected_oid": None}, "ISSUE_START_EXPECTED_OID_INVALID"),
        ]
        for override, reason in cases:
            with self.subTest(override=override), self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(fixer_payload(fix_binding(**override)))

    def test_handoff_path_must_be_relative_and_bound_to_the_issue(self):
        bad_paths = [
            "/abs/tmp/_handoff/issue-fixer--issue-354.yaml",
            "tmp/_handoff/../../etc/issue-fixer--issue-354.yaml",
            "tmp/_handoff/sub/issue-fixer--issue-354.yaml",
            "tmp/_karte/issue-fixer--issue-354.yaml",
            "tmp/_handoff/issue-fixer--issue-354.txt",
            # 境界検査: 別 Issue のファイル（`issue-3541`）を受理しない。
            "tmp/_handoff/issue-fixer--issue-3541.yaml",
            # agent_type 束縛: implementer 側のハンドオフを上書きさせない。
            "tmp/_handoff/issue-implementer--issue-354.yaml",
            "",
        ]
        for path in bad_paths:
            with self.subTest(path=path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_HANDOFF_PATH_INVALID"
            ):
                parse_dispatch_payload(fixer_payload(fix_binding(handoff_path=path)))
        # サフィックス無し・`.` 区切りはどちらも受理する（ラウンド採番は呼び出し元の裁量）。
        for path in (
            "tmp/_handoff/issue-fixer--issue-354.yaml",
            "tmp/_handoff/issue-fixer--issue-354-fix2.yaml",
        ):
            with self.subTest(path=path):
                ack = parse_dispatch_payload(fixer_payload(fix_binding(handoff_path=path)))
                self.assertEqual(ack.handoff_path, path)

    def test_shape_errors_are_reported_before_the_marker_is_read(self):
        payload = fixer_payload(isolation=None)
        del payload["tool_input"]["prompt"]
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"):
            parse_dispatch_payload(payload)

    def test_codex_field_mixing_is_rejected(self):
        for field, value in (
            ("agent_type", "issue-fixer"),
            ("message", "ENC[AQICAH-encrypted-prompt]"),
            ("task_name", "issue_354"),
        ):
            payload = fixer_payload()
            payload["tool_input"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_(TARGET_UNKNOWN|TOOL_INPUT_SHAPE_INVALID)"
            ):
                parse_dispatch_payload(payload)

    def test_managed_dispatch_behaviour_is_unchanged(self):
        """回帰: `isolation_only` の追加が managed 経路（`issue-implementer`）を変えていない。"""
        payload = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }
        self.assertEqual(parse_dispatch_payload(payload), request())
        # `issue-implementer` の marker を `issue-fixer` に流用しても通らない（契約が別）。
        borrowed = fixer_payload()
        borrowed["tool_input"]["prompt"] = BINDING_MARKER + json.dumps(
            claude_binding(), separators=(",", ":")
        )
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(borrowed)

    def test_manifest_schema_version_mismatch_is_fail_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                json.dumps({
                    "schema_version": "managed-issue-entrypoints/1",
                    "policy_version": "issue-start/1.0",
                    "managed": [],
                }),
                encoding="utf-8",
            )
            with patch("issue_start.gate.ENTRYPOINT_MANIFEST", path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                parse_dispatch_payload(fixer_payload())

    def test_an_agent_type_in_both_sections_is_fail_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            entry = {
                "entrypoint": "issue-pipeline",
                "agent_type": "issue-fixer",
                "binding_transports": {
                    "claude": {
                        "tool_names": ["Task"],
                        "agent_type_field": "subagent_type",
                        "required_tool_input_fields": ["subagent_type", "prompt"],
                        "forbidden_tool_input_fields": ["agent_type"],
                        "prompt_field": "prompt",
                        "binding_marker": "ISSUE_FIX_BINDING_V1=",
                        "required_isolation": "worktree",
                    }
                },
            }
            path.write_text(
                json.dumps({
                    "schema_version": "managed-issue-entrypoints/2",
                    "policy_version": "issue-start/1.0",
                    "managed": [entry],
                    "isolation_only": [entry],
                }),
                encoding="utf-8",
            )
            with patch("issue_start.gate.ENTRYPOINT_MANIFEST", path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                parse_dispatch_payload(fixer_payload())


class EvaluationTests(unittest.TestCase):
    def test_allow_contains_blocker_evidence_only(self):
        collector = Collector(load("closed_direct.json"))
        result = evaluate_issue_start(request(), collector_factory=lambda token: collector)
        self.assertEqual((result["result"], result["exit_code"]), ("ALLOW", 0))
        self.assertEqual(result["reason"], "ISSUE_START_ALLOWED")
        self.assertNotIn("branch_source_evidence", result)
        self.assertEqual(collector.waiver_calls, 0)

    def test_block_and_collection_error_preserve_verdict(self):
        for fixture, verdict in [("open_direct.json", "BLOCK"), ("cycle.json", "ERROR")]:
            result = evaluate_issue_start(
                request(), collector_factory=lambda token, f=fixture: Collector(load(f))
            )
            self.assertEqual(result["result"], verdict)
            self.assertNotIn("branch_source_evidence", result)

    def test_block_report_has_number_title_url_path_and_next_action(self):
        result = evaluate_issue_start(
            request(), collector_factory=lambda token: Collector(load("open_direct.json"))
        )
        item = result["blockers"][0]
        self.assertEqual(item["number"], 9)
        self.assertEqual(item["title"], "blocker 9")
        self.assertIn("/issues/9", item["url"])
        self.assertEqual(item["path"], ["example/repo#10", "example/repo#9"])
        self.assertIn("fresh invocation", item["next_action"])

    def test_repository_issue_binding_mismatch_is_error(self):
        bad = load("closed_direct.json")
        bad["subject"]["number"] = 11
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BLOCKER_BINDING_MISMATCH"):
            evaluate_issue_start(request(), collector_factory=lambda token: Collector(bad))


class HookLedgerMixin:
    """hook 経路の共通 fixture（テストは持たない）。"""

    def setUp(self):
        # Issue #309: ALLOW 経路は worktree 所有台帳へ `open` 起票する。実リポジトリの
        # `tmp/_worktree/` を汚さないよう、台帳の置き場をテストごとに隔離する。
        self._ledger_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._ledger_tmp.cleanup)
        self.ledger_root = Path(self._ledger_tmp.name).resolve()
        availability = patch("issue_start.gate._require_transport_available")
        availability.start()
        self.addCleanup(availability.stop)

    def ledger_entries(self):
        return worktree_ledger.read_ledger(self.ledger_root)["entries"]

    def managed_payload(self, task_name="issue_10"):
        return {
            "cwd": str(ROOT),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-implementer",
                "task_name": task_name,
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }


class HookTests(HookLedgerMixin, unittest.TestCase):
    def test_malformed_managed_dispatch_emits_deny(self):
        stdout = io.StringIO()
        rc = run_hook(
            stdin=io.StringIO(json.dumps(self.managed_payload("issue-10"))),
            stdout=stdout,
            stderr=io.StringIO(),
            cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
        )
        self.assertEqual(rc, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    @unittest.skip("Codex transport no longer reaches blocker evaluation")
    def test_codex_encrypted_message_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch(
            "issue_start.hook.resolve_github_token", return_value="credential-from-gh"
        ), patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0].issue, 10)
        self.assertEqual(evaluate.call_args.args[0].repository, "hiratashinnya/review-system")
        self.assertEqual(evaluate.call_args.kwargs["token"], "credential-from-gh")

    @unittest.skip("Codex transport no longer reaches blocker evaluation")
    def test_issue_317_equivalent_allows_with_mocked_gh_credential(self):
        repository = "hiratashinnya/review-system"
        snapshot = {
            "schema": "blocker-gate-snapshot/v1",
            "policy_version": POLICY_VERSION,
            "mode": "issue-start",
            "repository": repository,
            "subject": {"type": "issue", "number": 317},
            "roots": [f"{repository}#317"],
            "virtual_closed": [],
            "nodes": {
                f"{repository}#317": {
                    "node_id": "I317",
                    "state": "OPEN",
                    "blocked_by": [f"{repository}#316"],
                    "parent": None,
                    "children": [],
                },
                f"{repository}#316": {
                    "node_id": "I316",
                    "state": "CLOSED_COMPLETED",
                    "blocked_by": [],
                    "parent": None,
                    "children": [],
                },
            },
            "pages_complete": True,
            "errors": [],
            "fetched_at": "2026-08-09T00:00:00Z",
            "graphql_closing_set": [],
            "delivered_message_closing_set": [],
            "binding": {},
        }
        secret = "credential-from-mocked-gh"

        def evaluate(request, *, token, cwd=None):
            self.assertEqual(token, secret)
            return evaluate_issue_start(
                request,
                token=token,
                cwd=cwd,
                collector_factory=lambda actual: Collector(snapshot),
            )

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=secret), patch(
            "issue_start.hook.evaluate_issue_start", side_effect=evaluate
        ):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload("issue_317"))),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_claude_runtime_agent_alias_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
                "isolation": "worktree",
            },
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0], request())

    def test_missing_isolation_denies_before_any_github_evaluation(self):
        """Issue #350 AC4: `isolation` 欠落を hook が機械的に deny し、直し方を deny 文に載せる。"""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
            },
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start"
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_ISOLATION_NOT_WORKTREE", reason)
        # 「isolation を worktree にせよ」が deny 文だけで読み取れること（reason code だけにしない）。
        self.assertIn("isolation=worktree", reason)
        self.assertIn("actual=None", reason)
        # blocker 判定（GitHub API）まで進まずに落ちる＝dispatch 前に閉じる。
        evaluate.assert_not_called()

    @unittest.skip("Codex transport no longer reaches blocker evaluation")
    def test_block_deny_reason_preserves_actionable_blocker_report(self):
        blocker = {
            "number": 9,
            "repository": "example/repo",
            "title": "required blocker",
            "url": "https://github.com/example/repo/issues/9",
            "path": ["example/repo#10", "example/repo#9"],
            "next_action": "blockerをcloseしてfresh invocationで再試行する",
        }
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "BLOCK",
            "exit_code": 10,
            "reason": "OPEN_BLOCKER",
            "blockers": [blocker],
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        report = json.loads(reason.split(" blockers=", 1)[1])
        self.assertEqual(report, [blocker])


class CodexUnavailableTransportHookTests(unittest.TestCase):
    """Issue #452: Codex bindingなしで既存dispatch hookが最早期拒否する。"""

    def test_malformed_codex_dispatch_is_denied_without_binding_side_effects(self):
        cases = [
            {"agent_type": "issue-implementer"},
            {"agent_type": "issue-fixer", "task_name": None, "prompt": "mixed"},
            {"agent_type": "issue-implementer", "subagent_type": "issue-fixer"},
        ]
        for tool_input in cases:
            with self.subTest(tool_input=tool_input), \
                 patch("issue_start.gate._manifest") as manifest, \
                 patch("issue_start.gate.worktree_ledger.read_ledger") as ledger:
                with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TRANSPORT_UNAVAILABLE"):
                    parse_dispatch_payload({
                        "tool_name": "collaborationspawn_agent", "tool_input": tool_input,
                    }, runner=unittest.mock.Mock(side_effect=AssertionError("git called")))
                manifest.assert_not_called()
                ledger.assert_not_called()

    def test_existing_issue_start_hook_fails_closed_before_evaluation(self):
        payloads = [
            {
                "cwd": str(ROOT),
                "tool_name": "collaborationspawn_agent",
                "tool_input": {
                    "agent_type": "issue-implementer",
                    "task_name": "issue_10",
                    "message": "ENC[not-a-binding]",
                },
            },
            {
                "cwd": str(ROOT),
                "tool_name": "collaborationspawn_agent",
                "tool_input": {
                    "agent_type": "issue-fixer",
                    "task_name": "issue_10_fix_r1",
                    "message": "ENC[not-a-binding]",
                },
            },
        ]
        for payload in payloads:
            with self.subTest(role=payload["tool_input"]["agent_type"]):
                stdout = io.StringIO()
                with patch("issue_start.hook.evaluate_issue_start") as evaluate:
                    rc = run_hook(
                        stdin=io.StringIO(json.dumps(payload)),
                        stdout=stdout,
                        stderr=io.StringIO(),
                        cwd=ROOT,
                        now=LEDGER_NOW,
                    )
                self.assertEqual(rc, 0)
                decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn(
                    "ISSUE_START_TRANSPORT_UNAVAILABLE",
                    decision["permissionDecisionReason"],
                )
                self.assertIn("per-subagent workspace", decision["permissionDecisionReason"])
                evaluate.assert_not_called()


class WorktreeLedgerSideEffectTests(HookLedgerMixin, unittest.TestCase):
    """Issue #309 PR-1: ALLOW した dispatch を所有台帳へ `open` 起票する（**deny はしない**）。"""

    ALLOW_EVIDENCE = {
        "schema_version": "issue-start-evidence/1",
        "policy_version": "issue-start/1.0",
        "result": "ALLOW",
        "exit_code": 0,
        "reason": "ISSUE_START_ALLOWED",
    }

    def claude_payload(self):
        return {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }

    def run_allow(self, payload, *, ledger_root=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=dict(self.ALLOW_EVIDENCE)
        ):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root if ledger_root is None else ledger_root,
                now=LEDGER_NOW,
            )
        return rc, stdout, stderr

    def test_allow_opens_a_ledger_entry_bound_to_the_dispatch(self):
        rc, stdout, stderr = self.run_allow(self.claude_payload())
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "起票は dispatch を deny しない")
        entries = self.ledger_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["issue"], 10)
        self.assertEqual(entry["agent_type"], "issue-implementer")
        self.assertEqual(entry["branch_name"], "issue-297")
        self.assertEqual(entry["status"], "open")
        self.assertEqual(entry["dispatched_at"], "2026-08-19T04:11:07Z")
        # marker v1 に無い項目は推測せず None のまま（marker 拡張は後続 PR）。
        self.assertIsNone(entry["round"])
        self.assertIsNone(entry["handoff_path"])
        self.assertIsNone(entry["agent_id"])
        self.assertIsNone(entry["worktree_path"])
        # evidence（stderr）に entry_id が載る。
        evidence = json.loads(stderr.getvalue())
        self.assertEqual(evidence["ledger"]["entry_id"], entry["entry_id"])
        self.assertIsNone(evidence["ledger"]["error"])

    @unittest.skip("Codex prepare/binding ledger side effect retired by Issue #452")
    def test_codex_dispatch_does_not_open_a_second_legacy_entry(self):
        rc, _stdout, stderr = self.run_allow(self.managed_payload())
        self.assertEqual(rc, 0)
        self.assertEqual(self.ledger_entries(), [])
        evidence = json.loads(stderr.getvalue())
        self.assertEqual(evidence["ledger"]["entry_id"], "wl-000000000001")
        self.assertEqual(evidence["ledger"]["platform"], "codex")

    def test_broken_ledger_now_denies_fail_close(self):
        """Issue #354 PR-3 で **fail-open → fail-close** へ倒した箇所（契約変更の明示）。

        PR-1（#309）では台帳が壊れていても ALLOW のままだった——観測が正確になったことを
        実測してから deny を有効化する「統制を先に、付与は別 PR」の順序を守るため。
        PR-3 は残留 worktree を deny の材料にするので、**台帳を一意に読めない間は
        残留の有無を判定できない**＝通してはならない。

        起票（`record_open_entry`）そのものは今も fail-open で、
        :meth:`test_record_open_entry_never_raises` がその不変条件を保っている。
        """
        broken = self.ledger_root / "broken"
        broken.mkdir()
        path = worktree_ledger.ledger_path(broken, create_dir=True)
        path.write_text("{not json", encoding="utf-8")
        rc, stdout, _stderr = self.run_allow(self.claude_payload(), ledger_root=broken)
        self.assertEqual(rc, 0)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_WORKTREE_LEDGER_ERROR", reason)
        self.assertIn("LEDGER_INVALID_JSON", reason)
        self.assertIn("fail-close", reason)

    def test_allow_evidence_carries_the_worktree_residue_report(self):
        """FR-W12: 解放の実施/未実施が台帳と突き合わせられる形で evidence に残る。"""
        _rc, _stdout, stderr = self.run_allow(self.claude_payload())
        residue = json.loads(stderr.getvalue())["worktree_residue"]
        self.assertEqual(residue["stale"], [])
        self.assertEqual(residue["unclaimed"], [])
        self.assertEqual(residue["swept"], [])
        self.assertIn("claimed", residue)

    def test_denied_dispatch_records_nothing(self):
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload("issue-10"))),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertEqual(self.ledger_entries(), [], "deny した dispatch は起票しない")

    def test_record_open_entry_never_raises(self):
        """gate の起票関数は**どんな入力でも例外を投げない**（fail-open の実体）。"""
        for label, payload in (
            ("empty", {}),
            ("no-tool-input", {"tool_name": "Task"}),
            ("tool-input-not-a-mapping", {"tool_name": "Task", "tool_input": "x"}),
            ("no-agent-type", {"tool_name": "Task", "tool_input": {"prompt": "x"}}),
        ):
            with self.subTest(label=label):
                result = record_open_entry(
                    payload, request(), now=LEDGER_NOW, repo_root=self.ledger_root
                )
                self.assertIsNone(result["entry_id"])
                self.assertEqual(result["error"], "LEDGER_AGENT_TYPE_UNREADABLE")
        self.assertEqual(self.ledger_entries(), [])

    def test_record_open_entry_converges_on_the_main_worktree(self):
        """linked worktree から起動しても台帳は main worktree 側に1つだけ作られる。"""
        main = self.ledger_root / "main"
        gitdir = main / ".git" / "worktrees" / "agent-abc"
        gitdir.mkdir(parents=True)
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        linked = main / ".claude" / "worktrees" / "agent-abc"
        linked.mkdir(parents=True)
        (linked / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")

        result = record_open_entry(
            self.claude_payload(), request(), now=LEDGER_NOW, repo_root=linked
        )
        self.assertIsNotNone(result["entry_id"])
        self.assertTrue((main / "tmp" / "_worktree" / "ledger.json").is_file())
        self.assertFalse((linked / "tmp").exists())


class IsolationOnlyHookTests(HookLedgerMixin, unittest.TestCase):
    """Issue #354 PR-4: hook 経路での `isolation_only`（`issue-fixer`）の挙動。"""

    def run_dispatch(self, payload):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start"
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        return stdout.getvalue(), stderr.getvalue(), evaluate

    def test_allowed_without_touching_the_blocker_gate(self):
        stdout, stderr, evaluate = self.run_dispatch(fixer_payload())
        self.assertEqual(stdout, "", "分離だけを課す区分は deny しない")
        # 是正ラウンドは GitHub API を叩かない（API 不通でレビュー是正まで止めないため）。
        evaluate.assert_not_called()
        evidence = json.loads(stderr)
        self.assertEqual(evidence["result"], "ISOLATION_ONLY")
        self.assertEqual(evidence["reason"], "ISSUE_START_ISOLATION_ONLY_ALLOWED")
        self.assertIsNone(evidence["blocker_evidence"])
        self.assertEqual(evidence["binding"]["agent_type"], "issue-fixer")
        self.assertEqual(evidence["binding"]["round"], 1)
        self.assertIn("claimed", evidence["worktree_residue"])

    def test_the_ledger_entry_carries_issue_round_branch_and_handoff_path(self):
        """FR-W4 完全化: marker の値を推測せずそのまま台帳へ載せる。"""
        _stdout, stderr, _evaluate = self.run_dispatch(fixer_payload())
        entries = self.ledger_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["issue"], 354)
        self.assertEqual(entry["agent_type"], "issue-fixer")
        self.assertEqual(entry["round"], 1)
        self.assertEqual(entry["branch_name"], "claude/issue-354-pr4")
        self.assertEqual(entry["handoff_path"], "tmp/_handoff/issue-fixer--issue-354-fix1.yaml")
        self.assertEqual(entry["status"], "open")
        self.assertEqual(json.loads(stderr)["ledger"]["entry_id"], entry["entry_id"])

    def test_denied_dispatch_records_nothing_and_never_evaluates(self):
        stdout, _stderr, evaluate = self.run_dispatch(fixer_payload(isolation=None))
        decision = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_ISOLATION_NOT_WORKTREE", reason)
        self.assertIn("isolation=worktree", reason)
        evaluate.assert_not_called()
        self.assertEqual(self.ledger_entries(), [], "deny した dispatch は起票しない")


class WorktreeResidueDenyTests(HookLedgerMixin, unittest.TestCase):
    """Issue #354 PR-3（候補C）: 残留 worktree のある状態での次 dispatch を deny する。

    #354 が実測した事象は「残留 worktree があるのに `pr-reviewer` を dispatch し、
    レビューアが古い作業ツリーを掴んだ」——つまり **unmanaged 側**で起きた。したがって
    この deny は managed dispatch に限らず**全 `Task` dispatch** に掛かる。
    """

    def bind(self, agent_id, *, agent_type="issue-implementer", issue=354):
        worktree_ledger.open_entry(
            self.ledger_root, issue=issue, agent_type=agent_type, round=None,
            branch_name=None, handoff_path=None, now=LEDGER_NOW,
        )
        return worktree_ledger.bind_agent(
            self.ledger_root, agent_type=agent_type, agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )

    def make_worktree(self, name):
        path = self.ledger_root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path

    def advance(self, entry_id, *statuses):
        for status in statuses:
            worktree_ledger.mark(self.ledger_root, entry_id, status, now=LEDGER_NOW)

    def managed_dispatch(self):
        return {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }

    def unmanaged_dispatch(self):
        """manifest に載っていない agent_type（`parse_dispatch_payload` は `None` を返す）。"""
        return {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "pr-reviewer", "prompt": "review PR #401"},
        }

    def run_dispatch(self, payload):
        stdout, stderr = io.StringIO(), io.StringIO()
        allow = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=dict(allow)
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout, stderr=stderr,
                cwd=ROOT, ledger_root=self.ledger_root, now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        return stdout.getvalue(), stderr.getvalue(), evaluate

    def deny_reason(self, payload):
        stdout, _stderr, evaluate = self.run_dispatch(payload)
        decision = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        # 残留判定は GitHub API より前（ローカルの状態だけで決まる）。
        evaluate.assert_not_called()
        return decision["permissionDecisionReason"]

    def test_uncollected_residue_denies_with_the_remediation_command(self):
        """`stale` / `stopped` / `collected` はいずれも「回収が完了していない」＝deny。"""
        cases = {
            "stale": ("stale",),
            "stopped": ("stopped",),
            "collected": ("stopped", "collected"),
        }
        for label, statuses in cases.items():
            with self.subTest(status=label):
                self.setUp()
                self.make_worktree("agent-left")
                entry_id = self.bind("left")
                self.advance(entry_id, *statuses)
                reason = self.deny_reason(self.managed_dispatch())
                self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
                # entry_id / status / worktree_path が deny 文だけで読み取れること。
                self.assertIn(entry_id, reason)
                self.assertIn(label, reason)
                self.assertIn(".claude/worktrees/agent-left", reason)
                # 解消コマンドを必ず載せる（過剰 deny の緩和はここで行う）。
                self.assertIn(
                    "python3 -m gitgate collect-worktree --entry <entry-id>", reason
                )
                self.assertIn("worktree-forget", reason, "逃げ道も併記する")

    def test_worktree_not_in_the_ledger_denies_as_unclaimed(self):
        self.make_worktree("agent-nobody")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_UNCLAIMED", reason)
        self.assertIn(".claude/worktrees/agent-nobody", reason)
        self.assertIn("worktree-release", reason)
        self.assertIn("--force-uncollected", reason)

    def test_broken_ledger_denies_fail_close(self):
        path = worktree_ledger.ledger_path(self.ledger_root, create_dir=True)
        path.write_text("{not json", encoding="utf-8")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_LEDGER_ERROR", reason)
        self.assertIn("LEDGER_INVALID_JSON", reason)

    def test_a_live_running_dispatch_is_not_denied(self):
        """`running`＝live な dispatch が正当に占有している。deny しない。"""
        self.make_worktree("agent-live")
        self.bind("live")
        stdout, stderr, evaluate = self.run_dispatch(self.managed_dispatch())
        self.assertEqual(stdout, "", "live な worktree は残留ではない")
        evaluate.assert_called_once()
        residue = json.loads(stderr)["worktree_residue"]
        self.assertEqual(residue["running"], [".claude/worktrees/agent-live"])
        self.assertEqual(residue["unclaimed"], [])

    def test_stopped_is_claimed_for_unclaimed_but_still_a_residue(self):
        """`stopped` の二重の性質の境界（Issue #354 PR-3 の要注意点）。

        回収処理中の worktree を `ISSUE_START_WORKTREE_UNCLAIMED` として誤検出しては
        ならない（＝claimed 集合に含める）が、`stopped` のまま止まっている＝回収段が
        失敗している可能性があるので residue としては検出する。**deny の reason は
        UNCLAIMED ではなく RESIDUE になる**（解消コマンドが `collect-worktree` であって
        `worktree-release --force-uncollected` ではないから）。
        """
        self.make_worktree("agent-stopping")
        entry_id = self.bind("stopping")
        self.advance(entry_id, "stopped")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
        self.assertNotIn("ISSUE_START_WORKTREE_UNCLAIMED", reason)
        self.assertIn("collect-worktree", reason)

    def test_unmanaged_dispatch_is_denied_too(self):
        """#354 の実測事象（残留があるのに `pr-reviewer` を dispatch）を正面から塞ぐ。"""
        self.make_worktree("agent-left")
        entry_id = self.bind("left")
        self.advance(entry_id, "stale")
        reason = self.deny_reason(self.unmanaged_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)

    def test_unmanaged_dispatch_without_residue_still_emits_evidence(self):
        """F-354-08: unmanaged の ALLOW でも stdout は無出力のまま、stderr に残留判定の
        evidence（swept / claimed / unclaimed を含む）が残る（従来は無出力だった）。"""
        stdout, stderr, evaluate = self.run_dispatch(self.unmanaged_dispatch())
        self.assertEqual(stdout, "", "unmanaged は素通し（deny しない）")
        evaluate.assert_not_called()
        evidence = json.loads(stderr)
        self.assertEqual(evidence["result"], "UNMANAGED")
        residue = evidence["worktree_residue"]
        self.assertEqual(residue["stale"], [])
        self.assertEqual(residue["unclaimed"], [])
        self.assertEqual(residue["swept"], [])
        self.assertIn("claimed", residue)

    def test_orphan_running_entry_is_swept_then_denied(self):
        """worktree が消えた `running` は掃引で `stale` に落ち、その場で deny される。

        放置すると `resolve_worktree_for_agent` が恒久的に `ambiguous-running` になり、
        以後どの dispatch も束縛できなくなる（PR-1 の既知の詰まり）。
        """
        entry_id = self.bind("vanished")  # ディスク上に worktree を作らない
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
        self.assertIn(entry_id, reason)
        entries = worktree_ledger.read_ledger(self.ledger_root)["entries"]
        self.assertEqual(entries[0]["status"], "stale")

    def test_residue_deny_does_not_open_a_ledger_entry(self):
        self.make_worktree("agent-left")
        entry_id = self.bind("left")
        self.advance(entry_id, "stale")
        self.deny_reason(self.managed_dispatch())
        self.assertEqual(len(self.ledger_entries()), 1, "deny した dispatch は起票しない")

    def test_blocker_deny_evidence_shape_is_unchanged(self):
        """回帰: 既存 blocker gate 経路の deny 文（`blockers=` の JSON）が壊れていない。"""
        blocker = {
            "number": 9,
            "repository": "example/repo",
            "title": "required blocker",
            "url": "https://github.com/example/repo/issues/9",
            "path": ["example/repo#10", "example/repo#9"],
            "next_action": "blockerをcloseしてfresh invocationで再試行する",
        }
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "BLOCK",
            "exit_code": 10,
            "reason": "OPEN_BLOCKER",
            "blockers": [blocker],
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_dispatch())),
                stdout=stdout, stderr=io.StringIO(),
                cwd=ROOT, ledger_root=self.ledger_root, now=LEDGER_NOW,
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("BLOCK OPEN_BLOCKER", reason)
        self.assertEqual(json.loads(reason.split(" blockers=", 1)[1]), [blocker])


class _GateFakeGit:
    """`assert_no_worktree_residue` の `_finish_deferred_releases` 用の最小 git スタブ。

    `worktree_release` が呼ぶのは `git worktree list --porcelain` / `git worktree remove` /
    `git worktree prune` だけ（`branch_name` が None のエントリでは `git fetch` 等は走らない）。
    """

    def __init__(self, root, *, linked=(), fail_remove_stderr=None):
        self.root = Path(root)
        self.linked = list(linked)
        self.fail_remove_stderr = fail_remove_stderr
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "worktree", "list"]:
            blocks = [f"worktree {self.root}\nHEAD {'0' * 40}\nbranch refs/heads/main\n"]
            for rel in self.linked:
                blocks.append(f"worktree {self.root / rel}\nHEAD {'0' * 40}\n")
            return subprocess.CompletedProcess(argv, 0, "\n".join(blocks) + "\n", "")
        if argv[:3] == ["git", "worktree", "remove"]:
            if self.fail_remove_stderr is not None:
                return subprocess.CompletedProcess(argv, 1, "", self.fail_remove_stderr)
            shutil.rmtree(argv[-1], ignore_errors=True)
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")


class DeferredReleaseGateTests(unittest.TestCase):
    """Issue #464: `release_pending`（回収済み・削除だけ git ロックで遅延）の gate 側の扱い。

    * `ISSUE_START_WORKTREE_RESIDUE` / `ISSUE_START_WORKTREE_UNCLAIMED` で deny しない
      ——成果物は `collected_to` へ退避済みで失われていない。
    * ロックが外れていれば `_finish_deferred_releases` が削除を完了させ `released` にする。
      worktree ディレクトリが既に消えていても冪等に `released` へ進める。
    * fail-close は弱めない——`stale` / `collected` は従来どおり deny する。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def make_worktree(self, name):
        path = self.root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path

    def entry_at(self, *statuses, agent_id="rp", issue=464, on_disk=True):
        if on_disk:
            self.make_worktree(f"agent-{agent_id}")
        worktree_ledger.open_entry(
            self.root, issue=issue, agent_type="issue-implementer", round=None,
            branch_name=None, handoff_path=None, now=LEDGER_NOW,
        )
        entry_id = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )
        for status in statuses:
            worktree_ledger.mark(self.root, entry_id, status, now=LEDGER_NOW)
        return entry_id

    def status_of(self, entry_id):
        return {
            e["entry_id"]: e
            for e in worktree_ledger.read_ledger(self.root)["entries"]
        }[entry_id]["status"]

    def entry(self, entry_id):
        for item in worktree_ledger.read_ledger(self.root)["entries"]:
            if item.get("entry_id") == entry_id:
                return item
        return None

    def entry_with_branch(
        self, *statuses, agent_id="rp", issue=464,
        branch_name="claude/issue-464-fix", on_disk=True,
    ):
        if on_disk:
            self.make_worktree(f"agent-{agent_id}")
        worktree_ledger.open_entry(
            self.root, issue=issue, agent_type="issue-implementer", round=None,
            branch_name=branch_name, handoff_path=None, now=LEDGER_NOW,
        )
        entry_id = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )
        for status in statuses:
            worktree_ledger.mark(self.root, entry_id, status, now=LEDGER_NOW)
        return entry_id

    def test_release_pending_does_not_deny_and_the_gate_finishes_the_release(self):
        entry_id = self.entry_at("stopped", "collected", "release_pending")
        git = _GateFakeGit(self.root, linked=[".claude/worktrees/agent-rp"])
        report = assert_no_worktree_residue(
            repo_root=self.root, now=LEDGER_NOW, runner=git
        )
        self.assertEqual(report["stale"], [], "release_pending は residue ではない")
        self.assertEqual(report["unclaimed"], [], "削除待ちの占有は孤児ではない")
        self.assertEqual(
            [item["entry_id"] for item in report["deferred_release_finished"]], [entry_id]
        )
        self.assertTrue(report["deferred_release_finished"][0]["released"])
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertFalse((self.root / ".claude" / "worktrees" / "agent-rp").exists())

    def test_release_pending_with_a_vanished_worktree_advances_to_released(self):
        # ハーネスの auto-clean で worktree ごと消えているケース（症状B）。
        entry_id = self.entry_at(
            "stopped", "collected", "release_pending", on_disk=False
        )
        git = _GateFakeGit(self.root, linked=[])
        report = assert_no_worktree_residue(
            repo_root=self.root, now=LEDGER_NOW, runner=git
        )
        self.assertEqual(report["stale"], [])
        self.assertEqual(report["unclaimed"], [])
        self.assertTrue(report["deferred_release_finished"][0]["released"])
        self.assertEqual(self.status_of(entry_id), "released")

    def test_still_locked_release_pending_does_not_block_the_dispatch(self):
        entry_id = self.entry_at("stopped", "collected", "release_pending")
        git = _GateFakeGit(
            self.root, linked=[".claude/worktrees/agent-rp"],
            fail_remove_stderr=(
                "fatal: cannot remove a locked working tree, lock reason: still busy\n"
            ),
        )
        report = assert_no_worktree_residue(
            repo_root=self.root, now=LEDGER_NOW, runner=git
        )
        # まだロックされていても deny しない（成果物は安全）。
        self.assertEqual(report["stale"], [])
        self.assertEqual(report["unclaimed"], [])
        self.assertFalse(report["deferred_release_finished"][0]["released"])
        self.assertEqual(
            report["deferred_release_finished"][0]["error"], "WORKTREE_REMOVE_FAILED"
        )
        self.assertEqual(self.status_of(entry_id), "release_pending", "次回へ持ち越す")
        self.assertIn(".claude/worktrees/agent-rp", report["claimed"])
        self.assertIn(".claude/worktrees/agent-rp", report["release_pending"])

    def test_stale_and_collected_still_deny_so_fail_close_is_intact(self):
        for statuses in (("stale",), ("stopped", "collected")):
            with self.subTest(statuses=statuses):
                self.setUp()
                self.entry_at(*statuses, agent_id="x")
                git = _GateFakeGit(self.root, linked=[".claude/worktrees/agent-x"])
                with self.assertRaises(IssueStartError) as ctx:
                    assert_no_worktree_residue(
                        repo_root=self.root, now=LEDGER_NOW, runner=git
                    )
                self.assertEqual(ctx.exception.reason, "ISSUE_START_WORKTREE_RESIDUE")

    def test_release_pending_escalates_to_stale_after_repeated_failures(self):
        """Issue #464・F-464-02: 恒久的に削除できない ``release_pending`` は無制限に
        リトライされず、連続失敗が閾値（3）を超えたら ``stale`` へ落ちて通常の
        ``ISSUE_START_WORKTREE_RESIDUE`` に合流する。"""
        entry_id = self.entry_at("stopped", "collected", "release_pending")
        git = _GateFakeGit(
            self.root, linked=[".claude/worktrees/agent-rp"],
            fail_remove_stderr=(
                "fatal: cannot remove a locked working tree, lock reason: still busy\n"
            ),
        )
        for attempt in range(1, 4):
            with self.subTest(attempt=attempt):
                report = assert_no_worktree_residue(
                    repo_root=self.root, now=LEDGER_NOW, runner=git
                )
                self.assertEqual(report["stale"], [], f"attempt {attempt} は deny しない")
                self.assertEqual(self.status_of(entry_id), "release_pending")
        with self.assertRaises(IssueStartError) as ctx:
            assert_no_worktree_residue(repo_root=self.root, now=LEDGER_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "ISSUE_START_WORKTREE_RESIDUE")
        self.assertEqual(self.status_of(entry_id), "stale", "4回目で stale へ落ちる")
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertTrue(
            any("4回連続で失敗" in note and "Issue #464" in note for note in notes), notes
        )

    def test_generic_exception_during_retry_does_not_deny_but_is_recorded(self):
        """Issue #464・F-464-03: ``WorktreeError`` 以外（runner 起因の ``TypeError`` 等）も
        ``_finish_deferred_releases`` の中で吸収され、台帳は健全なまま dispatch を続ける
        （旧実装は外側の ``except Exception`` に抜けて
        ``ISSUE_START_WORKTREE_LEDGER_ERROR`` で全 dispatch を deny していた）。"""
        entry_id = self.entry_at("stopped", "collected", "release_pending")

        class _RaisingGit:
            def __init__(self):
                self.calls = []

            def __call__(self, argv, **kwargs):
                self.calls.append(list(argv))
                raise TypeError("boom")

        git = _RaisingGit()
        report = assert_no_worktree_residue(repo_root=self.root, now=LEDGER_NOW, runner=git)
        self.assertEqual(report["stale"], [])
        self.assertEqual(report["unclaimed"], [])
        self.assertFalse(report["deferred_release_finished"][0]["released"])
        self.assertEqual(report["deferred_release_finished"][0]["error"], "TypeError")
        self.assertEqual(self.status_of(entry_id), "release_pending")

    def test_deferred_release_does_not_fetch_or_delete_the_branch_ref(self):
        """Issue #464・F-464-06: 毎 dispatch の事前チェック（``_finish_deferred_releases``）は
        ``cleanup_branch_ref=False`` を渡すため、削除成功時でも ``git fetch``／
        ``git branch -D`` は一切走らない（フル掃除は ``SessionStart`` フックへ委ねる）。"""
        entry_id = self.entry_with_branch("stopped", "collected", "release_pending")
        git = _GateFakeGit(self.root, linked=[".claude/worktrees/agent-rp"])
        report = assert_no_worktree_residue(repo_root=self.root, now=LEDGER_NOW, runner=git)
        self.assertTrue(report["deferred_release_finished"][0]["released"])
        self.assertEqual(self.status_of(entry_id), "released")
        fetch_calls = [argv for argv in git.calls if argv[:2] == ["git", "fetch"]]
        self.assertEqual(fetch_calls, [], "ローカルブランチ ref 掃除の git fetch はホットパスから外れている")
        branch_delete_calls = [
            argv for argv in git.calls if argv[:3] == ["git", "branch", "-D"]
        ]
        self.assertEqual(branch_delete_calls, [])


if __name__ == "__main__":
    unittest.main()
