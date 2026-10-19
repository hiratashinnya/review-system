"""trusted承認済みのTD/TC/ADR/実装bytesだけをsnapshot後に継承する。"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from codex_worktree_exec.source_snapshot import verify_source_snapshot
from tests.unit.codex_worktree_exec_support import git, make_repository


class SourceSnapshotTests(unittest.TestCase):
    def test_untracked_source_and_tc_are_rejected_but_tmp_data_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, root = make_repository(Path(temporary))
            oid = git(root, "rev-parse", "HEAD")
            (root / "tmp").mkdir()
            (root / "tmp/input.json").write_text("{}")
            (root / "tmp/result.md").write_text("result")
            (root / "tmp/_worktree").mkdir()
            (root / "tmp/_worktree/ledger.json.lock").write_text("")
            git(root, "config", "core.excludesFile", str(root / "tmp/ignore.txt"))
            (root / "tmp/ignore.txt").write_text("ignored_source.py\n")
            verify_source_snapshot(root, oid, 371)
            for name in ("source.py", "test_extra.py", "tmp/injected.py", "ignored_source.py"):
                path = root / name
                path.write_bytes(b"unapproved = True\n")
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "untracked source"):
                    verify_source_snapshot(root, oid, 371)
                with self.assertRaises(ValueError):
                    verify_source_snapshot(root, oid, 371, {name: hashlib.sha256(path.read_bytes()).hexdigest()})
                path.unlink()

    def test_each_phase_output_needs_exact_committed_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, root = make_repository(Path(temporary))
            oid = git(root, "rev-parse", "HEAD")
            changes = {}
            for name in ("tool/verify/designs/ST-TD-1.md", "tests/tool/test_red.py",
                         "tool/adr/ADR-20261016-example.toml", "tool/implementation.py"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("approved phase output\n")
                changes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            git(root, "add", ".")
            git(root, "commit", "-qm", "phase outputs")
            with self.assertRaisesRegex(ValueError, "outside canonical"):
                verify_source_snapshot(root, oid, 371)
            verify_source_snapshot(root, oid, 371, changes)
            for name in changes:
                path = root / name
                original = path.read_bytes()
                path.write_bytes(original + b"unapproved\n")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify_source_snapshot(root, oid, 371, changes)
                path.write_bytes(original)
            (root / "unrelated.py").write_text("drift\n")
            git(root, "add", ".")
            git(root, "commit", "-qm", "unapproved drift")
            with self.assertRaisesRegex(ValueError, "outside canonical"):
                verify_source_snapshot(root, oid, 371, changes)

    def test_broad_and_unsafe_approval_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, root = make_repository(Path(temporary))
            oid = git(root, "rev-parse", "HEAD")
            for name in ("../source.py", "/tmp/source.py", ".git/config", "./source.py"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify_source_snapshot(root, oid, 371, {name: "a" * 64})
