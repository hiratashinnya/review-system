"""Regression tests for PR #816 review findings: ID, recovery, and trusted policy."""
import hashlib
import hmac
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from karte.finding_record import Finding
from karte.karte_record import Karte
from codex_worktree_exec.triage_round_ids import ingested_finding_ids
from codex_worktree_exec.triage_review_capture import capture_existing
from codex_worktree_exec.triage_binding_capture import binding_from_capture
from codex_worktree_exec.triage_binding_verify import verify_binding_capture, sign_binding
from codex_worktree_exec.source_snapshot import verify_source_snapshot
from codex_worktree_exec.triager_dispatch import require_clean_tracked
from issue_start.triage_existing_capture import execute_with_capture


EXISTING = """### F-783-01
harm: real
harm_detail: data loss
severity: major
scope: in
locus: old.py
summary: existing finding
evidence: observed before
expected: preserved
recheck: run old test
"""
NEW = """### new
harm: real
harm_detail: logic error
severity: major
scope: in
locus: new.py
summary: newly detected defect
evidence: observed now
expected: corrected
recheck: run new test
"""


def record(fid, source, rounds):
    from karte.review_report import parse_review
    item = parse_review(source, 783)[0]
    return Finding(id=fid, status=item.status, harm=item.harm,
                   harm_detail=item.harm_detail, severity=item.severity,
                   locus=list(item.locus), summary=item.summary,
                   evidence=item.evidence, expected=item.expected,
                   recheck=item.recheck, rounds=rounds)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class TriageRepairTest(unittest.TestCase):
    def test_new_and_existing_findings_use_exact_karte_ids(self):
        body = (EXISTING + "\n" + NEW).encode()
        karte = Karte(issue=783, findings=[
            record("F-783-01", EXISTING, [1, 2]),
            record("F-783-02", NEW, [2]),
        ])
        with patch("codex_worktree_exec.triage_round_ids.karte_loader.load_karte",
                   return_value=(None, karte)):
            ids = ingested_finding_ids(body, Path("/unused"), 783, 2)
            self.assertEqual(ids, ["F-783-01", "F-783-02"])
            karte.findings[1].summary = "tampered"
            with self.assertRaisesRegex(ValueError, "differs"):
                ingested_finding_ids(body, Path("/unused"), 783, 2)
            karte.findings[1].summary = "newly detected defect"
            karte.findings[1].rounds = [1]
            with self.assertRaisesRegex(ValueError, "count"):
                ingested_finding_ids(body, Path("/unused"), 783, 2)

    def test_receipt_and_proposal_bind_assigned_ids(self):
        body = (EXISTING + "\n" + NEW).encode()
        approval = {"issue": 783, "run_id": "r", "target_key": "k",
                    "snapshot_oid": "a" * 40, "input_digest": "b" * 64,
                    "source_changes": {}, "approval_context": "approved",
                    "triage_phase": "review",
                    "materials": {"verification_design": {"content": "VD"},
                                  "solution_planning": {"content": "CP"}}}
        key = b"k" * 32
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            captured = capture_existing(body, root, approval, "c" * 40, key,
                                        "review", 2, assigned_ids=["F-783-01", "F-783-02"])
            with patch("codex_worktree_exec.triage_binding_capture.github_evidence",
                       return_value={"issue_body": "AC", "change": "diff"}):
                binding = binding_from_capture(*captured, root, key, pr=816,
                                               phase="review", round_no=2)
            verify_binding_capture(binding, key)
            ids = [item["finding_id"] for item in json.loads(binding["review"])["findings"]]
            self.assertEqual(ids, ["F-783-01", "F-783-02"])
            changed = dict(binding)
            review = json.loads(changed["review"])
            review["findings"][1]["finding_id"] = "F-783-03"
            changed["review"] = json.dumps(review)
            changed["binding_signature"] = sign_binding(
                {k: v for k, v in changed.items() if k != "binding_signature"}, key)
            with self.assertRaises(ValueError):
                verify_binding_capture(changed, key)
            with self.assertRaises(ValueError):
                capture_existing(body, root, approval, "c" * 40, key, "review", 2,
                                 assigned_ids=["F-783-01", "F-783-01"])

    def test_retry_after_successful_ingest_only_captures_existing_output(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "tmp").mkdir()
            (root / "tmp/review.md").write_text(EXISTING)
            request = SimpleNamespace(role="pr-reviewer",
                                      output_file=Path("tmp/review.md"),
                                      binding_file=Path("tmp/binding.json"))
            approval = {"issue": 783, "triage_phase": "review", "run_id": "r",
                        "target_key": "k", "snapshot_oid": "a" * 40,
                        "input_digest": "b" * 64, "source_changes": {},
                        "approval_context": "approved"}
            with patch("issue_start.triage_existing_capture.paths.main_worktree_root",
                       return_value=root), \
                 patch("issue_start.triage_existing_capture.review_envelope_of",
                       return_value={"phase": "implementation"}), \
                 patch("issue_start.triage_existing_capture.approved_materials",
                       return_value=approval), \
                 patch("issue_start.triage_existing_capture.progress_target",
                       return_value=(783, 3)), \
                 patch("issue_start.triage_existing_capture._head",
                       return_value="c" * 40), \
                 patch("issue_start.triage_existing_capture.ingested_finding_ids",
                       return_value=["F-783-01"]), \
                 patch("issue_start.triage_existing_capture.binding_from_capture",
                       side_effect=[ValueError("GitHub temporarily unavailable"),
                                    {"recovered": True}]), \
                 patch("issue_start.triage_existing_capture.capture_target") as start:
                calls = []
                invoke = lambda: execute_with_capture(
                    request, ["review"], root, {}, b"k" * 32,
                    816, "review", 2, "tmp/triage.json",
                    lambda *args, **kwargs: calls.append(True))
                with self.assertRaisesRegex(ValueError, "GitHub temporarily unavailable"):
                    invoke()
                self.assertFalse((root / "tmp/triage.json").exists())
                self.assertEqual(invoke(), 0)
                self.assertEqual(calls, [])
                start.assert_not_called()
            self.assertEqual(json.loads((root / "tmp/triage.json").read_text()),
                             {"recovered": True})

    def test_readonly_source_gate_rejects_tracked_worktree_edits(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            git(root, "init", "-q")
            (root / "policy.md").write_text("trusted")
            git(root, "add", "policy.md")
            git(root, "-c", "user.name=test", "-c", "user.email=t@example.com",
                "commit", "-qm", "initial")
            oid = git(root, "rev-parse", "HEAD")
            with patch("codex_worktree_exec.source_snapshot.verify_untracked_sources"):
                verify_source_snapshot(root, oid, 783)
                require_clean_tracked(root)
                (root / "policy.md").write_text("changed")
                # Shared snapshot semantics stay unchanged for other roles.
                verify_source_snapshot(root, oid, 783)
                with self.assertRaisesRegex(ValueError, "triager worktree"):
                    require_clean_tracked(root)

    def test_committed_harm_and_policy_reject_dirty_bytes(self):
        from finding_triager import adapter
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            git(root, "init", "-q")
            role = root / ".ai/agents/finding-triager.md"
            harm = root / ".ai/skills/review-harm/SKILL.md"
            policy = root / ".ai/guidance/triage-policy-v1.json"
            for path, data in ((role, "role"), (harm, "harm"), (policy, "{}")):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data)
            git(root, "add", ".")
            git(root, "-c", "user.name=test", "-c", "user.email=t@example.com",
                "commit", "-qm", "trusted")
            expected = {"issue": 783, "phase": "review", "round": 1,
                        "run_id": "r", "target_key": "k",
                        "input_digest": "a" * 64, "snapshot_oid": "b" * 40,
                        "review_oid": "c" * 40}
            context = {"issue": 783, "snapshot_oid": "b" * 40, "review_oid": "c" * 40,
                       "input_digest": "a" * 64, "approval_ref": "approved",
                       "documents": dict.fromkeys(("ac", "vd_cp", "design", "change"), "evidence")}
            context_raw = json.dumps(context).encode()
            digest = hashlib.sha256(context_raw).hexdigest()
            review = dict(expected, context_sha256=digest, producer="pr-reviewer",
                          reviewer_worktree="/reviewer", findings=[])
            raw = json.dumps(review).encode()
            key = b"k" * 32
            signature = hmac.new(key, raw, hashlib.sha256).hexdigest()
            with patch.object(adapter, "ROOT", root), \
                 patch.object(adapter, "DEFAULT_POLICY", policy), \
                 patch.object(adapter, "check_harm_sync", return_value=False):
                adapter.prepare(raw, signature, key, expected, context_raw, digest)
                harm.write_text("uncommitted")
                with self.assertRaises(ValueError):
                    adapter.prepare(raw, signature, key, expected, context_raw, digest)
                harm.write_text("harm")
                policy.write_text('{"policy_id":"changed"}')
                with patch.object(adapter, "prepare", return_value=("", review)), \
                     patch.object(adapter, "verify_capture", return_value=[]):
                    with self.assertRaises(ValueError):
                        adapter.propose(raw, signature, key, expected, context_raw, digest,
                                        b"capture", "signature", b"x" * 32)


if __name__ == "__main__":
    unittest.main()
