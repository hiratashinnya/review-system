"""GitHub warning presentation stays derived from public threshold alerts (#635)."""

import copy
import unittest

from defect_metrics.annotation import render_warning


def report(codes=(), current=(3, 18), trailing=(4, 37), issues=(579, 580, 594)):
    details = {
        "BASELINE_EXCEEDED": "派生 Issue/PR = 0.7 が基線 0.68 を超過。",
        "TRAILING_REGRESSION": "派生 Issue/PR = 0.17 が直近4週 0.11 の1.5 倍以上（50% 以上悪化）。",
    }
    alerts = [{"code": code, "detail": details[code]} for code in codes]
    return {
        "schema_version": 1,
        "report_window": {
            "window": {"start": "2026-10-05T03:48:20Z", "end": "2026-10-12T03:48:20Z"},
            "denominator": {"merged_prs": current[1]},
            "primary": {"derived_issues": current[0], "derived_per_pr": round(current[0] / current[1], 2),
                        "derived_issue_numbers": list(issues)},
        },
        "trailing_4_weeks": {
            "window": {"start": "2026-09-07T03:48:20Z", "end": "2026-10-05T03:48:20Z"},
            "denominator": {"merged_prs": trailing[1]},
            "primary": {"derived_issues": trailing[0], "derived_per_pr": round(trailing[0] / trailing[1], 2)},
            "aggregation": {"detail": "28日をまとめたプールド比。週次比の平均ではない。"},
        },
        "baseline_verification": {"reproduced": True, "mismatches": []},
        "threshold": {"anomaly": bool(alerts), "alerts": alerts},
    }


class DefectMetricsAnnotationTests(unittest.TestCase):
    def test_fixed_issue_run_shows_reason_counts_windows_rate_targets_and_limit(self):
        payload = report(("TRAILING_REGRESSION",))
        before = copy.deepcopy(payload)
        message = render_warning(payload)
        self.assertIn("TRAILING_REGRESSION: 派生 Issue/PR = 0.17 が直近4週 0.11", message)
        self.assertIn("3/18 = 0.17", message)
        self.assertIn("4/37 = 0.11", message)
        self.assertIn("+54.17%", message)
        self.assertIn("#579 #580 #594", message)
        self.assertIn("baseline 0.68 は 超過なし", message)
        self.assertIn("プールド比", message)
        self.assertIn("計画タスクを含み", message)
        self.assertIn("欠陥分類や因果関係は判定しない", message)
        self.assertEqual(payload, before)

    def test_each_alert_combination_only_displays_published_reasons(self):
        cases = (
            (("TRAILING_REGRESSION",), (3, 18), (4, 37), "超過なし"),
            (("BASELINE_EXCEEDED",), (7, 10), (20, 40), "超過"),
            (("BASELINE_EXCEEDED", "TRAILING_REGRESSION"), (7, 10), (4, 10), "超過"),
        )
        for alerts, current, trailing, baseline in cases:
            with self.subTest(alerts=alerts):
                text = render_warning(report(alerts, current=current, trailing=trailing))
                for code in ("BASELINE_EXCEEDED", "TRAILING_REGRESSION"):
                    self.assertEqual(code in text, code in alerts)
                self.assertIn(f"baseline 0.68 は {baseline}", text)
        self.assertEqual(render_warning(report((), current=(3, 18), trailing=(4, 24))), "")


if __name__ == "__main__":
    unittest.main()
