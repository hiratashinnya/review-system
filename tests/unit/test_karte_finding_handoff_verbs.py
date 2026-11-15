"""プレビュー・投稿の安全条件と再実行。"""
import subprocess
from unittest import mock

from karte.finding_handoff_exemption import is_stall_exempt
from karte.finding_handoff_preview import preview
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class HandoffPostTest(VerbCase):
    def test_preview_confirm_post_and_count(self):
        before = self.path.read_bytes()
        token = self.token()
        self.assertEqual(before, self.path.read_bytes())
        for confirm in ([], ["--confirm", "bad"]):
            code, _, _ = self.call("handoff-post", *self.flags(), *confirm)
            self.assertEqual(4, code)
        self.assertEqual(0, self.posts)
        code, _, err = self.call("handoff-post", *self.flags(), "--confirm", token)
        self.assertEqual(0, code, err)
        self.assertTrue(is_stall_exempt(self.ledger().findings[0]))
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
        for value in ("#10", "https://github.com/else/repo/issues/9"):
            item = self.ledger().findings[0]
            item.deferred_to = value
            self.assertFalse(is_stall_exempt(item))

    def test_prerequisites(self):
        for field, value in (("harm", "real"), ("status", "resolved"), ("disposition", ""),
                             ("disposition", "fix-here"), ("disposition", "waived"),
                             ("deferred_to", "#10"), ("deferred_to", "https://github.com/x/r/issues/9")):
            with self.subTest(field=field, value=value):
                item = self.ledger().findings[0]
                setattr(item, field, value)
                self.save(item)
                self.assertEqual(4, self.call("handoff-preview", *self.flags())[0])
                self.setUp_item()
        self.issue.update({"pull_request": {}, "html_url": "https://github.com/Owner/Repo/pull/9"})
        code, _, err = self.call("handoff-preview", *self.flags())
        self.assertEqual(4, code)
        self.assertIn("プルリクエスト宛", err)
        self.assertEqual(0, self.posts)

    def setUp_item(self):
        from tests.unit.test_karte_finding_handoff_predicate import verified_item
        item = verified_item()
        item.handoff = None
        self.save(item)

    def test_failure_after_post_reuses_comment(self):
        token = self.token()
        def failure(argv):
            if "/issues/comments/" in argv[3]:
                raise subprocess.TimeoutExpired(argv, 30)
        self.failure = failure
        code, out, _ = self.call("handoff-post", *self.flags(), "--confirm", token)
        self.assertEqual(4, code)
        self.assertIn("issuecomment-1", out)
        self.assertIsNone(self.ledger().findings[0].handoff)
        self.failure = None
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)

    def test_warning_limit_and_locked(self):
        item = self.ledger().findings[0]
        item.summary = "連絡 @somebody"
        self.save(item)
        self.assertIn("警告", self.call("handoff-preview", *self.flags())[1])
        item.summary = "x" * 65537
        self.save(item)
        self.assertEqual(4, self.call("handoff-preview", *self.flags())[0])
        self.setUp_item()
        token = self.token()
        self.issue["locked"] = True
        self.assertEqual(4, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(0, self.posts)

    def test_observation_change_stops_write(self):
        token = self.token()
        def mutate(argv):
            if "/issues/comments/" in argv[3]:
                item = self.ledger().findings[0]
                item.deferred_to = "#10"
                self.save(item)
        self.failure = mutate
        code, out, err = self.call("handoff-post", *self.flags(), "--confirm", token)
        self.assertEqual(4, code)
        self.assertIn("観測後に finding が変わった", err)
        self.assertIn("issuecomment-1", out)
        self.assertIsNone(self.ledger().findings[0].handoff)
