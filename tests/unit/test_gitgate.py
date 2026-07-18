"""gitgate（Issue #227 追加修正3・git ラッパー）の単体テスト。

検証観点:
  - 各 verb が正しい固定 git argv を組む（build_git_argv・純関数）。
  - 想定外の引数は git に渡さず GitgateError（＝git を実行しない）。injection 試行の無害化。
  - leaf 検証（パス／ブランチ名／ref／整数／grep）。
  - main() が subprocess.run を shell=False の list 渡しで呼ぶ（monkeypatch で捕捉）。
"""

import json
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from gitgate import GitgateError, build_git_argv
from gitgate import cli as gitgate_cli


class BuildGitArgvHappyPathTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(build_git_argv(["status"]), ["git", "status"])

    def test_add_paths_go_after_double_dash(self):
        self.assertEqual(
            build_git_argv(["add", "a.py", "dir/b.py"]),
            ["git", "add", "--", "a.py", "dir/b.py"],
        )

    def test_commit_uses_F_and_requires_existing_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=True) as f:
            self.assertEqual(
                build_git_argv(["commit", f.name]),
                ["git", "commit", "-F", f.name],
            )

    def test_push_is_fixed(self):
        self.assertEqual(build_git_argv(["push"]), ["git", "push", "-u", "origin", "HEAD"])

    def test_branch_current_is_fixed(self):
        self.assertEqual(build_git_argv(["branch-current"]), ["git", "branch", "--show-current"])

    def test_new_branch(self):
        self.assertEqual(
            build_git_argv(["new-branch", "issue-227-foo"]),
            ["git", "switch", "-c", "issue-227-foo"],
        )

    def test_fetch_is_fixed(self):
        self.assertEqual(build_git_argv(["fetch"]), ["git", "fetch", "--prune", "origin"])

    def test_diff_variants(self):
        self.assertEqual(build_git_argv(["diff"]), ["git", "diff"])
        self.assertEqual(build_git_argv(["diff", "--stat"]), ["git", "diff", "--stat"])
        self.assertEqual(
            build_git_argv(["diff", "main...HEAD"]), ["git", "diff", "main...HEAD"]
        )
        self.assertEqual(
            build_git_argv(["diff", "--stat", "HEAD~1", "HEAD"]),
            ["git", "diff", "--stat", "HEAD~1", "HEAD"],
        )

    def test_log_variants(self):
        self.assertEqual(build_git_argv(["log"]), ["git", "log"])
        self.assertEqual(build_git_argv(["log", "-n", "5"]), ["git", "log", "-n", "5"])
        self.assertEqual(build_git_argv(["log", "-n5"]), ["git", "log", "-n", "5"])
        self.assertEqual(build_git_argv(["log", "--oneline"]), ["git", "log", "--oneline"])
        self.assertEqual(
            build_git_argv(["log", "--grep", "fix(hooks)"]),
            ["git", "log", "--grep=fix(hooks)"],
        )
        self.assertEqual(
            build_git_argv(["log", "--grep=foo|bar", "-n", "3", "--oneline"]),
            ["git", "log", "--grep=foo|bar", "-n", "3", "--oneline"],
        )


class BuildGitArgvRejectionTests(unittest.TestCase):
    def test_unknown_verb_is_rejected(self):
        with self.assertRaises(GitgateError):
            build_git_argv(["merge", "feature"])
        with self.assertRaises(GitgateError):
            build_git_argv(["pull"])
        with self.assertRaises(GitgateError):
            build_git_argv([])

    def test_no_arg_verbs_reject_extra_args(self):
        # Critical 回帰: `push --receive-pack=x`（外部プログラム実行を狙う）は push が引数を取らないため
        # GitgateError となり、`--receive-pack=…` は git に到達しない。
        for argv in [
            ["push", "--receive-pack=sh -c evil"],
            ["push", "origin", "HEAD"],
            ["status", "--foo"],
            ["fetch", "--upload-pack=evil"],
            ["branch-current", "-a"],
        ]:
            with self.subTest(argv=argv):
                with self.assertRaises(GitgateError):
                    build_git_argv(argv)

    def test_publish_info_rejects_extra_args_without_running_git(self):
        with patch.object(gitgate_cli.subprocess, "run") as run:
            rc = gitgate_cli.main(["publish-info", "upstream"])
        self.assertEqual(rc, 2)
        run.assert_not_called()

    def test_add_neutralizes_flags_via_double_dash(self):
        # add のパスに `--receive-pack=x` を与えても `--` 以降に置かれるため pathspec として無害。
        self.assertEqual(
            build_git_argv(["add", "--receive-pack=x"]),
            ["git", "add", "--", "--receive-pack=x"],
        )
        # 引数なしの add は拒否。
        with self.assertRaises(GitgateError):
            build_git_argv(["add"])

    def test_add_rejects_newline_and_nul_paths(self):
        with self.assertRaises(GitgateError):
            build_git_argv(["add", "a\nb"])
        with self.assertRaises(GitgateError):
            build_git_argv(["add", "a\0b"])

    def test_commit_rejects_missing_file(self):
        with self.assertRaises(GitgateError):
            build_git_argv(["commit", "/nonexistent/definitely/missing.md"])
        # 引数の個数違反も拒否。
        with self.assertRaises(GitgateError):
            build_git_argv(["commit"])
        with tempfile.NamedTemporaryFile("w", delete=True) as f:
            with self.assertRaises(GitgateError):
                build_git_argv(["commit", f.name, "extra"])

    def test_new_branch_rejects_injection_and_leading_dash(self):
        for name in ["x; sh", "x && sh", "a b", "-D", "--force", "a$(x)", "a`x`", "a\nb"]:
            with self.subTest(name=name):
                with self.assertRaises(GitgateError):
                    build_git_argv(["new-branch", name])
        # 個数違反も拒否。
        with self.assertRaises(GitgateError):
            build_git_argv(["new-branch"])
        with self.assertRaises(GitgateError):
            build_git_argv(["new-branch", "a", "b"])

    def test_diff_rejects_write_and_unknown_flags(self):
        for argv in [
            ["diff", "--output=/tmp/x"],
            ["diff", "-o", "/tmp/x"],
            ["diff", "--ext-diff"],
            ["diff", "--stat", "--output=/tmp/x"],
        ]:
            with self.subTest(argv=argv):
                with self.assertRaises(GitgateError):
                    build_git_argv(argv)

    def test_diff_rejects_bad_refs(self):
        for ref in ["-evil", "a;b", "a b", "a$(x)", "a\nb", "--upload-pack=x"]:
            with self.subTest(ref=ref):
                with self.assertRaises(GitgateError):
                    build_git_argv(["diff", ref])

    def test_log_rejects_bad_integer_and_unknown_flags(self):
        for argv in [
            ["log", "-n", "abc"],
            ["log", "-n"],
            ["log", "-nabc"],
            ["log", "--output=/tmp/x"],
            ["log", "--pretty=format:%x"],
            ["log", "HEAD"],  # 位置引数は不可
            ["log", "--grep"],
        ]:
            with self.subTest(argv=argv):
                with self.assertRaises(GitgateError):
                    build_git_argv(argv)

    def test_log_grep_pattern_rejects_control_chars(self):
        with self.assertRaises(GitgateError):
            build_git_argv(["log", "--grep", "a\nb"])


class MainSubprocessTests(unittest.TestCase):
    def test_publish_info_reports_only_fixed_origin_and_same_name_remote_ref(self):
        local_sha = "a" * 40
        remote_sha = "b" * 40
        completed = [
            subprocess.CompletedProcess([], 0, "https://github.com/o/r.git\n", ""),
            subprocess.CompletedProcess(
                [],
                0,
                "git@github.com:o/r.git\nssh://git@github.com/o/r.git\n",
                "",
            ),
            subprocess.CompletedProcess([], 0, "feature/publish\n", ""),
            subprocess.CompletedProcess([], 0, local_sha + "\n", ""),
            subprocess.CompletedProcess(
                [], 0, f"{remote_sha}\trefs/heads/feature/publish\n", ""
            ),
        ]
        stdout = StringIO()
        with patch.object(gitgate_cli.subprocess, "run", side_effect=completed) as run:
            with patch.object(gitgate_cli.sys, "stdout", stdout):
                rc = gitgate_cli.main(["publish-info"])

        self.assertEqual(rc, 0)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [
                ["git", "remote", "get-url", "origin"],
                ["git", "remote", "get-url", "--push", "--all", "origin"],
                ["git", "branch", "--show-current"],
                ["git", "rev-parse", "--verify", "HEAD"],
                [
                    "git",
                    "ls-remote",
                    "--heads",
                    "origin",
                    "refs/heads/feature/publish",
                ],
            ],
        )
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "current_branch": "feature/publish",
                "local_commit": local_sha,
                "origin_fetch_url": "https://github.com/o/r.git",
                "origin_push_urls": [
                    "git@github.com:o/r.git",
                    "ssh://git@github.com/o/r.git",
                ],
                "remote_commit": remote_sha,
                "remote_exists": True,
                "remote_ref": "refs/heads/feature/publish",
            },
        )

    def test_publish_info_falls_back_to_fetch_url_and_reports_missing_remote_ref(self):
        local_sha = "c" * 40
        completed = [
            subprocess.CompletedProcess([], 0, "git@github.com:o/r.git\n", ""),
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "feature/new\n", ""),
            subprocess.CompletedProcess([], 0, local_sha + "\n", ""),
            subprocess.CompletedProcess([], 0, "", ""),
        ]
        stdout = StringIO()
        with patch.object(gitgate_cli.subprocess, "run", side_effect=completed):
            with patch.object(gitgate_cli.sys, "stdout", stdout):
                rc = gitgate_cli.main(["publish-info"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "current_branch": "feature/new",
                "local_commit": local_sha,
                "origin_fetch_url": "git@github.com:o/r.git",
                "origin_push_urls": ["git@github.com:o/r.git"],
                "remote_commit": None,
                "remote_exists": False,
                "remote_ref": "refs/heads/feature/new",
            },
        )

    def test_publish_info_preserves_git_error_and_exit_code(self):
        failed = subprocess.CompletedProcess([], 128, "", "fatal: no origin\n")
        stderr = StringIO()
        with patch.object(gitgate_cli.subprocess, "run", return_value=failed):
            with patch.object(gitgate_cli.sys, "stderr", stderr):
                rc = gitgate_cli.main(["publish-info"])
        self.assertEqual(rc, 128)
        self.assertEqual(stderr.getvalue(), "fatal: no origin\n")

    def test_main_invokes_git_with_shell_false_list(self):
        calls = {}

        class FakeCompleted:
            returncode = 0

        def fake_run(argv, **kwargs):
            calls["argv"] = argv
            calls["kwargs"] = kwargs
            return FakeCompleted()

        orig = gitgate_cli.subprocess.run
        gitgate_cli.subprocess.run = fake_run
        try:
            rc = gitgate_cli.main(["status"])
        finally:
            gitgate_cli.subprocess.run = orig
        self.assertEqual(rc, 0)
        self.assertEqual(calls["argv"], ["git", "status"])
        self.assertIs(calls["kwargs"].get("shell", False), False)

    def test_main_returns_error_and_never_runs_git_on_bad_args(self):
        ran = {"count": 0}

        def fake_run(argv, **kwargs):  # pragma: no cover - must not be called
            ran["count"] += 1
            raise AssertionError("git must not run for rejected args")

        orig = gitgate_cli.subprocess.run
        gitgate_cli.subprocess.run = fake_run
        try:
            rc = gitgate_cli.main(["push", "--receive-pack=sh -c evil"])
        finally:
            gitgate_cli.subprocess.run = orig
        self.assertEqual(rc, 2)
        self.assertEqual(ran["count"], 0)

    def test_module_entry_point_runs(self):
        # `python3 -m gitgate` がパッケージとして起動できること（不正 verb で終了コード 2）。
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["python3", "-m", "gitgate", "merge", "feature"],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("gitgate:", result.stderr)


if __name__ == "__main__":
    unittest.main()
