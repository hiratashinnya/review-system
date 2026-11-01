"""descriptor境界と、runtime検査後にshimを再選択しない起動identity。"""

import hashlib
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from agy_delegate.cohort_executable import executable_sha256
from agy_delegate.launch_identity import canonical_launch_request
from agy_delegate.settings_file_read import read_settings_bytes, validate_settings_path
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class LocalReadTests(unittest.TestCase):
    def test_bounded_regular_settings_and_executable_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_bytes(b"synthetic")
            self.assertIsNone(validate_settings_path(path))
            self.assertEqual(read_settings_bytes(path), b"synthetic")
            self.assertEqual(executable_sha256(path), hashlib.sha256(b"synthetic").hexdigest())
            path.write_bytes(b"x" * 1048577)
            with self.assertRaises(ValueError):
                read_settings_bytes(path)

    def test_symlink_nonregular_and_oversize_do_not_block_or_follow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_bytes(b"synthetic")
            alias = root / "alias"
            alias.symlink_to(target)
            with self.assertRaises(ValueError):
                read_settings_bytes(alias)
            with self.assertRaises(OSError):
                executable_sha256(alias)
            fifo = root / "fifo"
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                read_settings_bytes(fifo)
            with target.open("wb") as stream:
                stream.truncate(268435457)
            with self.assertRaises(ValueError):
                executable_sha256(target)

    def test_only_known_leaf_shim_is_canonicalized_before_runtime(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        home = fake.workspace / "home"
        shim = home / ".local/bin/agy"
        shim.parent.mkdir(parents=True)
        shim.symlink_to(fake.executable)
        with patch("pathlib.Path.home", return_value=home):
            accepted = canonical_launch_request(replace(fake.request(), executable=shim))
        self.assertEqual(accepted.executable, fake.executable.resolve())
        wrong = shim.with_name("other")
        wrong.symlink_to(fake.executable)
        with self.assertRaises(ValueError):
            canonical_launch_request(replace(fake.request(), executable=wrong))
        shim.unlink()
        shim.symlink_to(fake.workspace, target_is_directory=True)
        with patch("pathlib.Path.home", return_value=home), self.assertRaises(ValueError):
            canonical_launch_request(replace(fake.request(), executable=shim / fake.executable.name))
