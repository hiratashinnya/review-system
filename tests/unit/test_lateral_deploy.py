"""TC-lateral-deploy-001: Asset lateral deployment parser and converters.

Unit tests for parse_frontmatter(), conversion functions, and skip logic.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

# Import the script module by explicit file location (it lives under scripts/,
# outside the review_system package, so we load it without touching sys.path
# per the repo's import policy in docs/design/02-module-architecture.md).
_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "lateral_deploy.py"
_spec = importlib.util.spec_from_file_location("lateral_deploy", _SCRIPT_PATH)
lateral_deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lateral_deploy)

parse_frontmatter = lateral_deploy.parse_frontmatter
should_skip_conversion = lateral_deploy.should_skip_conversion
convert_skill_to_prompt = lateral_deploy.convert_skill_to_prompt
convert_agent_to_instructions = lateral_deploy.convert_agent_to_instructions
extract_spec_principles = lateral_deploy.extract_spec_principles
scan_assets = lateral_deploy.scan_assets
generate_copilot_instructions = lateral_deploy.generate_copilot_instructions
write_outputs = lateral_deploy.write_outputs


class TestParseFrontmatter(unittest.TestCase):
    """Test parse_frontmatter() with line-based delimiter scanning."""

    def test_normal_frontmatter(self):
        """Parse valid frontmatter with hyphenated keys."""
        text = """\
---
name: align
description: Pre-work alignment
disable-model-invocation: false
user-invocable: true
---
# Body heading
Content here."""
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm["name"], "align")
        self.assertEqual(fm["description"], "Pre-work alignment")
        self.assertEqual(fm["disable-model-invocation"], "false")
        self.assertEqual(fm["user-invocable"], "true")
        self.assertIn("# Body heading", body)

    def test_frontmatter_with_dashes_in_value(self):
        """Parse frontmatter where value contains --- (delimiter should scan line-based)."""
        text = """\
---
name: test-skill
description: This skill --- does something
---
# Body"""
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm["name"], "test-skill")
        # Should not terminate early when value contains ---
        self.assertEqual(fm["description"], "This skill --- does something")
        self.assertIn("# Body", body)

    def test_missing_closing_delimiter(self):
        """Should fail if closing --- is missing."""
        text = """\
---
name: align
description: no closing delimiter"""
        with self.assertRaises(ValueError) as ctx:
            parse_frontmatter(text)
        self.assertIn("closing ---", str(ctx.exception))

    def test_no_frontmatter(self):
        """Return empty dict and full text if no frontmatter."""
        text = "Just body content"
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, text)

    def test_empty_file(self):
        """Handle empty input."""
        fm, body = parse_frontmatter("")
        self.assertEqual(fm, {})
        self.assertEqual(body, "")

    def test_quoted_values(self):
        """Strip quotes from values."""
        text = """\
---
name: "quoted-name"
description: 'single-quoted'
plain: unquoted
---
Body"""
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm["name"], "quoted-name")
        self.assertEqual(fm["description"], "single-quoted")
        self.assertEqual(fm["plain"], "unquoted")


class TestShouldSkipConversion(unittest.TestCase):
    """Test should_skip_conversion() logic."""

    def test_skip_when_user_invocable_false(self):
        """Skip if user-invocable: false."""
        fm = {"user-invocable": "false"}
        self.assertTrue(should_skip_conversion(fm))

    def test_not_skip_when_user_invocable_true(self):
        """Don't skip if user-invocable: true."""
        fm = {"user-invocable": "true"}
        self.assertFalse(should_skip_conversion(fm))

    def test_not_skip_when_user_invocable_missing(self):
        """Don't skip if user-invocable is missing (default is true)."""
        fm = {"name": "test"}
        self.assertFalse(should_skip_conversion(fm))

    def test_not_skip_when_user_invocable_other(self):
        """Don't skip if user-invocable has other value."""
        fm = {"user-invocable": "maybe"}
        self.assertFalse(should_skip_conversion(fm))


class TestConvertSkillToPrompt(unittest.TestCase):
    """Test convert_skill_to_prompt() format conversion."""

    def test_basic_conversion(self):
        """Convert skill to prompt format with safe YAML."""
        skill_file = Path("skills/align/SKILL.md")
        fm = {"name": "align", "description": "Alignment skill"}
        body = "# Alignment\nContent"
        output_path, content = convert_skill_to_prompt(skill_file, fm, body)

        self.assertEqual(output_path, ".github/prompts/align.prompt.md")
        self.assertIn("mode: 'agent'", content)
        self.assertIn("description: 'Alignment skill'", content)
        self.assertIn("# Alignment\nContent", content)

    def test_escape_single_quotes_in_description(self):
        """Escape single quotes in description for YAML safety."""
        skill_file = Path("skills/test/SKILL.md")
        fm = {"name": "test", "description": "It's a test"}
        body = "Body"
        _, content = convert_skill_to_prompt(skill_file, fm, body)
        # Single quote should be escaped as '' in YAML
        self.assertIn("It''s a test", content)

    def test_remove_newlines_in_description(self):
        """Remove newlines from description for YAML safety."""
        skill_file = Path("skills/test/SKILL.md")
        fm = {"name": "test", "description": "Line 1\nLine 2"}
        body = "Body"
        _, content = convert_skill_to_prompt(skill_file, fm, body)
        # Newlines should be removed
        self.assertIn("Line 1 Line 2", content)

    def test_fallback_to_parent_name(self):
        """Use parent directory name if name not in frontmatter."""
        skill_file = Path("some/path/myskill/SKILL.md")
        fm = {"description": "test"}
        body = "Body"
        output_path, _ = convert_skill_to_prompt(skill_file, fm, body)
        # Should use parent dir name
        self.assertEqual(output_path, ".github/prompts/myskill.prompt.md")


class TestConvertAgentToInstructions(unittest.TestCase):
    """Test convert_agent_to_instructions() format conversion."""

    def test_basic_conversion(self):
        """Convert agent to instructions format."""
        agent_file = Path("agents/spec-inspector.md")
        fm = {"name": "spec-inspector", "tools": "Read,Grep", "model": "opus"}
        body = "# Inspector\nContent"
        output_path, content = convert_agent_to_instructions(agent_file, fm, body)

        self.assertEqual(output_path, ".github/instructions/spec-inspector.instructions.md")
        self.assertIn("applyTo: '**'", content)
        self.assertIn("<!-- tools: Read,Grep | model: opus -->", content)
        self.assertIn("# Inspector\nContent", content)

    def test_fallback_to_stem(self):
        """Use file stem if name not in frontmatter."""
        agent_file = Path("agents/my-agent.md")
        fm = {}
        body = "Body"
        output_path, _ = convert_agent_to_instructions(agent_file, fm, body)
        # Should use file stem
        self.assertEqual(output_path, ".github/instructions/my-agent.instructions.md")


class TestExtractSpecPrinciples(unittest.TestCase):
    """Test extract_spec_principles() — code-fence handling (no broken blocks)."""

    def _write_temp(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()
        path = Path(tmp.name)
        self.addCleanup(path.unlink)
        return path

    def test_code_fence_does_not_leak_unclosed_block(self):
        """A lone/odd code fence must not produce an unbalanced block in output.

        Without filtering, a trailing ``` would leak an unclosed code block into
        copilot-instructions.md and break the following skill table.
        """
        content = (
            "---\nname: spec-principles\nuser-invocable: false\n---\n\n"
            "# 原則（PR1–PR10）\n\n"
            "- **PR1 もので分ける** — 説明。\n"
            "- **PR2 2軸** — コード例：\n"
            "  ```python\n  def foo():\n      pass\n  ```\n"
            "- **PR3 系外** — 説明。\n"
            "- **PR10 認識合わせ先行** — 説明。\n\n"
            "```\n"  # lone trailing fence
        )
        path = self._write_temp(content)
        out = extract_spec_principles(path)
        # No code fences should leak — balanced (zero) means the table won't break.
        self.assertEqual(out.count("```"), 0)
        self.assertIn("PR1", out)
        self.assertIn("PR10", out)

    def test_missing_file_returns_empty(self):
        """Return empty string if principles file does not exist."""
        self.assertEqual(extract_spec_principles(Path("/nonexistent/SKILL.md")), "")


class TestScanAssets(unittest.TestCase):
    """Test scan_assets() directory traversal and glob patterns."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.claude_dir = Path(self._tmp.name) / ".claude"
        # skills/align/SKILL.md
        skill_dir = self.claude_dir / "skills" / "align"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: align\n---\nBody", encoding="utf-8")
        # agents/spec-inspector.md
        agents_dir = self.claude_dir / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "spec-inspector.md").write_text("---\nname: spec-inspector\n---\nBody", encoding="utf-8")
        # standards/old-skill/SKILL.md
        std_dir = self.claude_dir / "standards" / "old-skill"
        std_dir.mkdir(parents=True)
        (std_dir / "SKILL.md").write_text("---\nname: old-skill\n---\nBody", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_skills(self):
        assets = scan_assets(self.claude_dir)
        self.assertEqual(len(assets["skills"]), 1)
        self.assertEqual(assets["skills"][0].name, "SKILL.md")
        self.assertIn("align", str(assets["skills"][0]))

    def test_finds_agents(self):
        assets = scan_assets(self.claude_dir)
        self.assertEqual(len(assets["agents"]), 1)
        self.assertIn("spec-inspector.md", str(assets["agents"][0]))

    def test_finds_standards(self):
        assets = scan_assets(self.claude_dir)
        self.assertEqual(len(assets["standards"]), 1)
        self.assertIn("old-skill", str(assets["standards"][0]))

    def test_missing_subdirs_return_empty_lists(self):
        empty_claude = Path(self._tmp.name) / "empty_claude"
        empty_claude.mkdir()
        assets = scan_assets(empty_claude)
        self.assertEqual(assets["skills"], [])
        self.assertEqual(assets["agents"], [])
        self.assertEqual(assets["standards"], [])


class TestGenerateCopilotInstructions(unittest.TestCase):
    """Test generate_copilot_instructions() orchestrator exclusion and table escaping."""

    def _make_claude_dir(self, skills: list[tuple[str, str, bool]]) -> Path:
        """Create a temp .claude dir with given skills: [(name, description, is_orchestrator)]."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmp)
        claude_dir = Path(tmp) / ".claude"
        for name, description, is_orchestrator in skills:
            skill_dir = claude_dir / "skills" / name
            skill_dir.mkdir(parents=True)
            extra = "disable-model-invocation: true\n" if is_orchestrator else ""
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {description}\n{extra}---\nBody",
                encoding="utf-8",
            )
        return claude_dir

    def test_orchestrator_excluded_from_skill_table(self):
        """Skills with disable-model-invocation: true must not appear in the table."""
        claude_dir = self._make_claude_dir([
            ("align", "Alignment skill", False),
            ("asset-pipeline", "Pipeline orchestrator", True),
        ])
        assets = scan_assets(claude_dir)
        _, content = generate_copilot_instructions(assets, claude_dir)
        self.assertIn("`/align`", content)
        self.assertNotIn("`/asset-pipeline`", content)

    def test_pipe_in_description_is_escaped(self):
        """Pipe characters in description must be escaped for Markdown table validity."""
        claude_dir = self._make_claude_dir([
            ("my-skill", "Input | Output mapping", False),
        ])
        assets = scan_assets(claude_dir)
        _, content = generate_copilot_instructions(assets, claude_dir)
        self.assertIn(r"Input \| Output mapping", content)
        # Raw unescaped pipe must not appear inside a table cell
        lines_with_my_skill = [l for l in content.splitlines() if "my-skill" in l]
        self.assertTrue(any("\\|" in l for l in lines_with_my_skill))


class TestWriteOutputs(unittest.TestCase):
    """Test write_outputs() duplicate-path detection and path-traversal defence."""

    def test_duplicate_path_raises_systemexit(self):
        outputs = [
            (".github/foo.md", "content-a"),
            (".github/foo.md", "content-b"),
        ]
        with self.assertRaises(SystemExit):
            write_outputs(outputs, dry_run=True)

    def test_traversal_path_raises_systemexit(self):
        """Path that escapes .github/ (e.g. via ..) must be rejected."""
        outputs = [("../.hidden/secret.md", "bad")]
        with self.assertRaises(SystemExit):
            write_outputs(outputs, dry_run=False)

    def test_dry_run_writes_no_files(self):
        """Dry run must not create any files on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".github" / "test.md"
            outputs = [(".github/test.md", "hello")]
            # dry_run=True should NOT create the file
            import os
            orig = os.getcwd()
            os.chdir(tmp)
            try:
                write_outputs(outputs, dry_run=True)
            finally:
                os.chdir(orig)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
