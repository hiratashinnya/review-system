"""再検証の無効化・復帰・並行変更。"""
import subprocess

from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class HandoffRecheckTest(VerbCase):
    def test_invalid_and_recover(self):
        self.assertEqual(0, self.post()[0])
        original = self.comments[0].copy()
        failures = [lambda: self.issue.update(state="closed", state_reason="completed"),
                    lambda: self.issue.update(state="closed", state_reason="not_planned"),
                    lambda: self.comments[0].update(body="変更"),
                    lambda: self.comments[0].update(user={"login": "other"}),
                    lambda: self.issue.update(html_url="https://github.com/x/r/issues/9"),
                    lambda: self.comments.clear()]
        for fail in failures:
            with self.subTest(fail=fail):
                fail()
                code, _, err = self.call("handoff-recheck")
                self.assertEqual(4, code, err)
                self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)
                self.issue.update(state="open", state_reason=None, locked=False,
                                  html_url="https://github.com/Owner/Repo/issues/9")
                self.comments[:] = [original.copy()]
                self.assertEqual(0, self.call("handoff-recheck")[0])
                self.assertEqual("verified", self.ledger().findings[0].handoff.handoff_state)

    def test_locked_issue_remains_verifiable(self):
        self.assertEqual(0, self.post()[0])
        self.issue.update(locked=True)
        code, out, err = self.call("handoff-recheck")
        self.assertEqual(0, code, err)
        self.assertIn("verified", out)
        self.assertEqual("verified", self.ledger().findings[0].handoff.handoff_state)

    def test_unavailable_and_changed(self):
        self.assertEqual(0, self.post()[0])
        def unavailable(argv):
            raise subprocess.TimeoutExpired(argv, 30)
        self.failure = unavailable
        self.assertEqual(4, self.call("handoff-recheck")[0])
        self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)
        self.failure = None
        self.assertEqual(0, self.call("handoff-recheck")[0])
        def mutate(argv):
            if "/issues/comments/" in argv[3]:
                item = self.ledger().findings[0]
                item.summary = "変更後"
                self.save(item)
        self.failure = mutate
        code, out, _ = self.call("handoff-recheck")
        self.assertEqual(4, code)
        self.assertIn("観測後に finding が変わった", out)
        self.assertEqual("verified", self.ledger().findings[0].handoff.handoff_state)
