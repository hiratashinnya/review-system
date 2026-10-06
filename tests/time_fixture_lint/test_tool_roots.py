"""CIに直結するtool別TCをfixture・literal検査から漏らさない。"""

from pathlib import Path
import tempfile
import unittest

from time_fixture_lint.scanner import scan


class ToolTestRootsCanaryTests(unittest.TestCase):
    def test_jev_fixture_consumer_is_checked_with_existing_unit_consumer(self):
        for folder in ("jev_hooks", "time_fixture_lint"):
            with self.subTest(folder=folder):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    fixture = root / "tests/fixtures/widget/waiver.yml"
                    fixture.parent.mkdir(parents=True)
                    fixture.write_text('expires_at: "2026-01-08T00:00:00Z"\n')
                    consumers = {
                        "unit": "def test_x():\n    now=datetime(2026, 1, 2)\n    load('waiver.yml')\n",
                        folder: "def test_x():\n    load('waiver.yml')\n",
                    }
                    for folder, source in consumers.items():
                        path = root / "tests" / folder / "test_widget.py"
                        path.parent.mkdir(parents=True)
                        path.write_text(source)
                    report = scan(root)
                    self.assertEqual(len(report.violations), 1)
                    self.assertEqual(report.violations[0].status, "violation")
                    self.assertIn(f"tests/{folder}/test_widget.py", report.violations[0].detail)

    def test_jev_fixed_python_epoch_is_checked_without_unit_directory(self):
        for folder in ("jev_hooks", "time_fixture_lint"):
            with self.subTest(folder=folder):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    path = root / f"tests/{folder}/test_widget.py"
                    path.parent.mkdir(parents=True)
                    path.write_text("RESET_EPOCH = 1783767886\n")
                    report = scan(root)
                    self.assertEqual(len(report.violations), 1)
                    self.assertEqual(report.violations[0].path, f"tests/{folder}/test_widget.py")
                    self.assertEqual(report.violations[0].name, "RESET_EPOCH")

    def test_jev_protected_literal_is_checked_and_not_rejected(self):
        for folder in ("jev_hooks", "time_fixture_lint"):
            with self.subTest(folder=folder):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    path = root / f"tests/{folder}/test_widget.py"
                    path.parent.mkdir(parents=True)
                    path.write_text(
                        "def test_x():\n    now=datetime(2026, 1, 2)\n"
                        "    value={'expires_at': '2026-01-08T00:00:00Z'}\n"
                    )
                    report = scan(root)
                    self.assertEqual(len(report.findings), 1)
                    self.assertEqual(report.findings[0].status, "protected")
                    self.assertEqual(report.violations, [])
