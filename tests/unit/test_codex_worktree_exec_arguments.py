"""codex_worktree_exec の引数検査（ロール allowlist と argv の形）。"""

import unittest

from codex_worktree_exec.arguments import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    parse_request,
)
from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.roles import CODEX_EXEC_ROLES
from issue_start.gated_roles import GATED_ROLES

BASE = [
    "-C", "wt", "--prompt-file", "p.md", "--output-file", "o.md",
    "--model", "gpt-6-sol", "--reasoning-effort", "high",
]


def request_args(role="issue-implementer", *extra):
    return ["--role", role, *BASE, *extra]


class RefusalAssertions(unittest.TestCase):
    def assert_refused(self, argv, error_id):
        with self.assertRaises(CodexExecError) as caught:
            parse_request(argv)
        self.assertEqual(caught.exception.error_id, error_id)


class RoleAllowlistTests(RefusalAssertions):
    def test_roles_are_all_gated_roles(self):
        # D4: 書込ロールをリテラルで再定義せず GATED_ROLES から導出する。
        self.assertEqual(CODEX_EXEC_ROLES, GATED_ROLES)
        self.assertIn("pr-reviewer", CODEX_EXEC_ROLES)

    def test_writing_roles_are_accepted(self):
        for role in sorted(CODEX_EXEC_ROLES):
            with self.subTest(role=role):
                request = parse_request(request_args(role))
                self.assertEqual(request.role, role)
                self.assertEqual(request.timeout_seconds, DEFAULT_TIMEOUT_SECONDS)

    def test_reviewer_and_unknown_roles_are_refused(self):
        for role in ("main", "general-purpose", ""):
            with self.subTest(role=role):
                self.assert_refused(request_args(role), "CODEX_EXEC_ROLE_NOT_ALLOWED")


class ArgumentShapeTests(RefusalAssertions):
    def test_each_required_argument_is_required(self):
        full = request_args()
        for index in range(0, len(full), 2):
            argv = full[:index] + full[index + 2:]
            with self.subTest(missing=full[index]):
                self.assert_refused(argv, "CODEX_EXEC_ARGUMENT_INVALID")

    def test_repeated_option_is_refused(self):
        # 後勝ちで別ロールへ差し替わる経路を作らない。
        self.assert_refused(request_args("issue-implementer", "--role", "issue-fixer"), "CODEX_EXEC_ARGUMENT_INVALID")
        self.assert_refused(request_args("issue-fixer", "-C", "other"), "CODEX_EXEC_ARGUMENT_INVALID")

    def test_abbreviated_and_unknown_options_are_refused(self):
        argv = ["--rol", "issue-implementer", *BASE]
        self.assert_refused(argv, "CODEX_EXEC_ARGUMENT_INVALID")
        self.assert_refused(request_args("issue-implementer", "-c", "sandbox_mode=x"), "CODEX_EXEC_ARGUMENT_INVALID")
        self.assert_refused(request_args("issue-implementer", "extra"), "CODEX_EXEC_ARGUMENT_INVALID")

    def test_model_effort_and_timeout_are_checked_individually(self):
        cases = [
            (["--role", "issue-fixer", *BASE[:6], "--model", "gpt;rm", *BASE[8:]], "CODEX_EXEC_MODEL_INVALID"),
            (["--role", "issue-fixer", *BASE[:8], "--reasoning-effort", "extreme"], "CODEX_EXEC_EFFORT_INVALID"),
            (request_args("issue-fixer", "--timeout-seconds", "0"), "CODEX_EXEC_TIMEOUT_INVALID"),
            (request_args("issue-fixer", "--timeout-seconds", str(MAX_TIMEOUT_SECONDS + 1)), "CODEX_EXEC_TIMEOUT_INVALID"),
            (request_args("issue-fixer", "--timeout-seconds", "1e3"), "CODEX_EXEC_TIMEOUT_INVALID"),
        ]
        for argv, error_id in cases:
            with self.subTest(error_id=error_id, argv=argv):
                self.assert_refused(argv, error_id)

    def test_explicit_timeout_within_range_is_kept(self):
        request = parse_request(request_args("issue-fixer", "--timeout-seconds", str(MAX_TIMEOUT_SECONDS)))
        self.assertEqual(request.timeout_seconds, MAX_TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
