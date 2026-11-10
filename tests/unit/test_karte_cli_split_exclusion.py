"""分割後の解除判定の一元化と CLI 互換名を検査する。"""

import argparse
import ast
import contextlib
import importlib
import inspect
import io
import tempfile
import unittest
from pathlib import Path

from karte import cli, finding_record, model
from tests.unit.test_karte_cli_split_compat import cases, prepare


MODULES = (
    "stall_detection", "saturation_groups", "status_verdict", "status_findings",
    "status_payload", "status_text", "status_finding_lines", "render_attempt_lines",
    "render_finding_lines", "render_saturation_lines", "render_text",
)
RULE_NAMES = {"CLEARING_HARM", "CLEARING_DISPOSITIONS"}


def references(tree):
    return {node.id if isinstance(node, ast.Name) else node.attr
            for node in ast.walk(tree)
            if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load)} & RULE_NAMES


class TestSplitExclusion(unittest.TestCase):
    def test_split_modules_do_not_reference_clearing_constants(self):
        directory = Path(cli.__file__).parent
        actual = {path.stem for path in directory.glob("*.py")}
        self.assertTrue(set(MODULES) <= actual, set(MODULES) - actual)
        for name in ("cli", *MODULES):
            with self.subTest(module=name):
                module = importlib.import_module(f"karte.{name}")
                self.assertFalse(references(ast.parse(inspect.getsource(module))))

    def test_only_finding_cleared_by_disposition_uses_constants(self):
        directory = Path(cli.__file__).parent
        found = set()
        for path in directory.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            hits = references(tree)
            if hits:
                self.assertEqual(path.name, "finding_record.py")
                found |= hits
                finding = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Finding")
                method = next(n for n in finding.body if isinstance(n, ast.FunctionDef) and n.name == "cleared_by_disposition")
                self.assertEqual(hits, references(method))
                all_loads = [node.id if isinstance(node, ast.Name) else node.attr
                             for node in ast.walk(tree)
                             if isinstance(node, (ast.Name, ast.Attribute))
                             and isinstance(node.ctx, ast.Load)
                             and (node.id if isinstance(node, ast.Name) else node.attr) in RULE_NAMES]
                method_loads = [node.id if isinstance(node, ast.Name) else node.attr
                                for node in ast.walk(method)
                                if isinstance(node, (ast.Name, ast.Attribute))
                                and isinstance(node.ctx, ast.Load)
                                and (node.id if isinstance(node, ast.Name) else node.attr) in RULE_NAMES]
                self.assertCountEqual(all_loads, method_loads)
        self.assertEqual(found, RULE_NAMES)
        self.assertTrue(inspect.getsource(finding_record.Finding.cleared_by_disposition.fget))

    def test_cli_compatibility_attributes_exist(self):
        for name in ("_saturated_groups", "_priors_for", "_stalled_ids", "_group_directive",
                     "_status_payload", "STALL_ROUNDS", "model"):
            with self.subTest(name=name):
                self.assertTrue(hasattr(cli, name), name)

    def test_close_attempt_prints_saturation_directive(self):
        karte = cases()["pair-saturated-multiple-results"][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prepare(root, model.dumps(karte))
            diff = root / "empty.diff"
            diff.write_text("", encoding="utf-8")
            args = argparse.Namespace(repo_root=str(root), issue="307", attempt="2",
                                      outcome="no-change", finding_ids=None, base="HEAD",
                                      diff_file=str(diff), note="")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.cmd_close_attempt(args)
            self.assertEqual(code, 0, err.getvalue())
            self.assertEqual(err.getvalue(), "")
            self.assertIn("飽和した", out.getvalue())
            self.assertIn("DIRECTIVE", out.getvalue())
