"""走査と読み戻し照合。"""

import unittest
from dataclasses import replace
from unittest.mock import patch

from karte.finding_handoff_block import render_block
from karte.finding_handoff_github import list_comments
from karte.finding_handoff_hash import content_hash
from karte.finding_handoff_scan import scan_comments
from karte.finding_handoff_verify import verify_comment
from karte.finding_record import Finding
from tests.unit.test_karte_finding_handoff_gh import comment, reply


class VerifyTest(unittest.TestCase):
    def setUp(self):
        guard = patch("subprocess.run", side_effect=AssertionError("実コマンド禁止"))
        guard.start()
        self.addCleanup(guard.stop)
        self.finding = Finding(id="F-7-01", harm="none", summary="要約", expected="期待", locus=["a.py"])
        self.body = render_block(self.finding, "Codex")
        self.digest = content_hash(self.finding.id, self.finding.harm, self.finding.summary,
                                   self.finding.locus, self.finding.expected)
        self.comment = comment() | {"body": self.body}

    def test_verify(self):
        self.assertTrue(verify_comment(self.comment, self.finding, "ME").valid)
        windows = "\r\n" + "\r\n".join(line + "  " for line in self.body.splitlines()) + "\r\n"
        self.assertTrue(verify_comment(self.comment | {"body": windows}, self.finding, "me").valid)
        for bad in (self.body.replace("要約", "改変"), "no block", self.body + "\n" + self.body,
                    self.body.replace("- harm:", "- bad:")):
            self.assertFalse(verify_comment(self.comment | {"body": bad}, self.finding, "me").valid)
        self.assertFalse(verify_comment(self.comment, replace(self.finding, expected="変更"), "me").valid)
        self.assertFalse(verify_comment(self.comment, self.finding, "someone").valid)

    def test_scan_second_page_and_oldest(self):
        old = self.comment | {"created_at": "2020-01-01", "html_url": "old"}
        new = self.comment | {"created_at": "2021-01-01", "html_url": "new"}
        other = old | {"user": {"login": "other"}}
        def run(argv, **kwargs):
            return (reply([other], 'Link: <next>; rel="next"') if "&page=1" in argv[-1]
                    else reply([new, old]))
        comments = list_comments("o/r#9", run)
        self.assertEqual((old, [new]), scan_comments(comments, self.finding.id, self.digest, "me"))
        self.assertEqual((None, []), scan_comments([other], self.finding.id, self.digest, "me"))
        same_time = new | {"created_at": old["created_at"], "html_url": "a"}
        self.assertEqual((old, [same_time]), scan_comments([old, same_time], self.finding.id, self.digest, "me"))
