"""defect_metrics（欠陥混入率の機械計測・Issue #488）の単体テスト。

時刻依存 test data の扱い（`.claude/rules/04-test-data.md`「時刻依存 test data の規律」）
--------------------------------------------------------------------------------------
本テストは絶対日付を多用するが、**wall clock を読む経路は 1 つしかない**
（`defect_metrics.cli.resolve_now`）。指標算出・閾値判定はいずれも渡された窓と
レコードだけで決まる純粋関数であり、実行時刻に依存しない。窓の決定が現在時刻に
依存する経路（``--window-start``/``--window-end`` を省略した場合と、閾値判定の
「直近4週」）を検証するテストでは、必ず ``--now`` / ``now=`` で固定値を注入する
（``resolve_now`` の既定分岐だけは注入せずに呼ぶが、そこでは固定日付と比較せず
「UTC の aware datetime を返すこと」しか検査しないため、時間経過で結果が反転しない）。
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from defect_metrics import cli, collect, metrics, model, threshold  # noqa: E402


def ts(text: str) -> datetime:
    return model.parse_timestamp(text)


def issue(number: int, created: str, body: str = "", closed: str | None = None) -> model.IssueRecord:
    return model.IssueRecord(
        number=number,
        created_at=ts(created),
        closed_at=ts(closed) if closed else None,
        body=body,
    )


def pull(number: int, merged: str) -> model.PullRequestRecord:
    return model.PullRequestRecord(number=number, merged_at=ts(merged))


class TimestampTests(unittest.TestCase):
    def test_date_only_is_midnight_utc(self):
        self.assertEqual(ts("2026-08-02"), datetime(2026, 8, 2, tzinfo=timezone.utc))

    def test_trailing_z_is_accepted(self):
        self.assertEqual(ts("2026-08-02T03:04:05Z"), datetime(2026, 8, 2, 3, 4, 5, tzinfo=timezone.utc))

    def test_offset_is_normalised_to_utc(self):
        self.assertEqual(ts("2026-08-02T09:00:00+09:00"), datetime(2026, 8, 2, tzinfo=timezone.utc))

    def test_naive_input_is_treated_as_utc(self):
        self.assertEqual(ts("2026-08-02T00:00:00"), datetime(2026, 8, 2, tzinfo=timezone.utc))

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            ts("   ")

    def test_format_timestamp_is_z_suffixed(self):
        self.assertEqual(model.format_timestamp(ts("2026-08-02T00:00:00+00:00")), "2026-08-02T00:00:00Z")


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.window = model.Window(start=ts("2026-08-02"), end=ts("2026-08-16"))

    def test_boundary_is_half_open(self):
        """start は含み end は含まない（隣接窓が境界を二重計上しない）。"""
        self.assertTrue(self.window.contains(ts("2026-08-02T00:00:00Z")))
        self.assertTrue(self.window.contains(ts("2026-08-15T23:59:59Z")))
        self.assertFalse(self.window.contains(ts("2026-08-16T00:00:00Z")))
        self.assertFalse(self.window.contains(ts("2026-08-01T23:59:59Z")))

    def test_none_is_never_contained(self):
        self.assertFalse(self.window.contains(None))

    def test_days(self):
        self.assertEqual(self.window.days, 14.0)

    def test_shifted_back_is_adjacent(self):
        trailing = self.window.shifted_back(timedelta(days=28))
        self.assertEqual(trailing.end, self.window.start)
        self.assertEqual(trailing.start, ts("2026-07-05"))

    def test_empty_or_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            model.Window(start=ts("2026-08-16"), end=ts("2026-08-02"))
        with self.assertRaises(ValueError):
            model.Window(start=ts("2026-08-02"), end=ts("2026-08-02"))

    def test_naive_boundary_is_rejected(self):
        with self.assertRaises(ValueError):
            model.Window(start=datetime(2026, 8, 2), end=datetime(2026, 8, 16))


class ReferenceExtractionTests(unittest.TestCase):
    def test_plain_references(self):
        self.assertEqual(metrics.referenced_numbers("PR #123 が原因。#45 も参照。"), {123, 45})

    def test_cross_repo_and_heading_and_entity_are_excluded(self):
        body = "owner/repo#99 と ## 見出し と &#187; と abc#77"
        self.assertEqual(metrics.referenced_numbers(body), set())

    def test_trailing_word_characters_are_excluded(self):
        self.assertEqual(metrics.referenced_numbers("#12abc"), set())

    def test_empty_body(self):
        self.assertEqual(metrics.referenced_numbers(None), set())
        self.assertEqual(metrics.referenced_numbers(""), set())


class DerivedIssueTests(unittest.TestCase):
    def setUp(self):
        self.pulls = {
            10: pull(10, "2026-08-03T00:00:00Z"),
            11: pull(11, "2026-08-10T00:00:00Z"),
        }

    def test_within_horizon_is_derived(self):
        self.assertTrue(metrics.is_derived(issue(1, "2026-08-04T00:00:00Z", "#10 の後で壊れた"), self.pulls))

    def test_exact_horizon_boundary_is_inclusive(self):
        """merge から丁度 72 時間後の起票は派生に含める（境界を含む）。"""
        self.assertTrue(metrics.is_derived(issue(1, "2026-08-06T00:00:00Z", "#10"), self.pulls))

    def test_just_past_horizon_is_not_derived(self):
        self.assertFalse(metrics.is_derived(issue(1, "2026-08-06T00:00:01Z", "#10"), self.pulls))

    def test_pull_merged_after_creation_is_not_derived(self):
        """起票より後に merge された PR は原因になりえない。"""
        self.assertFalse(metrics.is_derived(issue(1, "2026-08-09T00:00:00Z", "#11"), self.pulls))

    def test_unknown_reference_is_ignored(self):
        self.assertFalse(metrics.is_derived(issue(1, "2026-08-04T00:00:00Z", "#999"), self.pulls))

    def test_multiple_references_count_once(self):
        target = issue(1, "2026-08-04T00:00:00Z", "#10 と #999 と #11")
        self.assertTrue(metrics.is_derived(target, self.pulls))


class WindowMetricsTests(unittest.TestCase):
    def setUp(self):
        self.window = model.Window(start=ts("2026-08-02"), end=ts("2026-08-16"))
        self.pulls = [
            pull(1, "2026-08-01T12:00:00Z"),  # 窓外（直前）
            pull(2, "2026-08-03T00:00:00Z"),
            pull(3, "2026-08-10T00:00:00Z"),
            pull(4, "2026-08-16T00:00:00Z"),  # 窓外（終端は含まない）
        ]
        self.issues = [
            issue(101, "2026-08-02T00:00:00Z", "#1 の直後に壊れた"),  # 窓外 PR 参照でも派生
            issue(102, "2026-08-04T00:00:00Z", "#2 の retrospective"),
            issue(103, "2026-08-05T00:00:00Z", "無関係な新機能"),
            issue(104, "2026-08-14T00:00:00Z", "#3 は 72h 超過なので派生ではない"),
            issue(105, "2026-08-20T00:00:00Z", "#3"),  # 窓外の起票
        ]
        self.issues[2] = issue(103, "2026-08-05T00:00:00Z", "無関係", closed="2026-08-09T00:00:00Z")

    def test_counts_and_ratios(self):
        result = metrics.compute_window_metrics(self.window, self.issues, self.pulls)
        self.assertEqual(result.merged_prs, 2)
        self.assertEqual(result.created_issues, 4)
        self.assertEqual(result.derived_issues, 2)
        self.assertEqual(result.derived_issue_numbers, (101, 102))
        self.assertEqual(result.closed_issues, 1)
        self.assertEqual(result.open_issue_net_change, 3)
        self.assertAlmostEqual(result.issues_per_pr, 2.0)
        self.assertAlmostEqual(result.derived_per_pr, 1.0)

    def test_zero_denominator_yields_none_not_zero(self):
        empty = model.Window(start=ts("2026-09-01"), end=ts("2026-09-02"))
        result = metrics.compute_window_metrics(empty, self.issues, self.pulls)
        self.assertEqual(result.merged_prs, 0)
        self.assertIsNone(result.issues_per_pr)
        self.assertIsNone(result.derived_per_pr)

    def test_primary_and_secondary_are_reported_separately(self):
        payload = metrics.compute_window_metrics(self.window, self.issues, self.pulls).as_dict()
        self.assertIn("derived_per_pr", payload["primary"])
        self.assertIn("issues_per_pr", payload["secondary"])
        self.assertNotEqual(payload["primary"]["derived_issues"], payload["secondary"]["created_issues"])


def _baseline_dataset() -> tuple[list[model.IssueRecord], list[model.PullRequestRecord]]:
    """Issue #488「現状と根拠」の基線窓の計数（22 PR / 41 Issue / 派生 15）を再現する合成データ。

    実データそのものではなく「同じ計数になる最小構成」であり、検証対象は
    分母・分子・比率・丸めの算術と窓の境界条件（実データ由来の値は
    ``verify-baseline`` サブコマンドが GitHub から取得して照合する）。
    """
    pulls = [pull(1000 + i, f"2026-08-{2 + (i % 13):02d}T06:00:00Z") for i in range(22)]
    issues: list[model.IssueRecord] = []
    # 派生 15 件: 直前の merge（同日 06:00）を 12 時間後に参照する。
    for i in range(15):
        issues.append(
            issue(2000 + i, f"2026-08-{2 + (i % 13):02d}T18:00:00Z", f"#{1000 + i} の merge 後に判明")
        )
    # 非派生 26 件: PR を参照しない起票（41 - 15）。
    for i in range(26):
        issues.append(issue(3000 + i, f"2026-08-{2 + (i % 13):02d}T20:00:00Z", "PR 参照なしの新規起票"))
    # 窓外のノイズ（境界条件の確認用）。PR 側の下限境界は WindowMetricsTests が見る
    # ——ここで基線窓の直前に merged PR を置くと「直近4週」窓（07-05〜08-02）の分母が
    # 1 になり派生率 0 の比較対象が生まれてしまい、基線再現の検証と閾値判定の検証が
    # 混ざるため、この合成データでは置かない。
    issues.append(issue(4000, "2026-08-16T00:00:00Z", "終端は含まない"))
    issues.append(issue(4001, "2026-08-01T23:59:59Z", "起点未満は含まない"))
    pulls.append(pull(4002, "2026-08-16T00:00:00Z"))
    return issues, pulls


class BaselineReproductionTests(unittest.TestCase):
    def test_recorded_baseline_constants_match_issue_368_correction(self):
        self.assertEqual(model.BASELINE_WINDOW.start, ts("2026-08-02T00:00:00Z"))
        self.assertEqual(model.BASELINE_WINDOW.end, ts("2026-08-16T00:00:00Z"))
        self.assertEqual(model.BASELINE_WINDOW.days, 14.0)
        self.assertEqual(model.BASELINE_MERGED_PRS, 22)
        self.assertEqual(model.BASELINE_ALL_ISSUES, 41)
        self.assertEqual(model.BASELINE_DERIVED_ISSUES, 15)
        self.assertEqual(model.BASELINE_ISSUES_PER_PR, 1.86)
        self.assertEqual(model.BASELINE_DERIVED_PER_PR, 0.68)

    def test_baseline_window_reproduces_the_recorded_measurements(self):
        issues, pulls = _baseline_dataset()
        result = metrics.compute_window_metrics(model.BASELINE_WINDOW, issues, pulls)
        self.assertEqual(result.merged_prs, model.BASELINE_MERGED_PRS)
        self.assertEqual(result.created_issues, model.BASELINE_ALL_ISSUES)
        self.assertEqual(result.derived_issues, model.BASELINE_DERIVED_ISSUES)
        self.assertEqual(round(result.issues_per_pr, 2), model.BASELINE_ISSUES_PER_PR)
        self.assertEqual(round(result.derived_per_pr, 2), model.BASELINE_DERIVED_PER_PR)

    def test_shifted_start_changes_the_number(self):
        """窓の起点を1日ずらすと値が変わる＝散文の定義では再現できないことの実証（Issue #368）。"""
        issues, pulls = _baseline_dataset()
        shifted = model.Window(start=ts("2026-08-01"), end=ts("2026-08-16"))
        result = metrics.compute_window_metrics(shifted, issues, pulls)
        self.assertNotEqual(
            round(result.issues_per_pr, 2), round(model.BASELINE_ISSUES_PER_PR, 2)
        )


def wm(merged: int, derived: int, created: int = 0, closed: int = 0) -> metrics.WindowMetrics:
    return metrics.WindowMetrics(
        window=model.Window(start=ts("2026-09-01"), end=ts("2026-09-08")),
        merged_prs=merged,
        created_issues=created,
        derived_issues=derived,
        closed_issues=closed,
    )


class ThresholdTests(unittest.TestCase):
    def test_normal_case_reports_nothing(self):
        result = threshold.evaluate(wm(merged=10, derived=3), wm(merged=40, derived=12))
        self.assertFalse(result.anomaly)
        self.assertEqual(result.alerts, ())
        self.assertEqual(result.render_alert_lines(), [])

    def test_baseline_exceeded(self):
        result = threshold.evaluate(wm(merged=10, derived=7), wm(merged=40, derived=28))
        codes = {a.code for a in result.alerts}
        self.assertIn(threshold.BASELINE_EXCEEDED, codes)
        self.assertTrue(result.anomaly)

    def test_baseline_equal_is_not_exceeded(self):
        """基線 0.68 に一致するだけでは異常としない（「超えた場合」と定義されている）。"""
        result = threshold.evaluate(wm(merged=100, derived=68), wm(merged=100, derived=68))
        self.assertEqual([a.code for a in result.alerts], [])

    def test_baseline_window_itself_is_not_an_anomaly(self):
        """基線そのもの（15/22 = 0.6818…）を基線超過にしない＝表示精度どうしで比較する。"""
        current = wm(merged=model.BASELINE_MERGED_PRS, derived=model.BASELINE_DERIVED_ISSUES)
        self.assertGreater(float(current.derived_per_pr_exact), model.BASELINE_DERIVED_PER_PR)
        self.assertEqual(current.derived_per_pr_rounded, model.BASELINE_DERIVED_PER_PR)
        self.assertEqual([a.code for a in threshold.evaluate(current, None).alerts], [])

    def test_trailing_regression(self):
        """直近4週 0.20 に対し 0.30（1.5 倍）で悪化と判定する。基線 0.68 は超えない。"""
        result = threshold.evaluate(wm(merged=10, derived=3), wm(merged=100, derived=20))
        codes = {a.code for a in result.alerts}
        self.assertEqual(codes, {threshold.TRAILING_REGRESSION})

    def test_trailing_regression_just_below_factor(self):
        result = threshold.evaluate(wm(merged=100, derived=29), wm(merged=100, derived=20))
        self.assertEqual([a.code for a in result.alerts], [])

    def test_trailing_zero_rate_flags_only_when_current_is_positive(self):
        self.assertEqual(
            [a.code for a in threshold.evaluate(wm(merged=10, derived=0), wm(merged=10, derived=0)).alerts],
            [],
        )
        self.assertEqual(
            [a.code for a in threshold.evaluate(wm(merged=10, derived=1), wm(merged=10, derived=0)).alerts],
            [threshold.TRAILING_REGRESSION],
        )

    def test_zero_denominator_is_skipped_not_normal(self):
        result = threshold.evaluate(wm(merged=0, derived=0), wm(merged=10, derived=1))
        self.assertFalse(result.anomaly)
        self.assertEqual([s.code for s in result.skipped], [threshold.SKIP_NO_DENOMINATOR])

    def test_missing_trailing_data_is_skipped(self):
        result = threshold.evaluate(wm(merged=10, derived=1), wm(merged=0, derived=0))
        self.assertEqual([s.code for s in result.skipped], [threshold.SKIP_NO_TRAILING_DATA])


class CollectTests(unittest.TestCase):
    def test_load_issues(self):
        payload = [
            {"number": 1, "createdAt": "2026-08-02T00:00:00Z", "closedAt": "", "body": "x"},
            {"number": 2, "createdAt": "2026-08-03T00:00:00Z", "closedAt": None, "body": None},
        ]
        records = collect.load_issues(payload)
        self.assertEqual([r.number for r in records], [1, 2])
        self.assertIsNone(records[0].closed_at)
        self.assertEqual(records[1].body, "")

    def test_load_pulls_skips_unmerged(self):
        payload = [
            {"number": 1, "mergedAt": "2026-08-02T00:00:00Z"},
            {"number": 2, "mergedAt": None},
        ]
        self.assertEqual([r.number for r in collect.load_pulls(payload)], [1])

    def test_malformed_payload_raises(self):
        with self.assertRaises(collect.CollectionError):
            collect.load_issues({"not": "a list"})
        with self.assertRaises(collect.CollectionError):
            collect.load_issues([{"number": 1}])
        with self.assertRaises(collect.CollectionError):
            collect.load_pulls([{"mergedAt": "2026-08-02T00:00:00Z"}])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        issues, pulls = _baseline_dataset()
        self.issues_path = os.path.join(self.tmp.name, "issues.json")
        self.pulls_path = os.path.join(self.tmp.name, "pulls.json")
        with open(self.issues_path, "w", encoding="utf-8") as handle:
            json.dump(
                [
                    {
                        "number": i.number,
                        "createdAt": model.format_timestamp(i.created_at),
                        "closedAt": model.format_timestamp(i.closed_at) if i.closed_at else None,
                        "body": i.body,
                    }
                    for i in issues
                ],
                handle,
            )
        with open(self.pulls_path, "w", encoding="utf-8") as handle:
            json.dump(
                [
                    {"number": p.number, "mergedAt": model.format_timestamp(p.merged_at)}
                    for p in pulls
                ],
                handle,
            )

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(
            [*argv, "--issues-json", self.issues_path, "--pulls-json", self.pulls_path],
            stdout=out,
            stderr=err,
        )
        return code, out.getvalue(), err.getvalue()

    def test_report_over_the_baseline_window(self):
        code, out, err = self.run_cli(
            [
                "report",
                "--repository",
                "hiratashinnya/review-system",
                "--window-start",
                "2026-08-02",
                "--window-end",
                "2026-08-16",
                "--now",
                "2026-08-16T00:00:00Z",
            ]
        )
        payload = json.loads(out)
        self.assertEqual(payload["schema_version"], model.SCHEMA_VERSION)
        self.assertEqual(payload["generated_at"], "2026-08-16T00:00:00Z")
        self.assertEqual(payload["report_window"]["denominator"]["merged_prs"], 22)
        self.assertEqual(payload["report_window"]["primary"]["derived_issues"], 15)
        self.assertEqual(payload["report_window"]["primary"]["derived_per_pr"], 0.68)
        self.assertEqual(payload["report_window"]["secondary"]["created_issues"], 41)
        self.assertEqual(payload["report_window"]["secondary"]["issues_per_pr"], 1.86)
        self.assertEqual(payload["report_window"]["open_issue_net_change"]["net"], 41)
        self.assertIn("trailing_4_weeks", payload)
        # 直近4週に merged PR が無いので比較は skip され、基線 0.68 は超えていない。
        self.assertFalse(payload["threshold"]["anomaly"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(err, "")  # 異常でなければ何も報告しない

    def test_anomalous_window_exits_20_and_reports(self):
        code, out, err = self.run_cli(
            [
                "report",
                "--repository",
                "hiratashinnya/review-system",
                "--window-start",
                "2026-08-02",
                "--window-end",
                "2026-08-04",
                "--now",
                "2026-08-04T00:00:00Z",
            ]
        )
        payload = json.loads(out)
        self.assertTrue(payload["threshold"]["anomaly"])
        self.assertEqual(code, cli.EXIT_ANOMALY)
        self.assertIn(threshold.BASELINE_EXCEEDED, err)

    def test_output_file(self):
        target = os.path.join(self.tmp.name, "report.json")
        code, out, _ = self.run_cli(
            [
                "report",
                "--repository",
                "hiratashinnya/review-system",
                "--window-start",
                "2026-08-02",
                "--window-end",
                "2026-08-16",
                "--now",
                "2026-08-16T00:00:00Z",
                "--output",
                target,
            ]
        )
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(out, "")
        with open(target, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["report_window"]["denominator"]["merged_prs"], 22)

    def test_verify_baseline_passes_on_matching_data(self):
        code, out, err = self.run_cli(
            ["verify-baseline", "--repository", "hiratashinnya/review-system"]
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(json.loads(out)["mismatches"], [])

    def test_verify_baseline_fails_on_drifted_data(self):
        with open(self.pulls_path, encoding="utf-8") as handle:
            pulls = json.load(handle)
        pulls.append({"number": 90001, "mergedAt": "2026-08-05T00:00:00Z"})
        with open(self.pulls_path, "w", encoding="utf-8") as handle:
            json.dump(pulls, handle)
        code, _, err = self.run_cli(
            ["verify-baseline", "--repository", "hiratashinnya/review-system"]
        )
        self.assertEqual(code, cli.EXIT_BASELINE_MISMATCH)
        self.assertIn("BASELINE_MISMATCH", err)

    def test_collection_error_exits_1(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(
            [
                "report",
                "--repository",
                "hiratashinnya/review-system",
                "--issues-json",
                os.path.join(self.tmp.name, "missing.json"),
                "--pulls-json",
                self.pulls_path,
                "--now",
                "2026-08-16T00:00:00Z",
            ],
            stdout=out,
            stderr=err,
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("defect_metrics:", err.getvalue())


class WindowResolutionTests(unittest.TestCase):
    """窓の決め方が現在時刻に依存する経路は、必ず ``now`` を固定して検証する。"""

    NOW = ts("2026-09-06T00:00:00Z")

    def test_both_ends_given(self):
        window = cli.resolve_window(self.NOW, "2026-08-02", "2026-08-16", 7)
        self.assertEqual((window.start, window.end), (ts("2026-08-02"), ts("2026-08-16")))

    def test_start_only_extends_forward(self):
        window = cli.resolve_window(self.NOW, "2026-08-02", None, 7)
        self.assertEqual(window.end, ts("2026-08-09"))

    def test_end_only_extends_backward(self):
        window = cli.resolve_window(self.NOW, None, "2026-08-16", 7)
        self.assertEqual(window.start, ts("2026-08-09"))

    def test_no_ends_uses_injected_now(self):
        window = cli.resolve_window(self.NOW, None, None, 7)
        self.assertEqual(window.end, self.NOW)
        self.assertEqual(window.start, ts("2026-08-30"))

    def test_resolve_now_prefers_the_injected_value(self):
        self.assertEqual(cli.resolve_now("2026-09-06T00:00:00Z"), self.NOW)

    def test_resolve_now_without_injection_returns_aware_utc(self):
        """既定分岐は wall clock を読むため、固定日付とは比較せず tz だけを検査する。"""
        value = cli.resolve_now(None)
        self.assertIsNotNone(value.tzinfo)
        self.assertEqual(value.utcoffset(), timedelta(0))


if __name__ == "__main__":
    unittest.main()
