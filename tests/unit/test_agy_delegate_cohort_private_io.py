"""同UID・nlink・同じfile descriptor内でのfingerprint変化を検査する。"""

import os
import stat
from types import SimpleNamespace
from unittest.mock import patch

from agy_delegate.cohort_storage import read_cohort
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW


class CohortPrivateIOTests(CohortStoreFixture):
    def test_foreign_file_owner_is_rejected_without_child_or_detail_leak(self):
        real_fstat = os.fstat
        def foreign(fd):
            info = real_fstat(fd)
            if stat.S_ISREG(info.st_mode):
                return SimpleNamespace(st_uid=info.st_uid + 1, st_mode=info.st_mode,
                                       st_nlink=info.st_nlink, st_size=info.st_size)
            return info
        with patch("agy_delegate.cohort_private_io.os.fstat", side_effect=foreign), patch(
            "subprocess.run"
        ) as child:
            with self.assertRaisesRegex(ValueError, "cohort_file_owner_or_mode_invalid"):
                read_cohort(self.workspace, now=NOW)
        child.assert_not_called()

    def test_file_stat_change_on_same_descriptor_is_rejected(self):
        real_fstat = os.fstat
        calls = 0
        def changed(fd):
            nonlocal calls
            info = real_fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return info
            calls += 1
            if calls == 2:
                fields = {key: getattr(info, key) for key in ["st_dev", "st_ino", "st_uid",
                          "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"]}
                fields["st_mtime_ns"] += 1
                return SimpleNamespace(**fields)
            return info
        with patch("agy_delegate.cohort_private_io.os.fstat", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "cohort_file_changed"):
                read_cohort(self.workspace, now=NOW)

    def test_dangling_symlink_marker_blocks_even_with_valid_old_index(self):
        (self.store / f"{self.wid}.publishing").symlink_to(self.home / "missing")
        with self.assertRaisesRegex(ValueError, "cohort_publication_pending"):
            read_cohort(self.workspace, now=NOW)
