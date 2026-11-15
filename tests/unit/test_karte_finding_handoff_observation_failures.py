"""宛先走査・移転・不存在での失敗を verb 境界から検証する。"""
import subprocess
from unittest import mock

from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class HandoffObservationFailureTest(VerbCase):
    def test_post_rejects_changed_destination_without_posting(self):
        token = self.token()
        item = self.ledger().findings[0]
        item.deferred_to = "https://github.com/Other/Repo/issues/9"
        self.save(item)
        self.assertEqual(4, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(0, self.posts)
        self.assertIsNone(self.ledger().findings[0].handoff)

    def test_second_page_failure_never_posts(self):
        token = self.token()
        original = self.run_process
        def run(argv, **kwargs):
            if argv[0] == "gh" and "comments?" in argv[3]:
                if "&page=1" in argv[3]:
                    return type("Response", (), {"stdout": 'HTTP/2 200\nLink: <next>; rel="next"\n\n[]'})()
                raise subprocess.CalledProcessError(1, argv, stderr="HTTP 500")
            return original(argv, **kwargs)
        with mock.patch("subprocess.run", side_effect=run):
            self.assertEqual(4, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(0, self.posts)
        self.assertIsNone(self.ledger().findings[0].handoff)

    def test_recheck_missing_or_moved_issue_and_comment(self):
        self.assertEqual(0, self.post()[0])
        original_issue = self.issue.copy()
        original_comment = self.comments[0].copy()
        changes = (
            (self.issue, "repository_url", "https://api.github.com/repos/other/repo"),
            (self.issue, "number", 10),
            (self.comments[0], "issue_url", "https://api.github.com/repos/other/repo/issues/9"),
        )
        for obj, key, value in changes:
            with self.subTest(key=key):
                obj[key] = value
                self.assertEqual(4, self.call("handoff-recheck")[0])
                self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)
                self.issue.update(original_issue)
                self.comments[0].update(original_comment)
                self.assertEqual(0, self.call("handoff-recheck")[0])
        def missing_issue(argv):
            if argv[3].endswith("/issues/9"):
                raise subprocess.CalledProcessError(1, argv, stderr="HTTP 404")
        self.failure = missing_issue
        self.assertEqual(4, self.call("handoff-recheck")[0])
        self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)
