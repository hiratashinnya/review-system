"""標準py_compileの無害な生成物と承認sourceの読取validationだけを検査する。"""
import py_compile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.compiled_cache import verify_compiled_cache
from issue_envelope.path_binding import committed_bytes
from codex_worktree_exec.source_snapshot import verify_source_snapshot, verify_untracked_sources
from tests.unit.codex_worktree_exec_support import git, make_repository


class CompiledCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        _, self.root = make_repository(Path(temporary.name))
        self.source = self.root / "ordinary.py"
        self.source.write_text('"""ordinary module"""\nconstant = 1\nassert constant == 1\n')
        git(self.root, "add", "ordinary.py")
        git(self.root, "commit", "-qm", "ordinary source")
        self.oid = git(self.root, "rev-parse", "HEAD")

    def test_standard_current_compiler_outputs_allow_normal_snapshot_validation(self):
        for level in range(3):
            for filename in (str(self.source), "ordinary.py", "./ordinary.py"):
                with self.subTest(level=level, filename=filename):
                    cache = Path(py_compile.compile(str(self.source), dfile=filename,
                                                    doraise=True, optimize=level))
                    before = cache.read_bytes()
                    verify_compiled_cache(cache, self.root)
                    verify_source_snapshot(self.root, self.oid, 371)
                    self.assertEqual(cache.read_bytes(), before)

    def test_standard_timestamp_and_hash_headers_preserve_normal_validation(self):
        for mode in py_compile.PycInvalidationMode:
            with self.subTest(mode=mode):
                cache = Path(py_compile.compile(str(self.source), doraise=True,
                                                invalidation_mode=mode))
                verify_compiled_cache(cache, self.root)

    def test_source_must_still_match_head_before_cache_validation(self):
        cache = Path(py_compile.compile(str(self.source), doraise=True))
        self.source.write_text("constant = 2\n")
        with self.assertRaisesRegex(ValueError, "HEAD"):
            verify_compiled_cache(cache, self.root)

    def test_previous_standard_cache_is_not_approval_for_a_new_source_version(self):
        cache = Path(py_compile.compile(str(self.source), doraise=True))
        self.source.write_text("constant = 2\n")
        git(self.root, "add", "ordinary.py")
        git(self.root, "commit", "-qm", "updated ordinary source")
        with self.assertRaisesRegex(ValueError, "does not match committed source"):
            verify_compiled_cache(cache, self.root)
        current = Path(py_compile.compile(str(self.source), doraise=True))
        verify_compiled_cache(current, self.root)

    def test_missing_or_directory_source_is_not_accepted(self):
        cache = Path(py_compile.compile(str(self.source), doraise=True))
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, "source is not a regular"):
            verify_compiled_cache(cache, self.root)
        self.source.mkdir()
        with self.assertRaisesRegex(ValueError, "source is not a regular"):
            verify_compiled_cache(cache, self.root)

    def test_unsupported_tag_and_truncated_normal_file_are_not_accepted(self):
        cache = Path(py_compile.compile(str(self.source), doraise=True))
        other = cache.parent / "ordinary.unsupported.pyc"
        other.write_bytes(cache.read_bytes())
        with self.assertRaisesRegex(ValueError, "tag/optimization"):
            verify_compiled_cache(other, self.root)
        cache.write_bytes(cache.read_bytes()[:8])
        with self.assertRaisesRegex(ValueError, "header is not supported"):
            verify_compiled_cache(cache, self.root)

    def test_one_committed_source_check_per_source_and_no_process_global_cache(self):
        for level in range(3):
            py_compile.compile(str(self.source), doraise=True, optimize=level)
        with patch("codex_worktree_exec.compiled_cache.committed_bytes",
                   wraps=committed_bytes) as read:
            verify_untracked_sources(self.root)
            self.assertEqual(read.call_count, 1)
            verify_untracked_sources(self.root)
            self.assertEqual(read.call_count, 2)
