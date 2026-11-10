"""投稿・再検証における GitHub 失敗と読み戻し。"""
import subprocess
from unittest import mock

from karte.finding_handoff_errors import FindingHandoffError
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class FailureTest(VerbCase):
    def test_gh_failures_are_exit_four(self):
        token = self.token()
        failures = [subprocess.CalledProcessError(1, "gh", stderr="HTTP 401"),
                    subprocess.CalledProcessError(1, "gh", stderr="HTTP 403 rate limit"),
                    subprocess.TimeoutExpired("gh", 30), FileNotFoundError()]
        for failure in failures:
            def raise_error(argv):
                raise failure
            self.failure = raise_error
            code, _, err = self.call("handoff-post", *self.flags(), "--confirm", token)
            self.assertEqual(4, code)
            self.assertNotIn("Traceback", err)
            self.assertIsNone(self.ledger().findings[0].handoff)
        self.failure = None
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        for failure in failures:
            def raise_error(argv):
                raise failure
            self.failure = raise_error
            code, _, err = self.call("handoff-recheck")
            self.assertEqual(4, code)
            self.assertNotIn("Traceback", err)
            self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)

    def test_bad_json_and_shape(self):
        token = self.token()
        for response in ("HTTP/2 200\n\n{", "HTTP/2 200\n\n[]"):
            from types import SimpleNamespace
            original = self.run_process
            def run(argv, **kwargs):
                return original(argv, **kwargs) if argv[0] == "git" else SimpleNamespace(stdout=response)
            with mock.patch("subprocess.run", side_effect=run):
                code, _, err = self.call("handoff-post", *self.flags(), "--confirm", token)
                self.assertEqual(4, code)
                self.assertNotIn("Traceback", err)
            self.assertIsNone(self.ledger().findings[0].handoff)

    def test_readback_failure_and_no_delete(self):
        token = self.token()
        for change in (lambda body: body.replace("要約", "変更"), lambda body: "missing",
                       lambda body: body + "\n" + body):
            self.comments.clear()
            original = self.run_process
            def run(argv, **kwargs):
                result = original(argv, **kwargs)
                if "/issues/comments/" in argv[3]:
                    import json
                    headers, raw = result.stdout.split("\n\n", 1)
                    data = json.loads(raw)
                    data["body"] = change(data["body"])
                    result.stdout = headers + "\n\n" + json.dumps(data)
                return result
            with mock.patch("subprocess.run", side_effect=run):
                code, out, _ = self.call("handoff-post", *self.flags(), "--confirm", token)
            self.assertEqual(4, code)
            self.assertIn("issuecomment-1", out)
            self.assertEqual(1, len(self.comments))
            self.assertIsNone(self.ledger().findings[0].handoff)

    def test_store_failure_then_adopt(self):
        token = self.token()
        with mock.patch("karte.finding_handoff_store.owner_decision.write_karte", side_effect=OSError("disk")):
            code, out, _ = self.call("handoff-post", *self.flags(), "--confirm", token)
        self.assertEqual(4, code)
        self.assertIn("issuecomment-1", out)
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
