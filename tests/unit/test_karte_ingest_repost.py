"""再投稿（既存 finding を次のラウンドで再掲）の上書き契約（``ingest_apply.apply_accepted``）。

レビュー欄（harm・harm_detail・severity・summary・evidence・expected・recheck・locus）と、
オーナー判断欄（scope・disposition とその付随キー）は**毎ラウンドのレポートの値で上書き**する。
据え置くと、書かれなくなった disposition が台帳に残り続けて静かにずれる（書き忘れは未決定へ倒れる）。
解消の宣言（``status: resolved``）も同様に毎回レポートの値で決まる。
"""

import unittest

from karte import exit_codes
from tests.unit.karte_support import RootedCase, finding, required_finding

FIRST = finding(
    "a.py::f", "元の要約", harm_detail="元の実害", evidence="元の根拠", expected="元の期待",
    recheck="元の確認", disposition="waived", waived_by="owner", waived_reason="元の理由",
)
SECOND = finding(
    "[b.py::g, c.py::h]", "新しい要約", harm="none", harm_detail="新しい実害なし",
    severity="minor", scope="out", evidence="新しい根拠", expected="新しい期待",
    recheck="新しい確認", disposition="deferred", deferred_to="#123",
)
THIRD = finding("a.py::f", "三度目の要約")  # disposition を書かない＝未決定へ戻る


def snapshot(item) -> dict:
    """上書き対象のフィールドを取り出す。"""
    return {
        "status": item.status, "resolved_round": item.resolved_round, "harm": item.harm,
        "harm_detail": item.harm_detail, "severity": item.severity, "scope": item.scope,
        "locus": item.locus, "summary": item.summary, "evidence": item.evidence,
        "expected": item.expected, "recheck": item.recheck, "disposition": item.disposition,
        "deferred_to": item.deferred_to, "waived_by": item.waived_by,
        "waived_reason": item.waived_reason, "rounds": item.rounds,
    }


class TestRepostOverwritesEveryReviewedField(RootedCase):
    prefix = "karte-repost-"

    def _post(self, round_no, title, fields):
        code, _out, err = self.ingest(round_no, (title, fields))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        return snapshot(required_finding(self.ledger(), "F-7-01"))

    def test_first_post_is_stored_as_written(self):
        self.assertEqual(
            {
                "status": "open", "resolved_round": None, "harm": "real", "harm_detail": "元の実害",
                "severity": "major", "scope": "in", "locus": ["a.py::f"], "summary": "元の要約",
                "evidence": "元の根拠", "expected": "元の期待", "recheck": "元の確認",
                "disposition": "waived", "deferred_to": "", "waived_by": "owner",
                "waived_reason": "元の理由", "rounds": [1],
            },
            self._post(1, "new", FIRST),
        )

    def test_a_repost_replaces_the_review_fields_and_switches_the_disposition(self):
        self._post(1, "new", FIRST)
        self.assertEqual(
            {
                "status": "open", "resolved_round": None, "harm": "none",
                "harm_detail": "新しい実害なし", "severity": "minor", "scope": "out",
                "locus": ["b.py::g", "c.py::h"], "summary": "新しい要約", "evidence": "新しい根拠",
                "expected": "新しい期待", "recheck": "新しい確認", "disposition": "deferred",
                "deferred_to": "#123", "waived_by": "", "waived_reason": "",  # waived の付随キーは消える
                "rounds": [1, 2],
            },
            self._post(2, "F-7-01", SECOND),
        )

    def test_a_repost_without_a_disposition_clears_it(self):
        self._post(1, "new", FIRST)
        self._post(2, "F-7-01", SECOND)
        third = self._post(3, "F-7-01", THIRD)
        self.assertEqual(
            ("real", "in", "", "", "", "", ["a.py::f"], "三度目の要約", [1, 2, 3]),
            (third["harm"], third["scope"], third["disposition"], third["deferred_to"],
             third["waived_by"], third["waived_reason"], third["locus"], third["summary"],
             third["rounds"]),
        )

    def test_resolution_is_declared_per_round_and_can_be_withdrawn(self):
        self._post(1, "new", FIRST)
        resolved = self._post(2, "F-7-01", {**FIRST, "status": "resolved"})
        self.assertEqual(("resolved", 2), (resolved["status"], resolved["resolved_round"]))
        reopened = self._post(3, "F-7-01", FIRST)
        self.assertEqual(("open", None), (reopened["status"], reopened["resolved_round"]))
        self.assertEqual([1, 2, 3], reopened["rounds"])


if __name__ == "__main__":
    unittest.main()
