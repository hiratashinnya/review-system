"""実ファイル差替え時も workspace 外や特殊ファイルを読まない。"""

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agy_delegate.workspace_changes import snapshot


class WorkspaceSnapshotSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        (self.outside / "secret").write_text("outside")

    def test_file_replaced_by_symlink_before_open_is_rejected(self):
        victim = self.workspace / "victim"
        victim.write_text("inside")
        real_open = os.open

        def replace_then_open(name, flags, *args, **kwargs):
            if name == "victim":
                victim.unlink()
                victim.symlink_to(self.outside / "secret")
            return real_open(name, flags, *args, **kwargs)

        with patch("agy_delegate.workspace_changes.os.open", side_effect=replace_then_open):
            with self.assertRaisesRegex(ValueError, "^workspace_snapshot_incomplete$"):
                snapshot(self.workspace)

    def test_directory_replaced_by_symlink_before_open_is_rejected(self):
        victim = self.workspace / "victim"
        victim.mkdir()
        real_open = os.open

        def replace_then_open(name, flags, *args, **kwargs):
            if name == "victim":
                victim.rmdir()
                victim.symlink_to(self.outside, target_is_directory=True)
            return real_open(name, flags, *args, **kwargs)

        with patch("agy_delegate.workspace_changes.os.open", side_effect=replace_then_open):
            with self.assertRaisesRegex(ValueError, "^workspace_snapshot_incomplete$"):
                snapshot(self.workspace)

    def test_open_directory_remains_bound_after_path_replacement(self):
        victim = self.workspace / "victim"
        victim.mkdir()
        (victim / "inside").write_bytes(b"inside")
        real_open = os.open

        def open_then_replace(name, flags, *args, **kwargs):
            descriptor = real_open(name, flags, *args, **kwargs)
            if name == "victim":
                victim.rename(self.root / "held")
                victim.symlink_to(self.outside, target_is_directory=True)
            return descriptor

        with patch("agy_delegate.workspace_changes.os.open", side_effect=open_then_replace):
            observed = snapshot(self.workspace)
        self.assertEqual(observed, {"victim/inside": hashlib.sha256(b"inside").hexdigest()})

    def test_fifo_and_file_replaced_by_fifo_do_not_block(self):
        script = '''
import os, sys
from pathlib import Path
from unittest.mock import patch
from agy_delegate.workspace_changes import snapshot
workspace = Path(sys.argv[1])
os.mkfifo(workspace / "fifo")
assert snapshot(workspace) == {}
victim = workspace / "victim"
victim.write_text("inside")
real_open = os.open
def swap(name, flags, *args, **kwargs):
    if name == "victim":
        victim.unlink()
        os.mkfifo(victim)
    return real_open(name, flags, *args, **kwargs)
with patch("agy_delegate.workspace_changes.os.open", side_effect=swap):
    try:
        snapshot(workspace)
    except ValueError as error:
        assert str(error) == "workspace_snapshot_incomplete"
    else:
        raise AssertionError("replaced FIFO accepted")
'''
        result = subprocess.run([sys.executable, "-c", script, str(self.workspace)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
