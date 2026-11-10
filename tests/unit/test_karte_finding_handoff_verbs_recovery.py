"""部分失敗・排他更新・固定時刻の回帰。"""
import argparse
import contextlib
import io
import subprocess
from datetime import datetime, timezone
from unittest import mock

from karte.verb_handoff_post import cmd_handoff_post
from karte.verb_handoff_recheck import cmd_handoff_recheck
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class RecoveryTest(VerbCase):
    def test_server_created_then_timeout(self):
        token = self.token()
        original = self.run_process
        def run(argv, **kwargs):
            result = original(argv, **kwargs)
            if argv[0] == "gh" and argv[3].endswith("/comments"):
                raise subprocess.TimeoutExpired(argv, 30)
            return result
        with mock.patch("subprocess.run", side_effect=run):
            self.assertEqual(4, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)

    def test_explicit_clock(self):
        token = self.token()
        instant = datetime(2031, 2, 3, tzinfo=timezone.utc)
        args = argparse.Namespace(issue="7", finding="F-7-01", to="#9", agent="Codex", confirm=token)
        with mock.patch("karte.verb_handoff_post.timestamp", side_effect=lambda now: now.isoformat()):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, cmd_handoff_post.__wrapped__(args, self.root, now=instant))
        self.assertEqual(instant.isoformat(), self.ledger().findings[0].handoff.handoff_verified_at)
        later = datetime(2031, 2, 4, tzinfo=timezone.utc)
        with mock.patch("karte.verb_handoff_recheck.timestamp", side_effect=lambda now: now.isoformat()):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, cmd_handoff_recheck.__wrapped__(
                    argparse.Namespace(issue="7", finding=None), self.root, now=later))
        self.assertEqual(later.isoformat(), self.ledger().findings[0].handoff.handoff_verified_at)

    def test_recheck_wrong_repository_and_hash(self):
        from dataclasses import replace
        self.assertEqual(0, self.post()[0])
        item = self.ledger().findings[0]
        item.handoff = replace(item.handoff, handoff_issue="Other/Repo#9")
        self.save(item)
        self.assertEqual(4, self.call("handoff-recheck")[0])
        self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)
        item = self.ledger().findings[0]
        item.handoff = replace(item.handoff, handoff_issue="Owner/Repo#9")
        item.summary = "変更済み"
        self.save(item)
        self.assertEqual(4, self.call("handoff-recheck")[0])
        self.assertEqual("invalid", self.ledger().findings[0].handoff.handoff_state)

    def test_second_page_existing_block(self):
        token = self.token()
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        original = self.run_process
        def run(argv, **kwargs):
            if argv[0] == "gh" and "comments?" in argv[3] and "&page=1" in argv[3]:
                return type("Response", (), {"stdout": 'HTTP/2 200\nLink: <next>; rel="next"\n\n[]'})()
            return original(argv, **kwargs)
        with mock.patch("subprocess.run", side_effect=run):
            self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
