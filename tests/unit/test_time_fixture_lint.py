"""time_fixture_lint.scanner — 時刻依存 test data 検査の契約（Issue #344 手当てB）。

2系統のテスト:
  * ``ScannerSyntheticTests`` — 合成 tmp ツリーで各検出器の判定ロジック
    （violation/protected/no_consumer/allowlisted）をピンポイントで検証する。
  * ``RealRepoRegressionTests`` — このリポジトリ実物に対して scan() を実行し、
    violation が0件であることを確認する（新規の再武装を検知する実質的な回帰ゲート。
    `.github/workflows/` からは `python3 -m time_fixture_lint check` を直接叩くが、
    こちらは `python3 -m unittest discover` 経路でも同じ検査が効くようにする）。
"""

from pathlib import Path
import tempfile
import unittest

from time_fixture_lint.allowlist import ALLOWLIST, is_allowlisted
from time_fixture_lint.scanner import scan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ScannerSyntheticTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_unprotected_fixture_expiry_field_is_violation(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'approved_at: "2026-01-01T00:00:00Z"\nexpires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "def test_x():\n    load('waiver.yml')\n",
        )
        report = scan(self.root)
        statuses = {(f.name, f.status) for f in report.findings}
        self.assertIn(("approved_at", "violation"), statuses)
        self.assertIn(("expires_at", "violation"), statuses)
        self.assertEqual(len(report.violations), 2)

    def test_protected_fixture_expiry_field_via_mock_patch_is_not_violation(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'approved_at: "2026-01-01T00:00:00Z"\nexpires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "from unittest.mock import patch\n"
            "def test_x():\n"
            "    with patch('widget.resolver.datetime') as clock:\n"
            "        load('waiver.yml')\n",
        )
        report = scan(self.root)
        self.assertEqual(report.violations, [])
        statuses = {f.status for f in report.findings}
        self.assertEqual(statuses, {"protected"})

    def test_protected_fixture_via_now_kwarg_injection_is_not_violation(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'approved_at: "2026-01-01T00:00:00Z"\nexpires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "from datetime import datetime\n"
            "def test_x():\n"
            "    ctx = Context(now=datetime(2026, 1, 2))\n"
            "    load('waiver.yml')\n",
        )
        report = scan(self.root)
        self.assertEqual(report.violations, [])

    def test_fixture_with_no_referencing_test_is_no_consumer(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'expires_at: "2026-01-08T00:00:00Z"\n',
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].status, "no_consumer")

    def test_inert_created_at_field_is_never_flagged(self):
        _write(
            self.root,
            "tests/fixtures/widget/thing.json",
            '{\n  "created_at": "2026-01-01T00:00:00Z",\n  "fetched_at": "2026-01-01T00:00:00Z"\n}\n',
        )
        _write(self.root, "tests/unit/test_widget_thing.py", "def test_x():\n    pass\n")
        report = scan(self.root)
        self.assertEqual(report.findings, [])

    def test_bare_epoch_constant_in_python_test_without_protection_is_violation(self):
        _write(
            self.root,
            "tests/unit/test_widget_epoch.py",
            "RESET_EPOCH = 1783767886\n\ndef test_x():\n    assert RESET_EPOCH\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].name, "RESET_EPOCH")

    def test_bare_epoch_paired_with_time_time_relative_offset_is_not_flagged(self):
        _write(
            self.root,
            "tests/unit/test_widget_epoch.py",
            "import time\n\n"
            "def test_x():\n"
            "    future_epoch = int(time.time()) + 3600\n"
            "    assert future_epoch\n",
        )
        report = scan(self.root)
        self.assertEqual(report.findings, [])

    def test_allowlisted_hit_is_suppressed_from_violations(self):
        # allowlist.py の実エントリ（test_codex_rate_limit_api.py の resetsAt/NOW）を
        # 合成ツリーでも再現し、is_allowlisted() が (path, name) の組で一致することを確認する。
        entry = ALLOWLIST[0]
        found = is_allowlisted(entry.path, entry.name)
        self.assertIsNotNone(found)
        self.assertEqual(found.reason, entry.reason)
        self.assertIsNone(is_allowlisted(entry.path, "totally-different-name"))

    # --- PR #349 是正: F-344-01（保護判定のスコープ化） ------------------------------

    def test_unrelated_patch_in_separate_function_does_not_protect(self):
        # clock と無関係な patch() が「別の」テスト関数にあるだけで保護済みと誤判定しないこと
        # （#339 と同クラスの再武装を再現する評価回帰・F-344-01 の evidence 相当）。
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'expires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "from unittest.mock import patch\n"
            "def test_x():\n"
            "    load('waiver.yml')\n"
            "\n"
            "def test_unrelated():\n"
            "    with patch('widget.cli.resolve_token'):\n"
            "        pass\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].status, "violation")

    def test_unrelated_patch_in_same_function_does_not_protect(self):
        # clock と無関係な patch() が「同じ」関数内にあっても、対象文字列が clock 関連語を
        # 含まなければ保護済みとみなさない（PROTECTION_MARKER_RE の対象語彙narrowing）。
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'expires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "from unittest.mock import patch\n"
            "def test_x():\n"
            "    with patch('widget.cli.resolve_token'):\n"
            "        load('waiver.yml')\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].status, "violation")

    def test_fixture_and_clock_patch_split_across_local_helpers_is_protected(self):
        # test_blocker_gate_contract_cli.py の waiver_material()/evaluate_during_waiver_validity()
        # パターン（fixture を読むヘルパーと clock を patch するヘルパーが別関数）を合成再現し、
        # 呼び出しグラフの無向連結成分により正しく protected と判定されることを確認する。
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            'expires_at: "2026-01-08T00:00:00Z"\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "from unittest.mock import patch\n"
            "def build_material():\n"
            "    return load('waiver.yml')\n"
            "\n"
            "def evaluate_with_clock(material):\n"
            "    with patch('widget.resolver.datetime') as clock:\n"
            "        return use(material)\n"
            "\n"
            "def test_x():\n"
            "    material = build_material()\n"
            "    evaluate_with_clock(material)\n",
        )
        report = scan(self.root)
        self.assertEqual(report.violations, [])
        statuses = {f.status for f in report.findings}
        self.assertEqual(statuses, {"protected"})

    def test_python_literal_protected_only_within_its_own_function_scope(self):
        # scan_python_literals も同じスコープ化の対象（F-344-01 の残存事例）。
        # 保護マーカーが「別の」関数にあるだけでは保護済みと判定しない。
        _write(
            self.root,
            "tests/unit/test_widget_literal.py",
            "from unittest.mock import patch\n"
            "def test_unprotected():\n"
            '    payload = {"expires_at": "2026-01-08T00:00:00Z"}\n'
            "    assert payload\n"
            "\n"
            "def test_other_protected():\n"
            "    with patch('widget.resolver.datetime'):\n"
            "        pass\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].name, "expires_at")

    # --- PR #349 是正: F-344-03（引用符・1行インライン JSON） ------------------------

    def test_single_quoted_yaml_value_unprotected_is_violation(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.yml",
            "expires_at: '2026-01-08T00:00:00Z'\n",
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver.py",
            "def test_x():\n    load('waiver.yml')\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].name, "expires_at")

    def test_one_line_inline_json_python_literal_unprotected_is_violation(self):
        _write(
            self.root,
            "tests/unit/test_widget_inline_json.py",
            "def test_x():\n"
            '    payload = {"id": "abc", "expires_at": "2026-01-08T00:00:00Z"}\n'
            "    assert payload\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].name, "expires_at")

    def test_fixture_json_one_line_inline_object_unprotected_is_violation(self):
        _write(
            self.root,
            "tests/fixtures/widget/waiver.json",
            '{"id": "abc", "expires_at": "2026-01-08T00:00:00Z"}\n',
        )
        _write(
            self.root,
            "tests/unit/test_widget_waiver_json.py",
            "def test_x():\n    load('waiver.json')\n",
        )
        report = scan(self.root)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].name, "expires_at")


class RealRepoRegressionTests(unittest.TestCase):
    """このリポジトリ実物に対する回帰ゲート。allowlist で明示されていない限り violation は0件。"""

    def test_no_unexplained_violations_in_repo(self):
        report = scan(REPO_ROOT)
        if report.violations:
            details = "\n".join(f"  {f.path}:{f.line} {f.name}={f.value!r} ({f.status}) {f.detail}" for f in report.violations)
            self.fail(
                "time_fixture_lint found unprotected time-dependent test data:\n"
                f"{details}\n"
                "Either control the clock (mock.patch/now= injection) or add a justified "
                "entry to time_fixture_lint/allowlist.py."
            )

    def test_known_waiver_fixture_is_protected_not_allowlisted(self):
        # blocker_gate の waiver fixture のうち、実際に clock 比較を行うテスト
        # （WaiverVerifierTests・setUp で now= 注入により保護済み）が消費する2種は、
        # allowlist で誤魔化さず "protected" になっているべきことを明示的に確認する
        # （Issue #344 の中心事例）。対象ファイル名はここでは断片から組み立てる——
        # このメソッドの source text に対象名をリテラルで書くと、time_fixture_lint 自身の
        # 素朴な substring 一致による「参照テスト」判定に、このテストファイル自身が
        # ヒットしてしまうため（PR #349・F-344-01 是正で保護判定がファイル全文検索から
        # 参照箇所スコープへ絞られたことで顕在化した自己参照アーティファクト。
        # schema_only_waiver.yml を切り出した理由の変種）。
        name_prefix, name_suffixes, name_ext = "waiver_", ("valid", "expired"), ".yml"
        target_names = {name_prefix + suffix + name_ext for suffix in name_suffixes}
        report = scan(REPO_ROOT)
        waiver_hits = [f for f in report.findings if any(name in f.path for name in target_names)]
        self.assertTrue(waiver_hits, "waiver fixtures should have been scanned")
        for f in waiver_hits:
            self.assertEqual(f.status, "protected", f"{f.path}:{f.line} should be protected, got {f.status}")


if __name__ == "__main__":
    unittest.main()
