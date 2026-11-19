"""Origin-bound Issue review repository identification tests."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from karte import ac_repository
from karte.errors import KarteUsageError


class RepositoryBindingTest(unittest.TestCase):
    def test_supported_github_origin_urls(self):
        urls = ("https://github.com/Owner/Repo.git", "git@github.com:Owner/Repo.git",
                "ssh://git@github.com/Owner/Repo", "https://github.com/Owner/Repo/")
        for url in urls:
            with self.subTest(url=url), patch.object(
                ac_repository.subprocess, "run",
                return_value=SimpleNamespace(returncode=0, stdout=url),
            ):
                self.assertEqual("owner/repo", ac_repository.checkout_repo("/tmp"))

    def test_untrusted_or_missing_origin_never_binds(self):
        for url in ("https://evil.example/owner/repo", "/tmp/repo.git",
                    "https://github.com/owner/repo/other", "git@evil:owner/repo"):
            with self.subTest(url=url), patch.object(
                ac_repository.subprocess, "run",
                return_value=SimpleNamespace(returncode=0, stdout=url),
            ):
                self.assertIsNone(ac_repository.checkout_repo("/tmp"))
        with patch.object(ac_repository.subprocess, "run",
                          return_value=SimpleNamespace(returncode=128, stdout="")):
            self.assertIsNone(ac_repository.checkout_repo("/tmp"))

    def test_binding_is_immutable_and_current_checkout_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tmp").mkdir()
            snapshot = root / "tmp" / "snapshot.md"
            snapshot.write_text("issue", encoding="utf-8")
            ac_repository.bind(root, snapshot, "Owner/Repo")
            with patch.object(ac_repository, "checkout_repo", return_value="owner/repo"):
                self.assertEqual("owner/repo", ac_repository.frozen(root, snapshot, required=True))
            with patch.object(ac_repository, "checkout_repo", return_value="other/repo"):
                with self.assertRaises(KarteUsageError):
                    ac_repository.frozen(root, snapshot, required=True)
            with self.assertRaises(KarteUsageError):
                ac_repository.bind(root, snapshot, "other/repo")
