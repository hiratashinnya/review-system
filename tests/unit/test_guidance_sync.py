"""Issue #406: PF 常駐 guidance の生成・staged/CI 同期契約。"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from guidance_sync import COMMON_SOURCE, TARGETS, check, render, rendered_bytes, staged_check

REPO_ROOT = Path(__file__).resolve().parents[2]


class GuidanceSyncContractTests(unittest.TestCase):
    maxDiff = None

    def test_tracked_generated_files_match_sources(self):
        self.assertEqual(check(REPO_ROOT), [])

    def test_both_generated_files_share_the_common_source_hash_marker(self):
        expected = hashlib.sha256((REPO_ROOT / COMMON_SOURCE).read_bytes()).hexdigest()
        marker = f"<!-- common-source: {COMMON_SOURCE}; sha256: {expected} -->"
        for target in TARGETS:
            with self.subTest(target=target):
                self.assertIn(marker, (REPO_ROOT / target).read_text(encoding="utf-8"))

    def test_each_generated_file_declares_its_platform_source_hash(self):
        for target, source in TARGETS.items():
            with self.subTest(target=target):
                expected = hashlib.sha256((REPO_ROOT / source).read_bytes()).hexdigest()
                marker = f"<!-- platform-source: {source}; sha256: {expected} -->"
                self.assertIn(marker, (REPO_ROOT / target).read_text(encoding="utf-8"))

    def test_claude_is_imported_and_not_a_generated_target(self):
        self.assertNotIn("CLAUDE.md", TARGETS)
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(f"@{COMMON_SOURCE}", claude)
        self.assertNotIn("generated-by: python3 -m guidance_sync", claude)

    def test_hook_installation_and_staged_only_behavior_are_documented(self):
        hook = REPO_ROOT / ".githooks" / "pre-commit"
        body = hook.read_text(encoding="utf-8")
        self.assertTrue(body.startswith("#!/bin/sh\n"))
        self.assertIn("python3 -m guidance_sync staged-check", body)
        self.assertNotIn("guidance_sync render", body)
        self.assertNotIn("git add", body)
        readme = (REPO_ROOT / ".githooks/README.md").read_text(encoding="utf-8")
        self.assertIn("chmod +x .githooks/pre-commit", readme)
        self.assertIn("git config core.hooksPath .githooks", readme)

    def test_ci_runs_the_same_full_consistency_check(self):
        workflow = (REPO_ROOT / ".github/workflows/guidance-sync.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 -m guidance_sync check", workflow)
        self.assertIn('".ai/guidance/**"', workflow)
        self.assertIn('"AGENTS.md"', workflow)
        self.assertIn('".github/copilot-instructions.md"', workflow)


class RenderAndCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for relative in [COMMON_SOURCE, *TARGETS.values()]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"source:{relative}\n", encoding="utf-8")

    def test_render_then_check(self):
        self.assertEqual(sorted(render(self.root)), sorted(TARGETS))
        self.assertEqual(check(self.root), [])
        self.assertEqual(render(self.root), [])

    def test_check_detects_stale_generated_output(self):
        render(self.root)
        (self.root / COMMON_SOURCE).write_text("changed\n", encoding="utf-8")
        errors = check(self.root)
        self.assertEqual(len(errors), len(TARGETS))

    def test_rendered_bytes_has_exact_source_hashes(self):
        load = lambda relative: (self.root / relative).read_bytes()
        for target, source in TARGETS.items():
            output = rendered_bytes(target, load=load).decode("utf-8")
            common_hash = hashlib.sha256(load(COMMON_SOURCE)).hexdigest()
            platform_hash = hashlib.sha256(load(source)).hexdigest()
            self.assertIn(f"sha256: {common_hash}", output)
            self.assertIn(f"sha256: {platform_hash}", output)


@unittest.skipUnless(subprocess.run(["git", "--version"], capture_output=True).returncode == 0, "git required")
class StagedIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "test")
        self.git("config", "user.email", "test@example.com")
        for relative in [COMMON_SOURCE, *TARGETS.values()]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"source:{relative}\n", encoding="utf-8")
        render(self.root)
        self.git("add", "--", COMMON_SOURCE, *TARGETS.values(), *TARGETS.keys())
        self.git("commit", "-qm", "initial")

    def git(self, *args):
        completed = subprocess.run(
            ["git", *args], cwd=self.root, text=True, capture_output=True, check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed

    def test_common_source_without_generated_files_fails_close(self):
        (self.root / COMMON_SOURCE).write_text("changed\n", encoding="utf-8")
        self.git("add", "--", COMMON_SOURCE)
        errors = staged_check(self.root)
        self.assertEqual(len(errors), len(TARGETS))
        self.assertTrue(all("stage されていません" in error for error in errors))

    def test_common_source_and_both_rendered_files_pass(self):
        (self.root / COMMON_SOURCE).write_text("changed\n", encoding="utf-8")
        render(self.root)
        self.git("add", "--", COMMON_SOURCE, *TARGETS.keys())
        self.assertEqual(staged_check(self.root), [])

    def test_only_one_generated_file_is_staged_fails(self):
        (self.root / COMMON_SOURCE).write_text("changed\n", encoding="utf-8")
        render(self.root)
        first = next(iter(TARGETS))
        self.git("add", "--", COMMON_SOURCE, first)
        errors = staged_check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("stage されていません", errors[0])

    def test_check_reads_index_not_later_working_tree_edits(self):
        (self.root / COMMON_SOURCE).write_text("staged\n", encoding="utf-8")
        render(self.root)
        self.git("add", "--", COMMON_SOURCE, *TARGETS.keys())
        (self.root / COMMON_SOURCE).write_text("unstaged-later\n", encoding="utf-8")
        self.assertEqual(staged_check(self.root), [])

    def test_platform_source_requires_only_its_own_output(self):
        target, source = next(iter(TARGETS.items()))
        (self.root / source).write_text("platform-changed\n", encoding="utf-8")
        render(self.root)
        self.git("add", "--", source, target)
        self.assertEqual(staged_check(self.root), [])

    def test_staged_output_must_match_staged_sources(self):
        target = next(iter(TARGETS))
        (self.root / target).write_text("tampered\n", encoding="utf-8")
        self.git("add", "--", target)
        errors = staged_check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("一致しません", errors[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
