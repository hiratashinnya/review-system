"""アンカー不一致/前置き/欠落画像を完成として採用しない。"""

import unittest

from agy_delegate.adoption import adoption_reasons
from agy_delegate.types import Result


class AdoptionTests(unittest.TestCase):
    def test_anchor_mismatch_missing_or_unanswered(self):
        result = Result("run", classification="success_candidate")
        for observed in ({}, {"target": "wrong"}, {"target": "right", "unexpected": "x"}):
            reasons = adoption_reasons(result, expected_anchors={"target": "right"},
                                       observed_anchors=observed, substantive_verified=True)
            self.assertIn("anchor_mismatch_or_missing", reasons)

    def test_preface_and_missing_artifact_do_not_become_complete(self):
        result = Result("run", classification="success_candidate", response="これから調査します")
        reasons = adoption_reasons(result, expected_anchors={}, observed_anchors={},
                                   substantive_verified=False, required_artifact=True)
        self.assertEqual(set(reasons), {"substantive_verification_missing", "required_artifact_missing"})
        self.assertFalse(result.completed)

    def test_verified_response_remains_candidate_until_agent_adopts(self):
        result = Result("run", classification="success_candidate", response="verified")
        self.assertEqual(adoption_reasons(result, expected_anchors={"file": "anchor"},
                                         observed_anchors={"file": "anchor"}, substantive_verified=True), [])
        self.assertFalse(result.completed)


if __name__ == "__main__":
    unittest.main()
