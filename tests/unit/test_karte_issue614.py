"""Issue #614: check の診断対象・既存 verdict の独立性。"""

import argparse
import contextlib
import io
import unittest

from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.store import write_document
from karte import model, owner_decision, paths, verb_check
from karte.finding_handoff_hash import content_hash
from karte.finding_handoff_record import HandoffRecord
from karte.format_error import KarteFormatError
from karte.status_verdict import status_verdict
from tests.unit.karte_support import RootedCase
from tests.unit.test_feedback_ledger import ENTRY_ID, ledger_data


class TestCheckDiagnosis614(RootedCase):
    issue = 614

    def finding(self, seq, **updates):
        data = dict(
            id=f"F-{self.issue}-{seq:02d}", harm="real", disposition="fix-here",
            harm_detail="検査結果が誤る", severity="major", locus=["a/b.py::f"],
            summary=f"finding {seq}", evidence="a/b.py:1 の実装を確認",
            expected="誤りが解消する", recheck="再試験で確認する", rounds=[1],
        )
        data.update(updates)
        return model.Finding(**data)

    def check(self, findings):
        first = findings[0].id
        attempt = model.Attempt(1, 1, [first], "root-614", "logic", ["a/b.py::f"], "修正済み")
        result = model.Result(1, [first], ["a/b.py"], "fixed", "試験済み")
        karte = model.Karte(self.issue, findings, [attempt], [result])
        path = paths.karte_path(self.issue, self.root, create_dir=True)
        path.write_text(model.dumps(karte), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        args = argparse.Namespace(issue=str(self.issue), round="1", repo_root=str(self.root))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = verb_check.cmd_check(args)
        return code, out.getvalue(), err.getvalue(), model.parse(path.read_text(encoding="utf-8"))

    def test_verified_deferred_exempt_without_verdict_clearance(self):
        f = self.finding(2, harm="none", disposition="deferred", deferred_to="#900")
        f.handoff = HandoffRecord(
            handoff_issue="hiratashinnya/review-system#900",
            handoff_comment_url="https://github.com/hiratashinnya/review-system/issues/900#issuecomment-1",
            handoff_content_hash=content_hash(f.id, f.harm, f.summary, f.locus, f.expected),
            handoff_verified_at="2026-11-16T08:00:00+09:00", handoff_state="verified",
        )
        code, out, err, saved = self.check([self.finding(1), f])
        self.assertEqual(0, code, err)
        self.assertIn("検証済み handoff", out)
        self.assertIn(f.id, [x.id for x in status_verdict(saved)[2]])

    def test_unverified_deferred_requires_diagnosis(self):
        for handoff in (None, HandoffRecord(handoff_state="verified")):
            with self.subTest(handoff=handoff):
                f = self.finding(2, harm="none", disposition="deferred",
                                 deferred_to="#900", handoff=handoff)
                code, _out, err, _saved = self.check([self.finding(1), f])
                self.assertEqual(4, code)
                self.assertIn(f.id, err)

    def test_waived_without_override_is_not_exempt(self):
        f = self.finding(2, harm="none", disposition="waived",
                         waived_by="owner", waived_reason="判断済み")
        code, _out, err, _saved = self.check([self.finding(1), f])
        self.assertEqual(4, code)
        self.assertIn(f.id, err)

    def test_waived_with_override_is_exempt_but_still_open(self):
        write_document(self.root, LEDGER_SPEC, ledger_data())
        f = self.finding(2, harm="none", disposition="waived",
                         waived_by="owner", waived_reason="判断済み", override_ref=ENTRY_ID)
        code, out, err, saved = self.check([self.finding(1), f])
        self.assertEqual(0, code, err)
        self.assertIn("owner override", out)
        self.assertIn(f.id, [x.id for x in status_verdict(saved)[2]])

    def test_main_fix_here_exempt_while_status_still_harmful(self):
        f = self.finding(2, diagnosis_owner="main")
        code, out, err, saved = self.check([self.finding(1), f])
        self.assertEqual(0, code, err)
        self.assertIn("主文脈担当", out)
        self.assertEqual("harmful-open", status_verdict(saved)[-1])

    def test_legacy_fix_here_defaults_to_fixer(self):
        f = self.finding(2)
        code, _out, err, saved = self.check([self.finding(1), f])
        self.assertEqual(4, code)
        self.assertEqual("fixer", saved.finding(f.id).diagnosis_owner)
        self.assertIn(f.id, err)

    def test_decide_roundtrip_and_invalid_values(self):
        karte = model.Karte(self.issue, [self.finding(1)])
        owner_decision.record_decision(karte, f"F-{self.issue}-01", {}, None,
                                      diagnosis_owner="main")
        doc = model.dumps(karte)
        self.assertIn("diagnosis_owner: main", doc)
        self.assertEqual("main", model.parse(doc).findings[0].diagnosis_owner)
        with self.assertRaises(KarteFormatError):
            model.parse(doc.replace("diagnosis_owner: main", "diagnosis_owner: invalid"))
        with self.assertRaises(Exception):
            other = model.Karte(self.issue, [self.finding(1, disposition="deferred")])
            owner_decision.record_decision(other, f"F-{self.issue}-01", {}, None,
                                          diagnosis_owner="main")


if __name__ == "__main__":
    unittest.main()
