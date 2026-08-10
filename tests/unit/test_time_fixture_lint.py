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
        # waiver_valid.yml/waiver_expired.yml は clock 保護（mock.patch/now=注入）で守られて
        # いるべきで、allowlist で誤魔化していないことを明示的に確認する（Issue #344 の中心事例）。
        report = scan(REPO_ROOT)
        waiver_hits = [f for f in report.findings if "waiver_valid.yml" in f.path or "waiver_expired.yml" in f.path]
        self.assertTrue(waiver_hits, "waiver fixtures should have been scanned")
        for f in waiver_hits:
            self.assertEqual(f.status, "protected", f"{f.path}:{f.line} should be protected, got {f.status}")


if __name__ == "__main__":
    unittest.main()
