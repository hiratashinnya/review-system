"""asset_parity.copilot_paths — Copilot (`.github/`) パスの単一定義の契約。

copilot_paths.py が「Copilot パスの単一定義」を名乗れるのは、他モジュールが `.github` を
直書きしていない間だけである。名乗りと実態の食い違い（パス変更で直す箇所が散らばる）を
ここで機械的に固定する。
限界：検査は個々の文字列定数だけを照合し、定数式（".github" + "/skills" 等の組み立て）は
評価しない（#637 で扱う）。単一定義の完全な保証ではなく、直書き防止の補助である。
"""

import ast
import re
import tempfile
import unittest
from pathlib import Path

import asset_parity
from asset_parity.copilot_paths import (
    copilot_agent_path,
    copilot_instructions_path,
    copilot_mirror_roots,
    copilot_prompt_path,
    copilot_skill_path,
    inline_slot_path,
)
from asset_parity.inventory import AGENT, SKILL

ROOT = Path("/repo")
PACKAGE_DIR = Path(asset_parity.__file__).resolve().parent
DEFINITION_MODULE = "copilot_paths.py"


# `.github` as a path component: bare, or followed by one or more `/` or `\` (repeated separators
# still name the directory) and a path char (incl. `{`/`%` placeholders) or the string end.
# Prose like `（.github/）` does not match: its separator is followed by a non-path char.
_GITHUB_PATH_COMPONENT = re.compile(r"(?<![\w.])\.github(?:[/\\]+[\w.*{%-]|[/\\]*$)")
_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _docstring_constants(tree: ast.AST) -> set[int]:
    owners = (n for n in ast.walk(tree) if isinstance(n, _DOCSTRING_OWNERS) and n.body)
    firsts = (n.body[0] for n in owners)
    return {id(s.value) for s in firsts if isinstance(s, ast.Expr)}


def _github_path_literal_lines(source: str) -> list[int]:
    """Lines of string literals (docstrings excluded) that spell a `.github` path, whole or part."""
    tree = ast.parse(source)
    docstrings = _docstring_constants(tree)
    return sorted(
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings and _GITHUB_PATH_COMPONENT.search(node.value)
    )


def _github_dir_literals(path: Path) -> list[int]:
    return _github_path_literal_lines(path.read_text(encoding="utf-8"))


class TestCopilotPaths(unittest.TestCase):
    def test_file_paths(self):
        self.assertEqual(copilot_skill_path("x", ROOT), ROOT / ".github/skills/x/SKILL.md")
        self.assertEqual(copilot_prompt_path("x", ROOT), ROOT / ".github/prompts/x.prompt.md")
        self.assertEqual(copilot_agent_path("x", ROOT), ROOT / ".github/agents/x.agent.md")
        self.assertEqual(copilot_instructions_path(ROOT), ROOT / ".github/copilot-instructions.md")

    def test_inline_slot_lies_under_the_instructions_file(self):
        slot = inline_slot_path("x", ROOT)
        self.assertEqual(slot.parent, copilot_instructions_path(ROOT))

    def test_inline_slot_is_never_a_file_wherever_something_sits_at_its_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slot = inline_slot_path("x", root)
            copilot_instructions_path(root).mkdir(parents=True)  # a directory, not the file
            plain = Path(str(slot))
            plain.write_text("a real file at the slot's path", encoding="utf-8")
            self.assertTrue(plain.is_file())
            self.assertFalse(slot.is_file())

    def test_mirror_roots_contain_the_expected_files(self):
        agent_roots = copilot_mirror_roots(AGENT, ROOT)
        self.assertIn(copilot_agent_path("x", ROOT).parent, agent_roots)
        skill_roots = copilot_mirror_roots(SKILL, ROOT)
        self.assertIn(copilot_skill_path("x", ROOT).parent.parent, skill_roots)
        self.assertIn(copilot_prompt_path("x", ROOT).parent, skill_roots)


class TestSingleDefinition(unittest.TestCase):
    def test_only_copilot_paths_module_spells_the_github_directory(self):
        modules = {m.relative_to(PACKAGE_DIR).as_posix(): m for m in PACKAGE_DIR.rglob("*.py")}
        stray = {
            name: lines
            for name, module in sorted(modules.items())
            if name != DEFINITION_MODULE and (lines := _github_dir_literals(module))
        }
        self.assertEqual(
            stray, {},
            "asset_parity modules other than copilot_paths.py spell the '.github' directory "
            "themselves; move the path into copilot_paths.py so it stays the single definition",
        )

    def test_definition_module_does_spell_it(self):
        self.assertTrue(_github_dir_literals(PACKAGE_DIR / DEFINITION_MODULE))


class TestGithubPathScanner(unittest.TestCase):
    """The scan must catch bare, compound, trailing-slash and template-fragment path
    spellings, and nothing but path spellings."""

    def test_bare_and_compound_path_literals_are_found(self):
        source = (
            'a = ".github"\n'
            'b = ".github/skills"\n'
            'c = ".github/prompts/x.prompt.md"\n'
            'd = f"{root}/.github/agents"\n'
            'e = "some/.github/skills/*"\n'
        )
        self.assertEqual(_github_path_literal_lines(source), [1, 2, 3, 4, 5])

    def test_trailing_slash_and_placeholder_fragments_are_found(self):
        source = (
            'a = Path(".github/")\n'
            'b = f".github/{name}/SKILL.md"\n'
            'c = ".github/{}/SKILL.md".format(name)\n'
            'd = ".github/%s/SKILL.md" % name\n'
            'e = f"{root}/.github/{kind}"\n'
        )
        self.assertEqual(_github_path_literal_lines(source), [1, 2, 3, 4, 5])

    def test_repeated_and_backslash_separators_are_found(self):
        source = (
            'a = ".github//skills"\n'
            'b = ".github\\\\skills"\n'
            'c = ".github/\\\\agents"\n'
            'd = ".github//"\n'
            'e = f".github\\\\\\\\{name}"\n'
        )
        self.assertEqual(_github_path_literal_lines(source), [1, 2, 3, 4, 5])

    def test_prose_mention_and_lookalike_names_are_not_found(self):
        source = (
            'reason = "Copilot（.github/）には等価物なし"\n'
            'tail = "Copilot（.github/）"\n'
            'repeated = "Copilot（.github//）"\n'
            'other = ".githubusercontent/x"\n'
            'dotted = "x.github/y"\n'
        )
        self.assertEqual(_github_path_literal_lines(source), [])

    def test_docstrings_are_not_found_but_other_strings_in_the_same_scope_are(self):
        source = (
            '"""Module doc naming .github/skills."""\n'
            'def f():\n'
            '    """Doc naming .github/agents."""\n'
            '    return ".github/prompts"\n'
        )
        self.assertEqual(_github_path_literal_lines(source), [4])


if __name__ == "__main__":
    unittest.main()
