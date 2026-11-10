"""検証済み記録の保全と取得不能の組み合わせ。"""
from types import SimpleNamespace
from unittest import mock

from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class MoreTest(VerbCase):
    def test_locked_existing_block_can_be_adopted(self):
        token = self.token()
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.issue["locked"] = True
        code, output, _ = self.call("handoff-preview", *self.flags())
        self.assertEqual(0, code)
        self.assertIn("locked", output)
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
        self.assertEqual(0, self.call("handoff-recheck")[0])

    def test_recheck_invalid_json_and_shape(self):
        self.assertEqual(0, self.post()[0])
        original = self.run_process
        for response in ("HTTP/2 200\n\n{", "HTTP/2 200\n\n[]"):
            def run(argv, **kwargs):
                return original(argv, **kwargs) if argv[0] == "git" else SimpleNamespace(stdout=response)
            with mock.patch("subprocess.run", side_effect=run):
                code, _, err = self.call("handoff-recheck")
            self.assertEqual(4, code)
            self.assertNotIn("Traceback", err)
            self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)

    def test_post_content_change_stops_write(self):
        token = self.token()
        def mutate(argv):
            if "/issues/comments/" in argv[3]:
                item = self.ledger().findings[0]
                item.summary = "変更後"
                self.save(item)
        self.failure = mutate
        code, out, err = self.call("handoff-post", *self.flags(), "--confirm", token)
        self.assertEqual(4, code)
        self.assertIn("観測後に finding が変わった", err)
        self.assertIn("issuecomment-1", out)
        self.assertIsNone(self.ledger().findings[0].handoff)

    def test_recheck_deferred_to_change_stops_write(self):
        self.assertEqual(0, self.post()[0])
        def mutate(argv):
            if "/issues/comments/" in argv[3]:
                item = self.ledger().findings[0]
                item.deferred_to = "#10"
                self.save(item)
        self.failure = mutate
        code, out, _ = self.call("handoff-recheck")
        self.assertEqual(4, code)
        self.assertIn("観測後に finding が変わった", out)
        self.assertEqual("verified", self.ledger().findings[0].handoff.handoff_state)

    def test_changed_destination_returns_to_stalled_count(self):
        from karte.status_payload import status_payload
        self.assertEqual(0, self.post()[0])
        for target in ("#10", "https://github.com/other/repo/issues/9"):
            ledger = self.ledger()
            ledger.findings[0].deferred_to = target
            self.assertIn("F-7-01", status_payload(ledger)["stalled_findings"])
