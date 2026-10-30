"""source集合・個別read・全read後の改変を固定理由で拒否する。"""

import os
import stat
from types import SimpleNamespace
from unittest.mock import patch

from agy_delegate.cohort_generator import _read_source, current_generator_sha256
from tests.unit.test_agy_delegate_cohort_generator import GeneratorFixture


class CohortGeneratorStabilityTests(GeneratorFixture):
    def test_source_set_change_after_first_read_is_rejected(self):
        def changed(fd, name):
            result = _read_source(fd, name)
            (self.package / "new.py").write_bytes(b"new source")
            return result
        with patch("agy_delegate.cohort_generator._read_source", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "cohort_generator_changed"):
                current_generator_sha256()

    def test_source_changed_after_its_read_is_detected_by_final_identity_check(self):
        def changed(fd, name):
            result = _read_source(fd, name)
            if name == "z.ps1":
                (self.package / "a.py").write_bytes(b"same length!!")
            return result
        with patch("agy_delegate.cohort_generator._read_source", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "cohort_generator_changed"):
                current_generator_sha256()

    def test_os_read_failure_returns_only_fixed_reason(self):
        with patch("agy_delegate.cohort_generator.os.open", side_effect=OSError("private path")):
            with self.assertRaises(ValueError) as error:
                current_generator_sha256()
        self.assertEqual(str(error.exception), "cohort_generator_unavailable")

    def test_file_change_during_same_descriptor_read_is_rejected(self):
        actual_fstat = os.fstat
        count = 0
        def changed(fd):
            nonlocal count
            info = actual_fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return info
            count += 1
            if count == 2:
                names = ["st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size",
                         "st_mtime_ns", "st_ctime_ns"]
                attributes = {name: getattr(info, name) for name in names}
                attributes["st_ctime_ns"] += 1
                return SimpleNamespace(**attributes)
            return info
        with patch("agy_delegate.cohort_generator.os.fstat", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "cohort_generator_changed"):
                current_generator_sha256()

    def test_package_directory_alias_is_not_followed(self):
        alias = self.package / "alias"
        alias.symlink_to(self.package, target_is_directory=True)
        with patch("agy_delegate.cohort_generator._PACKAGE_DIRECTORY", alias):
            with self.assertRaisesRegex(ValueError, "cohort_generator_unavailable"):
                current_generator_sha256()
