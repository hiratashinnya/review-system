"""cohort 専有treeと既存ancestorの異なるmode契約を確認する。"""

import os
import stat
from types import SimpleNamespace
from unittest.mock import patch

from agy_delegate.cohort_paths import _check_directory, held_cohort_directory, workspace_id
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW
from agy_delegate.cohort_storage import read_cohort


class CohortPathTests(CohortStoreFixture):
    def test_existing_home_and_local_755_are_accepted_but_private_755_is_not(self):
        for directory in [self.home, self.home / ".local", self.home / ".local/state"]:
            directory.chmod(0o755)
        self.assertEqual(read_cohort(self.workspace, now=NOW), self.proof)
        for directory in [self.store, self.store.parent, self.store.parent.parent]:
            directory.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "cohort_directory_mode_invalid"):
                read_cohort(self.workspace, now=NOW)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
            directory.chmod(0o700)

    def test_other_writable_home_or_local_is_rejected_without_chmod(self):
        for directory in [self.home, self.home / ".local", self.home / ".local/state"]:
            directory.chmod(0o770)
            with self.assertRaisesRegex(ValueError, "cohort_directory_mode_invalid"):
                read_cohort(self.workspace, now=NOW)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o770)
            directory.chmod(0o700)

    def test_trusted_ancestors_require_root_owner_without_group_or_other_write(self):
        def info(uid, mode):
            return SimpleNamespace(st_uid=uid, st_mode=stat.S_IFDIR | mode)
        _check_directory(info(0, 0o755), "ancestor")
        for value in [info(1, 0o755), info(0, 0o775), info(0, 0o777)]:
            with self.assertRaises(ValueError):
                _check_directory(value, "ancestor")
        with self.assertRaises(ValueError):
            _check_directory(info(os.getuid() + 1, 0o700), "private")

    def test_symlink_ancestor_and_workspace_alias_are_rejected(self):
        local = self.home / ".local"
        moved = self.home / "actual-local"
        local.rename(moved)
        local.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError):
            read_cohort(self.workspace, now=NOW)
        alias = self.home / "workspace-alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(ValueError):
            workspace_id(alias)

    def test_home_and_xdg_environment_cannot_redirect_the_store(self):
        with patch.dict(os.environ, {"HOME": "/untrusted", "XDG_STATE_HOME": "/untrusted"}):
            self.assertEqual(read_cohort(self.workspace, now=NOW), self.proof)

    def test_create_does_not_accept_wrong_existing_mode(self):
        self.store.chmod(0o755)
        with self.assertRaises(ValueError):
            with held_cohort_directory(create=True):
                self.fail("unsafe directory accepted")
