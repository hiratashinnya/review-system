"""固定package source集合のcanonical hashと非source除外を偽fixtureで確認。"""

import hashlib
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agy_delegate.cohort_generator import current_generator_sha256


class GeneratorFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.package = Path(self.temporary.name)
        self.sources = {"a.py": b"python source", "z.ps1": b"powershell source"}
        for name, content in self.sources.items():
            (self.package / name).write_bytes(content)
        patcher = patch("agy_delegate.cohort_generator._PACKAGE_DIRECTORY", self.package)
        patcher.start()
        self.addCleanup(patcher.stop)


class CohortGeneratorTests(GeneratorFixture):
    def test_sorted_name_to_hash_canonical_object_and_no_children(self):
        hashes = {name: hashlib.sha256(content).hexdigest() for name, content in self.sources.items()}
        expected = hashlib.sha256(json.dumps(hashes, sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
        with patch("subprocess.run") as child:
            self.assertEqual(current_generator_sha256(), expected)
        child.assert_not_called()
        self.assertEqual(str(inspect.signature(current_generator_sha256)), "() -> str")

    def test_non_source_nested_source_and_environment_manifest_are_ignored(self):
        expected = current_generator_sha256()
        (self.package / "private.json").write_bytes(b"secret: must not be read")
        (self.package / "nested").mkdir()
        (self.package / "nested/source.py").write_bytes(b"not top level")
        with patch.dict(os.environ, {"HOME": "/untrusted", "XDG_STATE_HOME": "/untrusted",
                                    "AGY_GENERATOR_MANIFEST": "/untrusted"}):
            self.assertEqual(current_generator_sha256(), expected)

    def test_filename_and_both_source_types_are_bound(self):
        original = current_generator_sha256()
        (self.package / "a.py").rename(self.package / "renamed.py")
        self.assertNotEqual(current_generator_sha256(), original)
        previous = current_generator_sha256()
        (self.package / "z.ps1").write_bytes(b"changed helper")
        self.assertNotEqual(current_generator_sha256(), previous)

    def test_exact_source_size_limit_and_empty_inventory(self):
        (self.package / "a.py").write_bytes(b"x" * (1024 * 1024))
        self.assertRegex(current_generator_sha256(), "^[0-9a-f]{64}$")
        (self.package / "a.py").write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, "cohort_generator_source_too_large"):
            current_generator_sha256()
        for path in self.package.iterdir():
            path.unlink()
        with self.assertRaisesRegex(ValueError, "cohort_generator_inventory_invalid"):
            current_generator_sha256()

    def test_symlink_directory_or_fifo_source_is_rejected(self):
        path = self.package / "a.py"
        for kind in ["link", "directory", "fifo"]:
            path.unlink()
            if kind == "link":
                path.symlink_to(self.package / "z.ps1")
            elif kind == "directory":
                path.mkdir()
            else:
                os.mkfifo(path)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                current_generator_sha256()
            path.rmdir() if kind == "directory" else path.unlink()
            path.write_bytes(b"restored")
