"""画像回収が他会話/旧成果/symlinkへ逃げないことを検査する。"""

import unittest

from agy_delegate.artifacts import collect_images, image_snapshot
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_existing_conversation_not_new_run_artifact(self):
        directory = self.fake.brain / "old"
        directory.mkdir()
        (directory / "old.jpg").write_bytes(b"old")
        before = image_snapshot(self.fake.brain, None)
        with self.assertRaisesRegex(ValueError, "baseline"):
            collect_images(self.fake.brain, "old", before, self.fake.workspace / "out")

    def test_changed_bytes_only_and_collision_avoided(self):
        directory = self.fake.brain / "conv"
        directory.mkdir()
        (directory / "old.jpg").write_bytes(b"old")
        before = image_snapshot(self.fake.brain, "conv")
        (directory / "new.jpg").write_bytes(b"new")
        copied = collect_images(self.fake.brain, "conv", before, self.fake.workspace / "out")
        self.assertEqual(len(copied), 1)
        self.assertTrue(copied[0].endswith("new.jpg"))
        with self.assertRaises(FileExistsError):
            collect_images(self.fake.brain, "conv", before, self.fake.workspace / "out")

    def test_directory_and_file_symlinks_rejected(self):
        outside = self.fake.workspace / "outside"
        outside.mkdir()
        (outside / "secret.jpg").write_bytes(b"private")
        (self.fake.brain / "conv").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "escape"):
            collect_images(self.fake.brain, "conv", {}, self.fake.workspace / "out")
        target = self.fake.brain / "safe"
        target.mkdir()
        (target / "secret.jpg").symlink_to(outside / "secret.jpg")
        with self.assertRaisesRegex(ValueError, "symlink"):
            collect_images(self.fake.brain, "safe", {}, self.fake.workspace / "out")

    def test_other_conversation_is_not_fallback(self):
        (self.fake.brain / "other").mkdir()
        (self.fake.brain / "other" / "new.jpg").write_bytes(b"new")
        with self.assertRaisesRegex(ValueError, "missing"):
            collect_images(self.fake.brain, "missing", {}, self.fake.workspace / "out")


if __name__ == "__main__":
    unittest.main()
