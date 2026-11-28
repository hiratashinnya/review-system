"""Fixtures for the report's state, historical evidence and safe static markup."""

import json
import unittest

from weekly_report import analysis, render, snapshot
from weekly_report.period import parse_jst, resolve_period
from weekly_report.quantities import measured


def _metric(value, *, status=None, basis="period", **details):
    return {"basis": basis, **measured(value, "固定定義", "テスト出典", status=status, **details)}


def _data(start="2026-11-01", end="2026-11-08", now="2026-11-08"):
    period = resolve_period(start, end, now).as_dict()
    return {"repository": "example/review-system", "observed_at": period["observed_until"], "period": period,
            "reference": {"base_sha": "a" * 40, "base_ref": "origin/main", "checkout_sha": "b" * 40,
                          "checkout_dirty": False}, "metrics": {"issues_created": _metric(2)},
            "comparison": {"reason": "前回観測なし", "metrics": {}}, "sources": {}, "limitations": [],
            "events": {"created": [{"number": 1, "title": "設計発掘"}, {"number": 2, "title": "観測内容"}]},
            "inventory": {"open_pulls": [{"number": 3, "title": "検査する PR"}]}, "evidence": {}}


class ReportDisplayTests(unittest.TestCase):
    def test_batch_preserves_partial_and_future_rows_without_comparing_them(self):
        first = _data()
        second = _data("2026-11-08", "2026-11-15", "2026-11-15")
        second["metrics"]["issues_created"] = _metric(0)
        partial = _data("2026-11-15", "2026-11-22", "2026-11-17")
        future = {"status": "not_arrived", "reason": "予定期間", "period": {"start": "2026-11-22", "end": "2026-11-29"}}
        html = render.batch_report([(first, "week-2026-11-01/report.html"), (second, "../report.html"),
                                    (partial, "week-2026-11-15/report.html"), (future, None)])
        self.assertEqual(html.count("<meter "), 2)
        self.assertIn('value="0"', html)
        self.assertIn('href="week-2026-11-01/report.html"', html)
        self.assertNotIn('href="../report.html"', html)
        self.assertIn("途中経過", html)
        self.assertIn("未到来", html)
        self.assertIn("予定期間", html)

    def test_classifies_only_captured_derived_issues_and_preserves_legacy_analysis(self):
        data = _data()
        data["metrics"]["defects_per_merge"] = _metric(0.5, numerator=2, denominator=4, derived_issue_numbers=[1, 2])
        row = {"kind": "fact", "text": "根拠", "sources": ["snapshot.json"]}
        body = {"sections": {key: [row] for key in analysis.SECTIONS}, "summary": "要約"}
        self.assertIs(analysis.validate(body), body)
        case = {"number": 1, "category": "design_discovery", "kind": "fact", "text": "<根拠>",
                "sources": ["https://github.com/example/review-system/issues/1", "https://example.invalid/外部"]}
        body["derived_cases"] = [case, {**case, "number": 9, "text": "集計範囲外の文章"}]
        html = render.report(data, analysis.validate(body))
        self.assertIn("設計発掘（確認事実）", html)
        self.assertIn("分類の根拠が未入力です", html)
        self.assertIn("&lt;根拠&gt;", html)
        self.assertIn('href="https://github.com/example/review-system/issues/1"', html)
        self.assertNotIn('href="https://example.invalid', html)
        self.assertNotIn("集計範囲外の文章", html)

    def test_saved_observation_keeps_original_ci_state_and_partial_reasons(self):
        data = _data()
        data["observation"] = {"kind": "saved", "period_end_status": "not_measured", "period_end_reason": "期中の状態",
                               "current_collection_at": "2026-11-25", "source_snapshot_sha256": "c" * 64}
        check = {"head_sha": "d" * 40, "matching_workflow_run_ids": [42], "matching_review_ids": [],
                 "review_reason": "一部のレビューが欠損"}
        saved = {"pull_heads": {"3": check}, "head_ci": {"d" * 40: {"rows": [{"id": 42, "conclusion": "failure"}]}}}
        data["evidence"] = {"pull_heads": {"3": dict(check, head_sha="e" * 40)}, "saved_observation": saved}
        html = render.report(data, None)
        self.assertIn("保存済みの取得時点", html)
        self.assertIn("期中の状態", html)
        self.assertIn("42（failure）", html)
        self.assertIn("同一 SHA のレビュー 未確認", html)
        self.assertNotIn("e" * 40, html)

    def test_progress_baseline_and_measurement_states_are_distinct(self):
        data = _data()
        data["inventory"]["initiative_progress"] = {"1": {"number": 1, "title": "施策", "completed": 1, "total": 2}}
        data["comparison"]["initiative_changes"] = {"1": {"previous_total": 1, "current_total": 2}}
        data["metrics"].update({"main_baseline_total": _metric(44, commit_sha="履歴 SHA", difference_from_initial=-29),
                                "review_retries": _metric(None, status="not_retrieved"),
                                "review_real_findings": _metric(None, status="not_measured"),
                                "review_repeat_rate": _metric(None, status="not_calculable"),
                                "workflow_runs": _metric(0)})
        html = render.report(data, None)
        self.assertIn('<progress max="2" value="1"', html)
        self.assertIn("分母 1 → 2 件", html)
        self.assertIn("初期登録との差 -29 件", html)
        for label in ("未取得", "未計測", "算出不能", "0"):
            self.assertIn(f"<td>{label}<br>", html)

    def test_saved_transition_timestamps_preserve_the_html(self):
        data = _data()
        data["events"]["issue_transitions"] = [{"number": 1, "title": "再確認", "event": "reopened",
                                                 "created_at": parse_jst("2026-11-05")}]
        actual = render.report(data, None)
        self.assertIn("再オープン 2026-11-05T00:00:00+09:00", actual)
        self.assertEqual(actual, render.report(json.loads(snapshot.dumps(data)), None))
