"""Issue #539 の流入 role contract と流出 maintainability lint の契約。"""

from pathlib import Path
import tempfile
import unittest

from maintainability_lint.baseline import BaselineError, load_baseline
from maintainability_lint.cli import render_text
from maintainability_lint.scanner import build_baseline, empty_baseline, scan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _violations(root: Path, baseline=None):
    report = scan(root, empty_baseline() if baseline is None else baseline)
    return [item for item in report.findings if item.status == "violation"]


class MaintainabilityLintSyntheticTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def test_module_over_100_physical_lines_is_rejected(self):
        _write(self.root, "review_system/too_large.py", "value = 1\n" * 101)
        findings = _violations(self.root)
        self.assertEqual([item.rule for item in findings], ["module-over-100-lines"])

    def test_exact_module_baseline_is_accepted_but_growth_is_rejected(self):
        relative = "review_system/legacy.py"
        _write(self.root, relative, "value = 1\n" * 101)
        baseline = build_baseline(self.root)
        self.assertFalse(_violations(self.root, baseline))
        _write(self.root, relative, "value = 1\n" * 102)
        rules = {item.rule for item in _violations(self.root, baseline)}
        self.assertEqual(rules, {"module-over-100-lines"})

    def test_same_length_module_edit_is_rejected(self):
        relative = "review_system/legacy.py"
        _write(self.root, relative, "value = 1\n" * 101)
        baseline = build_baseline(self.root)
        self.assertFalse(_violations(self.root, baseline))
        _write(self.root, relative, "value = 2\n" + "value = 1\n" * 100)
        self.assertEqual(
            [item.rule for item in _violations(self.root, baseline)],
            ["module-over-100-lines"],
        )

    def test_resolved_debt_makes_baseline_stale(self):
        relative = "review_system/legacy.py"
        _write(self.root, relative, "value = 1\n" * 101)
        baseline = build_baseline(self.root)
        _write(self.root, relative, "value = 1\n" * 100)
        self.assertEqual(
            [item.rule for item in _violations(self.root, baseline)],
            ["stale-baseline"],
        )

    def test_four_line_comment_is_rejected_and_three_lines_are_allowed(self):
        _write(self.root, "review_system/ok.py", "# one\n# two\n# three\nvalue = 1\n")
        self.assertFalse(_violations(self.root))
        _write(self.root, "review_system/bad.py", "# one\n# two\n# three\n# four\n")
        self.assertEqual(
            [item.rule for item in _violations(self.root)],
            ["comment-over-3-lines"],
        )

    def test_comment_fingerprint_baseline_does_not_mask_edits(self):
        relative = "review_system/legacy.py"
        _write(self.root, relative, "# one\n# two\n# three\n# four\n")
        baseline = build_baseline(self.root)
        self.assertFalse(_violations(self.root, baseline))
        _write(self.root, relative, "# changed\n# two\n# three\n# four\n")
        rules = {item.rule for item in _violations(self.root, baseline)}
        self.assertEqual(rules, {"comment-over-3-lines", "stale-baseline"})

    def test_reduced_duplicate_comment_count_makes_baseline_stale(self):
        relative = "review_system/legacy.py"
        block = "# one\n# two\n# three\n# four\n"
        _write(self.root, relative, block + "value = 1\n" + block)
        baseline = build_baseline(self.root)
        _write(self.root, relative, block + "value = 1\n")
        self.assertEqual(
            [item.rule for item in _violations(self.root, baseline)],
            ["stale-baseline"],
        )

    def test_docstring_is_not_a_code_comment(self):
        _write(self.root, "review_system/docs.py", '"""one\ntwo\nthree\nfour\n"""\n')
        self.assertFalse(_violations(self.root))

    def test_dataclass_and_concrete_logic_class_must_be_separate(self):
        _write(
            self.root,
            "review_system/mixed.py",
            "from dataclasses import dataclass\n"
            "@dataclass\nclass Payload:\n    value: str\n"
            "class Processor:\n    def process(self):\n        return 1\n",
        )
        self.assertEqual(
            [item.rule for item in _violations(self.root)],
            ["data-and-logic-class-cohabitation"],
        )

    def test_dataclass_imported_under_alias_is_detected(self):
        _write(
            self.root,
            "review_system/mixed.py",
            "from dataclasses import dataclass as dc\n"
            "@dc\nclass Payload:\n    value: str\n"
            "class Processor:\n    def process(self):\n        return 1\n",
        )
        self.assertEqual(
            [item.rule for item in _violations(self.root)],
            ["data-and-logic-class-cohabitation"],
        )

    def test_dataclasses_module_decorator_is_detected(self):
        _write(
            self.root,
            "review_system/mixed.py",
            "import dataclasses\n"
            "@dataclasses.dataclass\nclass Payload:\n    value: str\n"
            "class Processor:\n    def process(self):\n        return 1\n",
        )
        self.assertEqual(
            [item.rule for item in _violations(self.root)],
            ["data-and-logic-class-cohabitation"],
        )

    def test_unrelated_dataclass_suffix_decorator_is_not_data_class(self):
        _write(
            self.root,
            "review_system/not_data.py",
            "from helpers import not_a_dataclass\n"
            "@not_a_dataclass\nclass Payload:\n    value: str\n"
            "class Processor:\n    def process(self):\n        return 1\n",
        )
        self.assertFalse(_violations(self.root))

    def test_same_class_names_with_body_edit_are_rejected(self):
        relative = "review_system/mixed.py"
        source = (
            "from dataclasses import dataclass\n"
            "@dataclass\nclass Payload:\n    value: str\n"
            "class Processor:\n    def process(self):\n        return VALUE\n"
        )
        _write(self.root, relative, source.replace("VALUE", "1"))
        baseline = build_baseline(self.root)
        self.assertFalse(_violations(self.root, baseline))
        _write(self.root, relative, source.replace("VALUE", "2"))
        self.assertEqual(
            [item.rule for item in _violations(self.root, baseline)],
            ["data-and-logic-class-cohabitation"],
        )

    def test_exception_and_abstract_contract_are_not_logic_classes(self):
        _write(
            self.root,
            "review_system/contracts.py",
            "from dataclasses import dataclass\n"
            "@dataclass\nclass Payload:\n    value: str\n"
            "class PayloadError(Exception):\n    pass\n"
            "class Port:\n    def run(self):\n        raise NotImplementedError()\n",
        )
        self.assertFalse(_violations(self.root))

    def test_bare_not_implemented_raise_is_not_logic(self):
        _write(
            self.root,
            "review_system/contracts.py",
            "from dataclasses import dataclass\n"
            "@dataclass\nclass Payload:\n    value: str\n"
            "class Port:\n    def run(self):\n        raise NotImplementedError\n",
        )
        self.assertFalse(_violations(self.root))

    def test_new_top_level_python_package_is_scanned(self):
        _write(self.root, "future_harness/__init__.py", "")
        _write(self.root, "future_harness/too_large.py", "value = 1\n" * 101)
        ignored = (
            ".claude/worktrees/secondary/pkg/too_large.py",
            ".cache/pkg/too_large.py",
            ".pixi/envs/default/lib/too_large.py",
            ".ruff_cache/too_large.py",
            "__pypackages__/3.13/lib/too_large.py",
            "env/lib/site-packages/too_large.py",
            "env.bak/lib/site-packages/too_large.py",
            "future_harness/.cache/generated.py",
            "future_harness/build/generated.py",
            "future_harness/tmp/generated.py",
            "tmp/too_large.py",
        )
        for relative in ignored:
            _write(self.root, relative, "value = 1\n" * 101)
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        outside = Path(external.name)
        _write(outside, "too_large.py", "value = 1\n" * 101)
        (self.root / "linked_harness").symlink_to(outside, target_is_directory=True)
        (self.root / "future_harness" / "linked.py").symlink_to(
            outside / "too_large.py"
        )
        self.assertEqual(
            [(item.path, item.rule) for item in _violations(self.root)],
            [("future_harness/too_large.py", "module-over-100-lines")],
        )


class MaintainabilityLintRepositoryTests(unittest.TestCase):
    def test_committed_baseline_is_well_formed_and_repo_is_clean(self):
        baseline = load_baseline()
        report = scan(REPO_ROOT, baseline)
        self.assertFalse(
            [item for item in report.findings if item.status == "violation"],
            render_text(report),
        )

    def test_new_lint_modules_obey_their_own_100_line_rule(self):
        for path in (REPO_ROOT / "maintainability_lint").glob("*.py"):
            self.assertLessEqual(
                len(path.read_text(encoding="utf-8").splitlines()),
                100,
                path.relative_to(REPO_ROOT).as_posix(),
            )

    def test_three_issue_roles_receive_the_same_owner_principles(self):
        required = (
            "名前だけで file / class / function の責務が一意に伝わる",
            "コードコメントは3行以内",
            "Python module は100物理行以内",
            "`@dataclass` と具体ロジック class は同一 file に置かない",
            "python3 -m maintainability_lint check",
        )
        for name in ("issue-implementer", "issue-fixer", "pr-reviewer"):
            text = (REPO_ROOT / ".ai" / "agents" / f"{name}.md").read_text(encoding="utf-8")
            for phrase in required:
                self.assertIn(phrase, text, f"{name}: missing {phrase}")

    def test_invalid_baseline_is_rejected_fail_close(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "baseline.json"
            path.write_text('{"schema_version": 1}', encoding="utf-8")
            with self.assertRaises(BaselineError):
                load_baseline(path)

    def test_new_harness_is_classified_registered_and_wired_to_ci(self):
        decision_rule = (REPO_ROOT / ".claude/rules/02-decision-process.md").read_text(encoding="utf-8")
        tailoring = (REPO_ROOT / ".claude/tailoring-registry.md").read_text(encoding="utf-8")
        workflow = (REPO_ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("`maintainability_lint`", decision_rule)
        self.assertIn("`maintainability_lint`", tailoring)
        self.assertIn("python3 -m maintainability_lint check", workflow)


if __name__ == "__main__":
    unittest.main()
