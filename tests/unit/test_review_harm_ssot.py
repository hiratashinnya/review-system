"""Issue #723: shared harm criteria and actual reviewer prompt supply."""
from pathlib import Path
import tempfile
import shutil
import subprocess
import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.invocation import compose_prompt

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('.ai/skills/review-harm/SKILL.md')
CLAUDE = Path('.claude/skills/review-harm/SKILL.md')


class ReviewHarmContractTests(unittest.TestCase):
    def test_source_preserves_categories_and_decision_boundaries(self):
        text = (ROOT / SOURCE).read_text(encoding='utf-8')
        for concept in ('仕様', '退行', 'fail-close', '正本', '履歴', '契約違反',
                        '秘密', 'コスト', '誤読', '名前と実体', 'トレーサビリティ',
                        '分岐', '暗黙の前提', '観測不能', '再現性'):
            with self.subTest(concept=concept):
                self.assertIn(concept, text)
        for boundary in ('real', 'none', 'scope', 'harm_detail', '処置方針', '迷'):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)

    def test_all_consumers_reference_same_source_and_direct_dispatch_guidance(self):
        for path in ('.ai/agents/pr-reviewer.md', '.ai/agents/plan-reviewer.md',
                     '.ai/skills/issue-pipeline/SKILL.md'):
            with self.subTest(path=path):
                self.assertIn(str(SOURCE), (ROOT / path).read_text(encoding='utf-8'))
        codex = (ROOT / '.ai/guidance/platforms/codex.md').read_text(encoding='utf-8')
        for term in ('review-harm', 'pr-reviewer', 'plan-reviewer', '全文', 'STOP'):
            self.assertIn(term, codex)
        pipeline = (ROOT / '.ai/skills/issue-pipeline/SKILL.md').read_text(encoding='utf-8')
        self.assertRegex(pipeline, r'(?m)^.*finding-triager.*#691.*review-harm/SKILL\.md.*全文.*供給.*$')

    def test_claude_direct_reviewers_preload_full_generated_criteria(self):
        source = (ROOT / SOURCE).read_text(encoding='utf-8')
        generated = (ROOT / CLAUDE).read_text(encoding='utf-8')
        # Ignore source frontmatter; the complete normative body must be preloaded.
        body = source.split('---', 2)[-1].strip()
        self.assertIn(body, generated)
        for role in ('pr-reviewer', 'plan-reviewer'):
            wrapper = (ROOT / f'.claude/agents/{role}.md').read_text(encoding='utf-8')
            frontmatter = wrapper.split('---', 2)[1]
            import re
            self.assertRegex(frontmatter, r'(?m)^skills:\s*(?:\[\s*review-harm\s*\]|\n\s+-\s+review-harm\s*$)')

    def test_codex_review_prompt_carries_entire_source_and_original_request(self):
        source = (ROOT / SOURCE).read_text(encoding='utf-8')
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        for path in (SOURCE, CLAUDE):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, root / path)
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c',
                        'user.email=test@example.invalid', 'commit', '-qm', 'criteria'], check=True)
        for role in ('pr-reviewer', 'plan-reviewer'):
            with self.subTest(role=role):
                prompt = compose_prompt(role, root, '依頼本文\n末尾')
                self.assertIn(source, prompt)
                self.assertEqual(prompt.count(source), 1)
                self.assertTrue(prompt.endswith('依頼本文\n末尾'))
        self.assertNotIn(source, compose_prompt('issue-fixer', ROOT, '依頼本文'))

    def test_missing_or_invalid_source_stops_before_a_prompt_is_produced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for content in (None, b'', b'\xff', b'not a valid criteria document'):
                path = root / SOURCE
                path.parent.mkdir(parents=True, exist_ok=True)
                if content is not None:
                    path.write_bytes(content)
                with self.subTest(content=content), self.assertRaises(CodexExecError):
                    compose_prompt('pr-reviewer', root, '依頼')
                path.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
