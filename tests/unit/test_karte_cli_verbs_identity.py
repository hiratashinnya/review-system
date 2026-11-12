"""分割後の再エクスポートと依存方向を固定する。"""
import ast
import importlib
from pathlib import Path
import unittest

from karte import cli

MODULES = (
    "report_source", "close_attempt_target", "verb_ingest_review", "verb_append",
    "close_attempt_report", "verb_close_attempt", "verb_check", "verb_show",
    "parser_ingest_args", "parser_attempt_args", "parser_inspect_args", "parser_core",
)


class TestCliVerbIdentity(unittest.TestCase):
    def test_reexports_are_identical(self):
        names = {
            "report_source": {"_read_report": "read_report"},
            "close_attempt_target": {
                "_resolve_close_attempt_number": "resolve_close_attempt_number",
                "_validate_outcome": "validate_outcome",
            },
            "verb_ingest_review": {"_prepare_ingest": "prepare_ingest", "cmd_ingest_review": "cmd_ingest_review"},
            "verb_append": {"cmd_append": "cmd_append"},
            "verb_close_attempt": {"cmd_close_attempt": "cmd_close_attempt"},
            "verb_check": {"cmd_check": "cmd_check"},
            "verb_show": {"cmd_render": "cmd_render", "cmd_status": "cmd_status"},
            "parser_core": {"build_parser": "build_parser"},
        }
        for module, aliases in names.items():
            target = importlib.import_module("karte." + module)
            for alias, name in aliases.items():
                with self.subTest(alias=alias):
                    self.assertIs(getattr(cli, alias), getattr(target, name))

    def test_lock_and_prepare_declarations(self):
        for name, locked in (("ingest_review", True), ("append", True), ("close_attempt", True),
                             ("render", False), ("check", False), ("status", False)):
            with self.subTest(verb=name):
                verb = getattr(cli, "cmd_" + name)
                self.assertIs(verb.locked, locked)
                cells = dict(zip(verb.__code__.co_freevars, (cell.cell_contents for cell in verb.__closure__)))
                self.assertIs(cells["prepare"], cli._prepare_ingest if name == "ingest_review" else None)

    def test_no_dependency_on_cli(self):
        for name in MODULES:
            module_file = importlib.import_module("karte." + name).__file__
            assert module_file is not None
            path = Path(module_file)
            with self.subTest(module=name):
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                    if isinstance(node, ast.Import):
                        self.assertFalse(any(alias.name == "karte.cli" or alias.name.startswith("karte.cli.") for alias in node.names))
                    elif isinstance(node, ast.ImportFrom):
                        imports_cli = node.module in ("karte.cli", "cli") or (
                            node.module in (None, "", "karte") and any(alias.name == "cli" for alias in node.names)
                        )
                        self.assertFalse(imports_cli, f"{name} imports karte.cli")
