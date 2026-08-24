"""`gitgate adopt-branch`（Issue #354・PR-2・FR-W10）の単体テスト。

検証観点:
  - 引数スキーマの拒否は **git を1回も実行する前に**起きる（runner スタブで呼び出し0件を assert）。
  - remote 先端 OID・PR head の再検証が fail-close（不一致・到達不能で `git switch` に到達しない）。
  - ローカル同名ブランチが在るときは拒否する（isolated worktree では想定外の状態）。
  - git の「別 worktree が掴んでいる」エラーが `BRANCH_ADOPT_ALREADY_CHECKED_OUT` へマップされる。
  - 正常系の checkout argv が `["git","switch","--create",<branch>,<oid>]` であること
    （current HEAD の暗黙継承ではなく検証済み exact OID を明示する）。

時刻依存なし（`.claude/rules/04-test-data.md`）: 本 verb は wall clock を一切読まない。
"""

import subprocess
import unittest

from branch_source import BranchSourceError
from gitgate.adopt import (
    AdoptBranchRequest,
    adopt_branch,
    parse_adopt_branch_args,
)

OID = "a" * 40
OTHER_OID = "b" * 40
BRANCH = "claude/issue-354-pr2"
REPO = "hiratashinnya/review-system"


class FakeGit:
    """`subprocess.run` 互換のスタブ。argv を記録し、応答を差し替えられる。"""

    def __init__(self, responses=None, timeout_keys=None):
        self.calls = []
        self.call_kwargs = []
        self.responses = responses or {}
        # ``timeout_keys`` に挙げた verb（例: "fetch"）が呼ばれたら
        # ``subprocess.TimeoutExpired`` を送出する（Issue #426・F-426-05）。
        self.timeout_keys = set(timeout_keys or ())

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        self.call_kwargs.append(kwargs)
        key = self._key(argv)
        if key in self.timeout_keys:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 30))
        rc, out, err = self.responses.get(key, (0, "", ""))
        return subprocess.CompletedProcess(list(argv), rc, out, err)

    def kwargs_for(self, verb):
        for argv, kwargs in zip(self.calls, self.call_kwargs):
            if self._key(argv) == verb:
                return kwargs
        return None

    @staticmethod
    def _key(argv):
        if len(argv) >= 2 and argv[1] == "rev-parse":
            return "rev-parse-local" if "--quiet" in argv else "rev-parse-remote"
        if len(argv) >= 3 and argv[1] == "branch" and argv[2] == "-D":
            return "branch-delete"
        if len(argv) >= 3 and argv[1] == "worktree" and argv[2] == "list":
            return "worktree-list"
        return argv[1] if len(argv) > 1 else ""

    @property
    def verbs(self):
        return [self._key(argv) for argv in self.calls]

    def argv_for(self, verb):
        for argv in self.calls:
            if self._key(argv) == verb:
                return argv
        return None


def porcelain_worktree_list(*, checked_out_branch=None):
    """``git worktree list --porcelain`` の疑似出力（main worktree ＋任意で1つの linked）。"""
    blocks = [f"worktree /repo\nHEAD {'0' * 40}\nbranch refs/heads/main\n"]
    if checked_out_branch is not None:
        blocks.append(
            f"worktree /repo/.claude/worktrees/agent-other\nHEAD {'0' * 40}\n"
            f"branch refs/heads/{checked_out_branch}\n"
        )
    return "\n".join(blocks) + "\n"


def default_responses(
    remote_oid=OID,
    local_exists=False,
    local_oid=None,
    checked_out_branch=None,
    branch_delete_ok=True,
):
    return {
        "fetch": (0, "", ""),
        "rev-parse-remote": (0, remote_oid + "\n", ""),
        # `--verify --quiet` は不在なら非0（＝ローカルに同名ブランチが無い）。
        "rev-parse-local": (
            (0, (local_oid or OID) + "\n", "") if local_exists else (1, "", "")
        ),
        "switch": (0, "", ""),
        "branch": (0, "", ""),
        "branch-delete": (0, "", "") if branch_delete_ok else (1, "", "error: cannot delete\n"),
        "worktree-list": (0, porcelain_worktree_list(checked_out_branch=checked_out_branch), ""),
    }


class FakeApi:
    def __init__(self, pull=None, error=None):
        self.pull = pull
        self.error = error
        self.calls = []

    def repository(self, repository):  # pragma: no cover - adopt は使わない
        raise AssertionError("adopt-branch must not query the repository endpoint")

    def pull_request(self, repository, number):
        self.calls.append((repository, number))
        if self.error is not None:
            raise self.error
        return self.pull


def open_pull(ref=BRANCH, sha=OID):
    return {"state": "open", "head": {"ref": ref, "sha": sha}}


class ParseAdoptBranchArgsTests(unittest.TestCase):
    def test_minimal_form(self):
        request = parse_adopt_branch_args(
            [BRANCH, "--repository", REPO, "--expected-oid", OID]
        )
        self.assertEqual(
            request, AdoptBranchRequest(BRANCH, REPO, OID, None)
        )

    def test_pr_form(self):
        request = parse_adopt_branch_args(
            [BRANCH, "--repository", REPO, "--expected-oid", OID, "--pr", "412"]
        )
        self.assertEqual(request.pr, 412)

    def test_uppercase_oid_is_normalized(self):
        request = parse_adopt_branch_args(
            [BRANCH, "--repository", REPO, "--expected-oid", OID.upper()]
        )
        self.assertEqual(request.expected_oid, OID)

    def test_rejects_bad_branch_names(self):
        for name in ["-D", "--force", "a b", "a;sh", "a$(x)", "a\nb", "a..b", "x/", ".hidden/x"]:
            with self.subTest(name=name):
                with self.assertRaises(BranchSourceError):
                    parse_adopt_branch_args(
                        [name, "--repository", REPO, "--expected-oid", OID]
                    )

    def test_rejects_bad_repository(self):
        for repo in ["owner", "owner/repo/extra", "owner repo", "owner/repo;sh", ""]:
            with self.subTest(repo=repo):
                with self.assertRaises(BranchSourceError):
                    parse_adopt_branch_args(
                        [BRANCH, "--repository", repo, "--expected-oid", OID]
                    )

    def test_rejects_non_40hex_oid(self):
        # 64hex（sha256 形）も adopt では受けない: worktree が掴む commit を一意に固定する用途で、
        # abbrev や別長を許すと「一致検査が緩い」入り口になる。
        for oid in ["", "abc", "z" * 40, "a" * 39, "a" * 41, "a" * 64, "HEAD", "-a" * 20]:
            with self.subTest(oid=oid):
                with self.assertRaises(BranchSourceError):
                    parse_adopt_branch_args(
                        [BRANCH, "--repository", REPO, "--expected-oid", oid]
                    )

    def test_rejects_non_positive_integer_pr(self):
        for pr in ["0", "-1", "1.5", "abc", "", " 1", "01"]:
            with self.subTest(pr=pr):
                with self.assertRaises(BranchSourceError):
                    parse_adopt_branch_args(
                        [BRANCH, "--repository", REPO, "--expected-oid", OID, "--pr", pr]
                    )

    def test_rejects_unknown_duplicate_and_valueless_flags(self):
        for args in [
            [],
            [BRANCH],
            [BRANCH, "--repository", REPO],
            [BRANCH, "--expected-oid", OID],
            [BRANCH, "--repository", REPO, "--expected-oid", OID, "--force"],
            [BRANCH, "--repository", REPO, "--expected-oid", OID, "--pr"],
            [BRANCH, "--repository", REPO, "--repository", REPO, "--expected-oid", OID],
        ]:
            with self.subTest(args=args):
                with self.assertRaises(BranchSourceError):
                    parse_adopt_branch_args(args)


class AdoptBranchGitInteractionTests(unittest.TestCase):
    def test_happy_path_switches_to_the_exact_verified_oid(self):
        git = FakeGit(default_responses())
        result = adopt_branch(
            AdoptBranchRequest(BRANCH, REPO, OID), cwd=None, runner=git
        )
        self.assertEqual(
            git.argv_for("switch"), ["git", "switch", "--create", BRANCH, OID]
        )
        self.assertEqual(git.argv_for("fetch"), ["git", "fetch", "--prune", "origin"])
        self.assertEqual(
            git.argv_for("branch"),
            ["git", "branch", f"--set-upstream-to=origin/{BRANCH}", BRANCH],
        )
        self.assertEqual(result.expected_oid, OID)
        self.assertEqual(result.policy_version, "branch-adopt/1.0")

    def test_shell_is_never_used(self):
        git = FakeGit(default_responses())

        def checking_runner(argv, **kwargs):
            self.assertIs(kwargs.get("shell", False), False)
            return git(argv, **kwargs)

        adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=checking_runner)

    def test_fetch_call_is_bounded_and_non_interactive(self):
        # stage 1 の fetch にだけ timeout と GIT_TERMINAL_PROMPT=0 が渡ること（純ローカル操作
        # には渡さない・Issue #426・F-426-05）。
        git = FakeGit(default_responses())
        adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        fetch_kwargs = git.kwargs_for("fetch")
        self.assertIsNotNone(fetch_kwargs)
        self.assertGreater(fetch_kwargs.get("timeout"), 0)
        self.assertEqual(fetch_kwargs.get("env", {}).get("GIT_TERMINAL_PROMPT"), "0")
        switch_kwargs = git.kwargs_for("switch")
        self.assertNotIn("timeout", switch_kwargs)
        self.assertNotIn("env", switch_kwargs)

    def test_fetch_timeout_fails_close(self):
        # F-426-05: 到達不能/認証待ちの origin で stage 1 の fetch がハングしうる欠陥を、
        # 有限時間の `subprocess.TimeoutExpired` で切り上げる。他の fetch 失敗と同じ
        # fail-close（BRANCH_GIT_ERROR）として扱い、switch には到達しない。
        git = FakeGit(default_responses(), timeout_keys={"fetch"})
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_GIT_ERROR")
        self.assertNotIn("switch", git.verbs)

    def test_remote_oid_mismatch_fails_close_before_switch(self):
        git = FakeGit(default_responses(remote_oid=OTHER_OID))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_OID_MISMATCH")
        self.assertNotIn("switch", git.verbs)

    def test_missing_remote_branch_fails_close_before_switch(self):
        responses = default_responses()
        responses["rev-parse-remote"] = (128, "", "fatal: Needed a single revision\n")
        git = FakeGit(responses)
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_REMOTE_MISSING")
        self.assertNotIn("switch", git.verbs)

    def test_unparsable_remote_oid_is_rejected(self):
        responses = default_responses()
        responses["rev-parse-remote"] = (0, "not-an-oid\n", "")
        git = FakeGit(responses)
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_REMOTE_OID_INVALID")
        self.assertNotIn("switch", git.verbs)

    def test_local_branch_diverging_from_origin_is_rejected(self):
        # ローカル ref があり、かつ origin の tip と違うコミットを指す＝正体不明のローカル作業。
        # 「無害な残留 ref」ではないので、tip の不一致だけで即 fail-close する
        # （`git worktree list` を呼ぶ必要すら無い＝defense-in-depth・Issue #426）。
        git = FakeGit(default_responses(local_exists=True, local_oid=OTHER_OID))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
        self.assertNotIn("switch", git.verbs)
        self.assertNotIn("worktree-list", git.verbs)
        self.assertNotIn("branch-delete", git.verbs)

    def test_stray_local_ref_matching_origin_is_reclaimed_and_adoption_succeeds(self):
        # adopt-branch 側単体の防御（Issue #426）: worktree-release がブランチ ref を
        # 消し損ねて（または旧版の実体・手動操作等で）残った stray ref——tip は origin と
        # 同じで、どの worktree にも checked out されていない——なら、以前は
        # `BRANCH_ADOPT_LOCAL_EXISTS` で失敗していたところを、無害と判定して自動的に
        # 削除し、adopt-branch は checkout まで成功する。**ここは FakeGit による adopt.py
        # 単体の検証**であり、release 側の実際の削除結果を入力にした通し検証ではない
        # （それは tests/unit/test_gitgate_worktree.py::BranchRefCleanupRealGitIntegrationTests
        # が実 git で担う・F-426-03）。
        git = FakeGit(default_responses(local_exists=True))
        result = adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(result.expected_oid, OID)
        self.assertIn("branch-delete", git.verbs)
        self.assertEqual(git.argv_for("branch-delete"), ["git", "branch", "-D", BRANCH])
        # 削除は switch より前に起きる。
        self.assertLess(
            git.verbs.index("branch-delete"), git.verbs.index("switch")
        )
        self.assertEqual(
            git.argv_for("switch"), ["git", "switch", "--create", BRANCH, OID]
        )

    def test_stray_local_ref_checked_out_elsewhere_is_not_reclaimed(self):
        # tip は origin と一致していても、別 worktree（main を含む）が現に checked out
        # していれば、無害とは言えない——reclaim せず既存どおり fail-close する。
        git = FakeGit(
            default_responses(local_exists=True, checked_out_branch=BRANCH)
        )
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
        self.assertNotIn("switch", git.verbs)
        self.assertNotIn("branch-delete", git.verbs)

    def test_worktree_list_failure_fails_close_instead_of_reclaiming(self):
        # 判定不能（`git worktree list` が失敗）は「無害」に倒さない——安全側で拒否する。
        responses = default_responses(local_exists=True)
        responses["worktree-list"] = (1, "", "fatal: not a git repository\n")
        git = FakeGit(responses)
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
        self.assertNotIn("switch", git.verbs)
        self.assertNotIn("branch-delete", git.verbs)

    def test_reclaim_delete_failure_fails_close(self):
        # 無害と判定できても、`git branch -D` 自体が失敗したら安全側（fail-close）に倒す。
        git = FakeGit(default_responses(local_exists=True, branch_delete_ok=False))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
        self.assertNotIn("switch", git.verbs)

    def test_already_checked_out_in_another_worktree_is_mapped(self):
        for stderr in [
            "fatal: 'x' is already checked out at '/repo/.claude/worktrees/agent-1'\n",
            "fatal: 'x' is already used by worktree at '/repo/.claude/worktrees/agent-1'\n",
        ]:
            with self.subTest(stderr=stderr):
                responses = default_responses()
                responses["switch"] = (128, "", stderr)
                git = FakeGit(responses)
                with self.assertRaises(BranchSourceError) as ctx:
                    adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
                self.assertEqual(
                    ctx.exception.reason, "BRANCH_ADOPT_ALREADY_CHECKED_OUT"
                )
                self.assertIn("collect-worktree", str(ctx.exception))
                self.assertNotIn("branch", git.verbs)

    def test_other_switch_failures_stay_generic(self):
        responses = default_responses()
        responses["switch"] = (128, "", "fatal: something else went wrong\n")
        git = FakeGit(responses)
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_GIT_ERROR")


class AdoptBranchPullRequestVerificationTests(unittest.TestCase):
    def test_open_pr_with_matching_head_is_accepted(self):
        git = FakeGit(default_responses())
        api = FakeApi(pull=open_pull())
        adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git)
        self.assertEqual(api.calls, [(REPO, 412)])
        self.assertEqual(
            git.argv_for("switch"), ["git", "switch", "--create", BRANCH, OID]
        )

    def test_api_is_not_consulted_without_pr(self):
        git = FakeGit(default_responses())
        api = FakeApi(pull=open_pull())
        adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID), api=api, runner=git)
        self.assertEqual(api.calls, [])

    def test_closed_pr_is_rejected(self):
        git = FakeGit(default_responses())
        api = FakeApi(pull={"state": "closed", "head": {"ref": BRANCH, "sha": OID}})
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_PR_NOT_OPEN")
        self.assertNotIn("switch", git.verbs)

    def test_head_ref_mismatch_is_rejected(self):
        git = FakeGit(default_responses())
        api = FakeApi(pull=open_pull(ref="claude/some-other-branch"))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_PR_HEAD_MISMATCH")
        self.assertNotIn("switch", git.verbs)

    def test_head_sha_mismatch_is_rejected(self):
        git = FakeGit(default_responses())
        api = FakeApi(pull=open_pull(sha=OTHER_OID))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git)
        self.assertEqual(ctx.exception.reason, "BRANCH_ADOPT_PR_HEAD_MISMATCH")
        self.assertNotIn("switch", git.verbs)

    def test_partial_api_response_is_rejected(self):
        for pull in [{"state": "open"}, {"state": "open", "head": {}}, "not-a-mapping"]:
            with self.subTest(pull=pull):
                git = FakeGit(default_responses())
                api = FakeApi(pull=pull)
                with self.assertRaises(BranchSourceError) as ctx:
                    adopt_branch(
                        AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git
                    )
                self.assertEqual(ctx.exception.reason, "BRANCH_API_PARTIAL_RESPONSE")
                self.assertNotIn("switch", git.verbs)

    def test_unreachable_api_fails_close(self):
        # 「確認できなかった」を「問題なし」に潰さない。API_UNREACHABLE は client 側が投げ、
        # adopt はそれを握り潰さずそのまま伝播させる（＝checkout に到達しない）。
        git = FakeGit(default_responses())
        api = FakeApi(error=BranchSourceError("API_UNREACHABLE"))
        with self.assertRaises(BranchSourceError) as ctx:
            adopt_branch(AdoptBranchRequest(BRANCH, REPO, OID, 412), api=api, runner=git)
        self.assertEqual(ctx.exception.reason, "API_UNREACHABLE")
        self.assertNotIn("switch", git.verbs)


class AdoptBranchArgumentValidationPrecedesGitTests(unittest.TestCase):
    def test_rejected_arguments_never_run_git(self):
        # 引数スキーマ違反は parse 段で落ちる＝git は1回も呼ばれない（fail-close の中核）。
        ran = {"count": 0}

        def forbidden_runner(argv, **kwargs):  # pragma: no cover - must not be called
            ran["count"] += 1
            raise AssertionError("git must not run for rejected arguments")

        bad_argument_sets = [
            [],
            ["--force", "--repository", REPO, "--expected-oid", OID],
            [BRANCH, "--repository", "owner", "--expected-oid", OID],
            [BRANCH, "--repository", REPO, "--expected-oid", "HEAD"],
            [BRANCH, "--repository", REPO, "--expected-oid", OID, "--pr", "0"],
        ]
        for args in bad_argument_sets:
            with self.subTest(args=args):
                with self.assertRaises(BranchSourceError):
                    request = parse_adopt_branch_args(args)
                    adopt_branch(request, runner=forbidden_runner)
        self.assertEqual(ran["count"], 0)


if __name__ == "__main__":
    unittest.main()
