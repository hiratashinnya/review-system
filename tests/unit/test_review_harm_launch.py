"""Verify criteria reach the actual child stdin and refusal precedes launch."""
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codex_worktree_exec import cli
from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.request import ExecRequest
from tests.unit.codex_worktree_exec_support import clean_environ, make_fake_codex

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('.ai/skills/review-harm/SKILL.md')
TARGET = Path('.claude/skills/review-harm/SKILL.md')


class HarmLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.worktree = self.root / 'linked'
        self.worktree.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.worktree)], check=True)
        self.codex = make_fake_codex(self.root)
        self.log = self.root / 'call'

    def commit_source(self):
        subprocess.run(['git', '-C', str(self.worktree), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.worktree), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'criteria'], check=True)

    def launch(self, role):
        request = ExecRequest(role=role, worktree=self.worktree, prompt_file=Path('p'),
                              output_file=Path('o'), model='gpt-6-sol',
                              reasoning_effort='high', timeout_seconds=10)
        replacements = {'parse_request': request, 'bind_worktree': self.worktree,
                        'codex_home': self.root, 'read_prompt': '本文\n',
                        'resolve_output_target': self.worktree / 'o'}
        with ExitStack() as stack:
            for name, value in replacements.items():
                stack.enter_context(patch.object(cli, name, return_value=value))
            for name in ('refuse_nested_launch', 'verify_profile_pinned',
                         'verify_project_trusted', 'verify_artifact_binding'):
                stack.enter_context(patch.object(cli, name))
            stack.enter_context(patch.object(cli, 'capture_target', return_value=(375, 0, 1)))
            stack.enter_context(patch.object(cli, 'review_envelope_of', return_value={}))
            stack.enter_context(patch.object(cli, 'ingest_codex_output', return_value='ingested'))
            return cli._launch([], clean_environ(), self.worktree, str(self.codex))

    def test_reviewers_receive_worktree_source_in_stdin_with_profile_unchanged(self):
        source = self.worktree / SOURCE
        source.parent.mkdir(parents=True)
        shutil.copy2(ROOT / SOURCE, source)
        target = self.worktree / TARGET
        target.parent.mkdir(parents=True)
        shutil.copy2(ROOT / TARGET, target)
        self.commit_source()
        for role in ('pr-reviewer', 'plan-reviewer'):
            with self.subTest(role=role):
                self.assertEqual(self.launch(role), 0)
                stdin = Path(f'{self.log}.stdin').read_text(encoding='utf-8')
                self.assertIn(source.read_text(encoding='utf-8'), stdin)
                self.assertTrue(stdin.endswith('本文\n'))
                argv = Path(f'{self.log}.argv').read_text(encoding='utf-8').splitlines()
                self.assertEqual(argv[:3], ['exec', '-C', str(self.worktree)])
                self.assertIn(f'default_permissions="{role}"', argv)

    def test_truncated_source_is_rejected_even_if_preload_was_regenerated(self):
        from review_harm_sync import render
        source = self.worktree / SOURCE
        source.parent.mkdir(parents=True)
        source.write_text(
            '---\nname: review-harm\n---\n# レビュー finding の実害判定\n'
            'harm_detail scope: out finding-triager real none\n', encoding='utf-8')
        render(self.worktree)
        with self.assertRaises(CodexExecError):
            self.launch('pr-reviewer')
        self.assertFalse(Path(f'{self.log}.argv').exists())

    def test_semantic_removal_rejected_even_with_regenerated_preload(self):
        from review_harm_sync import render
        source = self.worktree / SOURCE
        source.parent.mkdir(parents=True)
        shutil.copy2(ROOT / SOURCE, source)
        render(self.worktree)
        self.commit_source()
        import re
        text = source.read_text(encoding='utf-8')
        source.write_text(re.sub(r'(?m)^([1-4])\. .+$', r'\1. 無関係な文章。', text), encoding='utf-8')
        render(self.worktree)
        with self.assertRaises(CodexExecError):
            self.launch('pr-reviewer')
        self.assertFalse(Path(f'{self.log}.argv').exists())

    def test_invalid_or_missing_source_cannot_start_subprocess(self):
        source = self.worktree / SOURCE
        source.parent.mkdir(parents=True)
        target = self.worktree / TARGET
        target.parent.mkdir(parents=True)
        shutil.copy2(ROOT / TARGET, target)
        for payload in (None, b'', b'\xff', b'fake',
                        b'name: review-harm\n# \xe3\x83\xac\xe3\x83\x93\xe3\x83\xa5\xe3\x83\xbc finding \xe3\x81\xae\xe5\xae\x9f\xe5\xae\xb3\xe5\x88\xa4\xe5\xae\x9a\nharm_detail scope: out finding-triager real none'):
            with self.subTest(payload=payload):
                if payload is not None:
                    source.write_bytes(payload)
                with self.assertRaises(CodexExecError):
                    self.launch('pr-reviewer')
                self.assertFalse(Path(f'{self.log}.argv').exists())
                source.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
