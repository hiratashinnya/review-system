"""pr-reviewer handoff の共通 envelope 束縛（Issue #375・#371 契約）。"""

import ast
import unittest
from pathlib import Path

from issue_envelope import handoff
from issue_envelope import review_envelope as reexported
from karte import review_envelope

VALID = dict(
    issue=375, phase="implementation", run_id="run-1", target_key="pr-697",
    input_digest="b" * 64, snapshot_oid="a" * 40,
)


def _declared(**overrides):
    base = {
        "schema": review_envelope.SCHEMA, "schema_version": "1", "status": "ready",
        "producer": review_envelope.PRODUCER, "artifact_type": review_envelope.ARTIFACT_TYPE,
        **{key: str(value) for key, value in VALID.items()},
    }
    return {**base, **overrides}


class TestReviewEnvelope(unittest.TestCase):
    def test_bound_keys_stay_in_sync_with_the_process_artifact_vocabulary(self):
        self.assertEqual(
            [key for key in handoff.BINDINGS if key != "input_refs"], list(review_envelope.BOUND)
        )

    def test_issue_envelope_reexports_the_same_implementation(self):
        self.assertIs(review_envelope.validate_review_envelope, reexported.validate_review_envelope)
        self.assertEqual(review_envelope.BOUND, reexported.BOUND)

    def test_karte_review_envelope_needs_nothing_outside_the_karte_package(self):
        tree = ast.parse(Path(review_envelope.__file__).read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
        } | {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertEqual({"re"}, imported)

    def test_expected_of_returns_only_the_bound_keys_with_typed_issue(self):
        expected = review_envelope.expected_of(**VALID)
        self.assertEqual(set(review_envelope.BOUND), set(expected))
        self.assertEqual(375, expected["issue"])
        self.assertEqual("pr-reviewer", expected["producer"])

    def test_matching_declaration_is_accepted(self):
        data = review_envelope.validate_review_envelope(_declared(), review_envelope.expected_of(**VALID))
        self.assertEqual("ready", data["status"])
        self.assertEqual("", data["next_expected_artifact"])

    def test_every_bound_value_must_equal_the_expectation(self):
        expected = review_envelope.expected_of(**VALID)
        for key, value in (
            ("issue", "376"), ("run_id", "run-2"), ("target_key", "pr-1"), ("phase", "test_design"),
            ("snapshot_oid", "c" * 40), ("input_digest", "d" * 64),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, f"stale: {key}"):
                review_envelope.validate_review_envelope(_declared(**{key: value}), expected)

    def test_expectation_must_cover_every_bound_key(self):
        expected = review_envelope.expected_of(**VALID)
        del expected["run_id"]
        with self.assertRaisesRegex(ValueError, "期待値が欠落"):
            review_envelope.validate_review_envelope(_declared(), expected)

    def test_malformed_declarations_are_rejected(self):
        for overrides, fragment in (
            ({"schema": "other/v1"}, "schema"), ({"schema_version": "2"}, "schema_version"),
            ({"producer": "plan-reviewer"}, "producer"), ({"artifact_type": "ChangePlan"}, "artifact_type"),
            ({"status": "stop"}, "ready"), ({"next_expected_artifact": "ChangePlan"}, "next_expected"),
            ({"snapshot_oid": "abc"}, "OID"), ({"input_digest": "abc"}, "sha256"),
            ({"run_id": " "}, "run_id"), ({"issue": "0"}, "issue"), ({"issue": "x"}, "整数"),
            ({"phase": "solution_planning"}, "phase"),
        ):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, fragment):
                review_envelope.normalize(_declared(**overrides))

    def test_missing_and_unknown_keys_are_rejected(self):
        missing = _declared()
        del missing["run_id"]
        with self.assertRaisesRegex(ValueError, "欠落"):
            review_envelope.normalize(missing)
        with self.assertRaisesRegex(ValueError, "未知"):
            review_envelope.normalize(_declared(extra="1"))


if __name__ == "__main__":
    unittest.main()
