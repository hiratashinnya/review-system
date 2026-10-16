"""版管理された permission profile と execpolicy の静的検査（実起動の代替ではない）。"""

from pathlib import Path
import tomllib
import unittest

from codex_worktree_exec.roles import CODEX_EXEC_ROLES, WRITE_ROLES
from tests.unit.test_codex_native_merge_permissions import codex_denies, codex_forbidden_prefixes

ROOT = Path(__file__).resolve().parents[2]
CREDENTIAL_PATHS = ("~/.codex/auth.json", "~/.config/gh", "~/.claude/.credentials.json", "~/.ssh")


def permission_profiles():
    tables = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
    return tables.get("permissions", {})


class PermissionProfileTests(unittest.TestCase):
    def test_default_permissions_is_the_first_setting_and_selects_workspace(self):
        text = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        first_setting = next(line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#"))
        self.assertEqual(tomllib.loads(text)["default_permissions"], ":workspace")
        self.assertEqual(tomllib.loads(first_setting), {"default_permissions": ":workspace"})

    def test_every_codex_exec_role_has_a_profile(self):
        profiles = permission_profiles()
        for role in sorted(CODEX_EXEC_ROLES):
            with self.subTest(role=role):
                self.assertIn(role, profiles)
        self.assertIn("pr-reviewer", profiles)

    def test_role_profiles_are_identical(self):
        profiles = permission_profiles()
        bodies = [profiles[role] for role in sorted(WRITE_ROLES)]
        self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_profiles_keep_workspace_limits_disable_network_and_deny_credentials(self):
        profiles = permission_profiles()
        for role in sorted(CODEX_EXEC_ROLES):
            profile = profiles[role]
            with self.subTest(role=role):
                self.assertEqual(profile["extends"], ":workspace" if role in WRITE_ROLES else ":read-only")
                self.assertEqual(profile["network"], {
                    "enabled": False,
                    "allow_local_binding": False,
                    "dangerously_allow_all_unix_sockets": False,
                    "dangerously_allow_non_loopback_proxy": False,
                })
                for path in CREDENTIAL_PATHS:
                    self.assertEqual(profile["filesystem"].get(path), "deny", path)
                self.assertTrue(all(value == "deny" for value in profile["filesystem"].values()))


class ExecpolicyTests(unittest.TestCase):
    def test_codex_cannot_relaunch_the_wrapper(self):
        prefixes = codex_forbidden_prefixes()
        for command in (
            "python3 -m codex_worktree_exec --role issue-implementer -C .",
            "python -m codex_worktree_exec --role issue-fixer -C .",
        ):
            with self.subTest(command=command):
                self.assertTrue(codex_denies(command, prefixes))


if __name__ == "__main__":
    unittest.main()
