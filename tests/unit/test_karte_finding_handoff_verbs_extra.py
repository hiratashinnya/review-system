"""重複・origin・ロック・時刻の契約。"""
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from karte import finding_handoff_store
from karte.finding_handoff_block import render_block
from karte.finding_handoff_observe import timestamp
from karte.finding_handoff_record import HandoffRecord
from karte.parser_core import build_parser
from karte.handoff_cli import register
from tests.unit.karte_support import writer_lock_is_held
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class ExtraTest(VerbCase):
    def test_timestamp_and_lock(self):
        fixed = datetime(2025, 3, 1, tzinfo=timezone.utc)
        self.assertEqual("2025-03-01T00:00:00+00:00", timestamp(fixed))
        item = self.ledger().findings[0]
        record = HandoffRecord(handoff_state="invalid")
        original = finding_handoff_store.owner_decision.write_karte
        def write(path, ledger):
            self.assertTrue(writer_lock_is_held(self.root))
            original(path, ledger)
        with mock.patch.object(finding_handoff_store.owner_decision, "write_karte", side_effect=write):
            finding_handoff_store.store(self.root, 7, item.id, finding_handoff_store.snapshot(item), record)
        self.assertEqual(record, self.ledger().findings[0].handoff)

    def test_other_author_and_duplicate(self):
        token = self.token()
        body = render_block(self.ledger().findings[0], "Codex")
        from tests.unit.test_karte_finding_handoff_gh import comment
        other = comment() | {"body": body, "user": {"login": "other"},
             "issue_url": "https://api.github.com/repos/Owner/Repo/issues/9"}
        self.comments.append(other)
        self.assertEqual(4, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.assertEqual(1, self.posts)
        self.comments.pop(0)
        self.assertEqual(0, self.call("handoff-post", *self.flags(), "--confirm", token)[0])
        self.comments.append(self.comments[0].copy())
        self.assertIn("重複", self.call("handoff-post", *self.flags(), "--confirm", token)[1])
        self.assertEqual(1, self.posts)

    def test_origin_and_registration(self):
        parser = build_parser((register,))
        for name in ("handoff-preview", "handoff-post", "handoff-recheck"):
            action = next(a for a in parser._actions if a.dest == "verb")
            self.assertFalse(action.choices[name].get_default("func").locked)
        original = self.run_process
        for outcome in (subprocess.CalledProcessError(1, "git"), "https://example.com/o/r"):
            def run(argv, **kwargs):
                if argv[0] == "git":
                    if isinstance(outcome, Exception):
                        raise outcome
                    return SimpleNamespace(stdout=outcome)
                return original(argv, **kwargs)
            with mock.patch("subprocess.run", side_effect=run):
                for verb, flags in (("handoff-preview", self.flags()), ("handoff-post", self.flags()),
                                    ("handoff-recheck", [])):
                    self.assertEqual(4, self.call(verb, *flags)[0])
