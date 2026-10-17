"""UT-TC: 同repo targetは残しnested worktreeの成果物を混入させない。"""
import shutil
import tempfile
import unittest
from pathlib import Path
from issue_envelope.query import index
from issue_envelope.store import load, write
from .fixtures import artifact


class DiscoveryTests(unittest.TestCase):
    def test_nested_git_file_directory_and_symlink_are_excluded(self):
        for marker in ("file", "directory", "symlink"):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                parent = artifact(children=["VD-371-tool"])
                child = artifact(identifier="VD-371-tool", parent="VD-371")
                write(root / "verification_design/VD-371.toml", parent)
                write(root / "tool/verification_design/VD-371.toml", child)
                nested = root / ".claude/worktrees/linked"
                nested.mkdir(parents=True)
                for name in ("verification_design", "tool"):
                    shutil.copytree(root / name, nested / name)
                (nested / "tool/adr").mkdir()
                (nested / "tool/adr/invalid.toml").write_text("not an ADR")
                if marker == "file":
                    (nested / ".git").write_text("gitdir: /other/worktree")
                elif marker == "directory":
                    (nested / ".git").mkdir()
                else:
                    (nested / ".git").symlink_to(root / "missing")
                self.assertEqual(len(load(root)), 2)
                self.assertEqual(len(index(root)["nodes"]), 2)

    def test_normal_nested_target_is_not_excluded_and_symlink_cannot_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            parent = artifact(children=["VD-371-deep"])
            child = artifact(identifier="VD-371-deep", parent="VD-371")
            for node in (parent, child):
                node["scope"] = ["group/tool"]
            write(root / "verification_design/VD-371.toml", parent)
            write(root / "group/tool/verification_design/VD-371.toml", child)
            self.assertEqual(len(load(root)), 2)
            with tempfile.TemporaryDirectory() as outside:
                (root / "linked").symlink_to(outside, target_is_directory=True)
                (Path(outside) / "adr").mkdir()
                (Path(outside) / "adr/invalid.toml").write_text("outside")
                self.assertEqual(len(index(root)["nodes"]), 2)
                (root / "adr").symlink_to(Path(outside) / "adr", target_is_directory=True)
                with self.assertRaises(ValueError):
                    index(root)
