"""Issue #782: positive, invalid, concurrent, and actor-role checks."""

import hashlib
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from advisory.catalog import check_catalog, load_catalog
from advisory.cli import main
from advisory.operations import modify, new
from advisory.paths import record_path
from advisory.storage import sha


def attempt_parallel_update(data):
    root, key, expected, value = data
    try:
        return modify(Path(root), "main", key, expected, "amend",
                      reason="parallel CAS", changes={"evidence": value})
    except ValueError:
        return "conflict"


class AdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        def git(*args):
            return subprocess.run(["git", "-C", str(self.root), *args],
                                  check=True, capture_output=True)
        self.git = git
        git("init", "-b", "main")
        git("config", "user.email", "advisory@example.test")
        git("config", "user.name", "Advisory test")
        (self.root / "seed").write_text("seed")
        git("add", "seed")
        git("commit", "-m", "seed")
        self.role = mock.patch.dict(os.environ, {"ADVISORY_CALLER_ROLE": "main-thread"})
        self.role.start()
        self.addCleanup(self.role.stop)

    def create(self, topic="改善案を整理", on="2026-11-10", **kw):
        return new(self.root, "main", topic=topic, created_on=on,
                   sources=["issue:782", "finding:F-782-1"],
                   evidence="observed", recommendation="consider fix",
                   triage_rationale="harm none", policy_version="1.0", **kw)

    def test_round_trip_and_derived_list(self):
        key, checksum = self.create()
        path = record_path(self.root, key)
        self.assertEqual(checksum, sha(path.read_bytes()))
        self.assertEqual(check_catalog(load_catalog(self.root)), [])
        code = main(["--root", str(self.root), "check", "--against-ref", "main",
                     "--require-base"])
        self.assertEqual(code, 0)
        self.assertEqual(main(["--root", str(self.root), "list",
                               "--today", "2026-12-11"]), 0)

    def test_forbid_non_main_writer(self):
        with mock.patch.dict(os.environ, {"ADVISORY_CALLER_ROLE": "pr-reviewer"}):
            with self.assertRaisesRegex(ValueError, "main-thread"):
                self.create()

    def test_duplicate_and_similarity_screen(self):
        self.create()
        with self.assertRaisesRegex(ValueError, "duplicate topic"):
            self.create(on="2026-11-11")
        with self.assertRaisesRegex(ValueError, "possible semantic duplicate"):
            self.create(topic="改善案を整理する")
        self.create(topic="改善案を整理する", duplicate_reason="different artifact")

    def test_conflicting_update_refuses_to_overwrite(self):
        key, old = self.create()
        newer = modify(self.root, "main", key, old, "amend", reason="new proof",
                       changes={"evidence": "proof 2"})
        self.assertNotEqual(old, newer)
        with self.assertRaisesRegex(ValueError, "lost update"):
            modify(self.root, "main", key, old, "amend", reason="stale",
                   changes={"evidence": "bad"})
        self.assertEqual(load_catalog(self.root)[key]["evidence"], "proof 2")

    def test_transitions_and_promotion(self):
        key, first = self.create()
        with self.assertRaisesRegex(ValueError, "state transition"):
            modify(self.root, "main", key, first, "transition", reason="invalid",
                   changes={"status": "promoted"})
        second = modify(self.root, "main", key, first, "transition", reason="reviewed",
                        changes={"status": "triaged"})
        with mock.patch("advisory.operations.verify_existing_issue") as verify:
            self.assertEqual(main(["--root", str(self.root), "promote", "--base-ref",
                                   "main", "--id", key, "--expected-sha256", second,
                                   "--reason", "existing issue", "--existing-issue",
                                   "owner/repo#42"]), 0)
            verify.assert_called_once_with("owner/repo#42")
        self.assertEqual(load_catalog(self.root)[key]["status"], "promoted")

    def test_manual_tamper_detected(self):
        key, _ = self.create()
        path = record_path(self.root, key)
        path.write_text(path.read_text().replace('evidence = "observed"',
                                                  'evidence = "forged"'))
        self.assertEqual(main(["--root", str(self.root), "check"]), 4)

    def test_missing_advisory_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing related advisory"):
            self.create(related_ids=["ADV-20261110-unknown"])

    def test_remote_base_advance_is_refused(self):
        key, _ = self.create()
        self.git("add", ".ai")
        self.git("commit", "-m", "registered")
        self.git("checkout", "-b", "feature")
        old = sha(record_path(self.root, key).read_bytes())
        modify(self.root, "main", key, old, "amend", reason="feature edit",
               changes={"evidence": "feature"})
        self.git("add", ".ai")
        self.git("commit", "-m", "feature edit")
        self.git("checkout", "main")
        record_path(self.root, key).write_text(
            record_path(self.root, key).read_text().replace(
                'evidence = "observed"', 'evidence = "other"'))
        self.git("add", ".ai")
        self.git("commit", "-m", "other edit")
        self.git("checkout", "feature")
        self.assertEqual(main(["--root", str(self.root), "check",
                               "--against-ref", "main", "--require-base"]), 4)

    def test_invalid_schema_is_rejected(self):
        key, _ = self.create()
        record_path(self.root, key).write_text("schema_version = 'wrong'\n")
        self.assertEqual(main(["--root", str(self.root), "check"]), 4)

    def test_existing_base_change_is_bound_to_audit(self):
        key, _ = self.create()
        self.git("add", ".ai")
        self.git("commit", "-m", "registered")
        old = sha(record_path(self.root, key).read_bytes())
        modify(self.root, "main", key, old, "amend", reason="recheck",
               changes={"evidence": "new evidence"})
        self.assertEqual(check_catalog(load_catalog(self.root)), [])
        self.assertEqual(main(["--root", str(self.root), "check",
                               "--against-ref", "main", "--require-base"]), 0)

    def test_related_sources_are_append_only(self):
        key, previous = self.create()
        modify(self.root, "main", key, previous, "amend", reason="additional finding",
               changes={"sources": ["finding:F-782-2"]})
        self.assertEqual(load_catalog(self.root)[key]["sources"],
                         ["issue:782", "finding:F-782-1", "finding:F-782-2"])

    def test_closing_promoted_keeps_issue_reference(self):
        key, first = self.create()
        second = modify(self.root, "main", key, first, "transition",
                        reason="triage", changes={"status": "triaged"})
        with mock.patch("advisory.operations.verify_existing_issue") as verify:
            third = modify(self.root, "main", key, second, "promote",
                           reason="linked", changes={"promoted_issue": "owner/repo#1"})
            verify.assert_called_once_with("owner/repo#1")
        modify(self.root, "main", key, third, "transition",
               reason="delivered", changes={"status": "closed"})
        self.assertEqual(check_catalog(load_catalog(self.root)), [])
        self.assertEqual(load_catalog(self.root)[key]["promoted_issue"], "owner/repo#1")

    def test_direct_promote_rejects_unverified_issue_without_mutating_record(self):
        key, first = self.create()
        triaged = modify(self.root, "main", key, first, "transition",
                         reason="reviewed", changes={"status": "triaged"})
        path = record_path(self.root, key)
        original = path.read_bytes()
        with mock.patch("advisory.operations.verify_existing_issue",
                        side_effect=ValueError("could not verify existing issue")) as verify:
            with self.assertRaisesRegex(ValueError, "could not verify existing issue"):
                modify(self.root, "main", key, triaged, "promote",
                       reason="bad reference",
                       changes={"promoted_issue": "owner/repo#999"})
            verify.assert_called_once_with("owner/repo#999")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(check_catalog(load_catalog(self.root)), [])

    def test_claude_edit_tools_deny_direct_ledger_writes(self):
        import json
        settings = Path(__file__).resolve().parents[2] / ".claude/settings.json"
        deny = json.loads(settings.read_text(encoding="utf-8"))["permissions"]["deny"]
        self.assertIn("Write(/.ai/advisory/ledger/**)", deny)
        self.assertIn("Edit(/.ai/advisory/ledger/**)", deny)

    def test_schema_reference_matches_python_contract(self):
        import json
        from advisory.record_fields import EVENT_FIELDS, FIELDS
        schema = Path(__file__).resolve().parents[2] / ".ai/schema/advisory-ledger-v1.json"
        declared = json.loads(schema.read_text(encoding="utf-8"))
        self.assertEqual(set(declared["required"]), set(FIELDS))
        self.assertEqual(set(declared["$defs"]["event"]["required"]), set(EVENT_FIELDS))
        self.assertIs(declared["additionalProperties"], False)
        self.assertIs(declared["$defs"]["event"]["additionalProperties"], False)

    def test_nfkc_id_collision(self):
        self.create(topic="A")
        with self.assertRaisesRegex(ValueError, "collision|duplicate topic"):
            self.create(topic="Ａ")

    def test_real_parallel_processes_have_exactly_one_winner(self):
        key, expected = self.create()
        tasks = [(str(self.root), key, expected, value) for value in ("A", "B")]
        with ProcessPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt_parallel_update, tasks))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(check_catalog(load_catalog(self.root)), [])
        self.assertIn(load_catalog(self.root)[key]["evidence"], ("A", "B"))

    def test_audit_timestamp_tamper_fails_even_if_digest_rebuilt(self):
        import tomllib
        from advisory.audit import digest
        from advisory.serialization import render
        key, _ = self.create()
        path = record_path(self.root, key)
        record = tomllib.loads(path.read_text(encoding="utf-8"))
        record["history"][0]["at"] = "not-an-iso-date"
        event = record["history"][0]
        event["digest"] = digest({k: value for k, value in event.items()
                                  if k != "digest"})
        path.write_text(render(record), encoding="utf-8")
        self.assertEqual(main(["--root", str(self.root), "check"]), 4)

    def test_explicit_zero_offset_is_canonical_utc(self):
        key, _ = self.create(at="2026-11-10T12:00:00+00:00")
        entry = load_catalog(self.root)[key]
        self.assertEqual(entry["history"][0]["at"], "2026-11-10T12:00:00Z")
        self.assertEqual(check_catalog(load_catalog(self.root)), [])


    def test_non_bmp_unicode_is_persisted_and_amendable(self):
        from advisory.serialization import encode
        import tomllib
        original = "根拠😀𠮷"
        key, first = new(self.root, "main", topic="絵文字の証拠",
                         created_on="2026-11-10", sources=["issue:782"],
                         evidence=original, recommendation="推奨🚀",
                         triage_rationale="理由🧪", policy_version="1.0")
        path = record_path(self.root, key)
        self.assertIn(original, path.read_text(encoding="utf-8"))
        self.assertEqual(load_catalog(self.root)[key]["evidence"], original)
        second = modify(self.root, "main", key, first, "amend",
                        reason="再検証😀", changes={"evidence": "改訂😃"})
        self.assertNotEqual(first, second)
        self.assertEqual(load_catalog(self.root)[key]["evidence"], "改訂😃")
        self.assertEqual(check_catalog(load_catalog(self.root)), [])
        encoded = encode("DEL:\x7f 😀")
        self.assertIn("\\u007f", encoded)
        self.assertEqual(tomllib.loads("value = " + encoded)["value"], "DEL:\x7f 😀")
        with self.assertRaisesRegex(ValueError, "Unicode scalar"):
            encode("\ud800")

    def test_role_is_not_a_cli_flag(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--root", str(self.root), "new", "--base-ref", "main",
                  "--topic", "独立した案", "--created-on", "2026-11-10",
                  "--source", "issue:782", "--evidence", "known evidence",
                  "--recommendation", "follow-up",
                  "--triage-rationale", "harm none",
                  "--policy-version", "1.0", "--role", "main-thread"])
        self.assertEqual(caught.exception.code, 2)

    def test_promote_rejects_fake_or_pull_request_api_response(self):
        import io
        import json
        from advisory.github_issue import verify_existing_issue
        correct = {"number": 42,
                   "repository_url": "https://api.github.com/repos/owner/repo"}
        cases = (
            dict(correct, pull_request={"url": "https://api.github.com/pulls/42"}),
            dict(correct, number=99),
            dict(correct, repository_url="https://api.github.com/repos/evil/repo"),
        )
        for payload in cases:
            with self.subTest(payload=payload):
                stream = io.BytesIO(json.dumps(payload).encode("utf-8"))
                with mock.patch("advisory.github_issue.urllib.request.urlopen",
                                return_value=stream):
                    with self.assertRaisesRegex(ValueError, "does not match"):
                        verify_existing_issue("owner/repo#42")

    def test_forbid_all_mutation_verbs_without_trusted_role(self):
        key, checksum = self.create()
        with mock.patch.dict(os.environ, {"ADVISORY_CALLER_ROLE": "pr-reviewer"}):
            for action, change in (("amend", {"evidence": "rewritten"}),
                                   ("transition", {"status": "triaged"})):
                with self.subTest(action=action):
                    with self.assertRaisesRegex(ValueError, "main-thread"):
                        modify(self.root, "main", key, checksum, action,
                               reason="not trusted", changes=change)
        self.assertEqual(check_catalog(load_catalog(self.root)), [])


if __name__ == "__main__":
    unittest.main()
