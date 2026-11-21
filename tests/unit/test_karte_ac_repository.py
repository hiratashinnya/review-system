"""Origin-bound host and repository identity tests."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from karte import ac_repository
from karte.errors import KarteUsageError


class RepositoryBindingTest(unittest.TestCase):
    def test_public_and_enterprise_origin_urls(self):
        urls = (
            ("https://github.com/Owner/Repo.git", "github.com"),
            ("git@github.com:Owner/Repo.git", "github.com"),
            ("ssh://git@github.com/Owner/Repo", "github.com"),
            ("https://github.com/Owner/Repo/", "github.com"),
            ("https://git.corp.example/Owner/Repo.git", "git.corp.example"),
            ("git@git.corp.example:Owner/Repo", "git.corp.example"),
            ("ssh://git@git.corp.example/Owner/Repo", "git.corp.example"),
        )
        for url, host in urls:
            with self.subTest(url=url), patch.object(
                ac_repository.subprocess, "run",
                return_value=SimpleNamespace(returncode=0, stdout=url),
            ):
                self.assertEqual({"host": host, "repository": "owner/repo"},
                                 ac_repository.checkout_origin("/tmp"))

    def test_missing_and_malformed_origins_are_rejected(self):
        urls = ("file:///tmp/repo.git", "/tmp/repo.git",
                "https://github.com/owner/repo/other", "https://git.corp.example/owner/repo?bad=1",
                "https://user:password@github.com/owner/repo", "https://evil..example/owner/repo",
                "ssh://baduser@git.corp.example/Owner/Repo")
        for url in urls:
            with self.subTest(url=url), patch.object(
                ac_repository.subprocess, "run",
                return_value=SimpleNamespace(returncode=0, stdout=url),
            ):
                self.assertIsNone(ac_repository.checkout_origin("/tmp"))
        with patch.object(ac_repository.subprocess, "run",
                          return_value=SimpleNamespace(returncode=128, stdout="")):
            self.assertIsNone(ac_repository.checkout_origin("/tmp"))

    def test_binding_rejects_host_or_repo_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tmp").mkdir()
            snapshot = root / "tmp" / "snapshot.md"
            snapshot.write_text("issue", encoding="utf-8")
            origin = {"host": "github.com", "repository": "owner/repo"}
            ac_repository.bind(root, snapshot, origin)
            with patch.object(ac_repository, "checkout_origin", return_value=origin):
                self.assertEqual(origin, ac_repository.frozen(root, snapshot, required=True))
            for other in ({"host": "git.corp.example", "repository": "owner/repo"},
                          {"host": "github.com", "repository": "other/repo"}):
                with self.subTest(other=other), patch.object(
                    ac_repository, "checkout_origin", return_value=other
                ), self.assertRaises(KarteUsageError):
                    ac_repository.frozen(root, snapshot, required=True)
                with self.assertRaises(KarteUsageError):
                    ac_repository.bind(root, snapshot, other)


if __name__ == "__main__":
    unittest.main()
