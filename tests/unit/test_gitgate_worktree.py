"""`gitgate` の worktree ライフサイクル verb（Issue #354・PR-2）の単体テスト。

対象:
  * ``worktree-release``  — 冪等な解放（FR-W5）
  * ``collect-worktree``  — 回収 → 検証 → 解放を1操作で（FR-W2）
  * ``worktree-forget``   — ``stale`` を ``abandoned`` へ逃がす（worktree もエントリも消さない）

中核の検証観点:
  * **パスガードを通らないものに対して ``git worktree remove`` が1度も呼ばれない**
    （runner スタブで呼び出し履歴を検査する）。削除経路を持つモジュールなので、
    「拒否した」だけでなく「git に到達していない」ことまで固定する。
  * ``running`` エントリは ``--force-uncollected`` を付けても解放されない。
  * 回収（読み取り・書き込み・sha256 検証）に失敗したら**解放段に到達しない**。
  * ``worktree-forget`` はエントリを削除せず ``abandoned`` へ遷移させるだけ。

時刻の扱い（`.claude/rules/04-test-data.md`）:
  ``now`` は常に固定値を**引数で注入**する。台帳にも本モジュールにも wall clock 比較は
  存在しないため、時間経過だけでこのテストが赤くなる経路は構造的に無い。
  それを担保するために :class:`NoWallClockReadTests` が実装ソースを機械検査する。
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gitgate.worktree import (
    WorktreeError,
    collect_worktree,
    parse_collect_worktree_args,
    parse_worktree_forget_args,
    parse_worktree_release_args,
    validate_collect_dest,
    validate_handoff_relpath,
    validate_worktree_path,
    worktree_forget,
    worktree_release,
)
from issue_start import worktree_ledger

# wall clock とは一切比較されない固定スタンプ（診断用のスタンプを台帳に書くだけ）。
FIXED_NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
AGENT_ID = "ae14ef51f0cb8b8cf"
WT_REL = f".claude/worktrees/agent-{AGENT_ID}"
HANDOFF_REL = "tmp/_handoff/issue-implementer--issue-354-pr2.yaml"
HANDOFF_BODY = b"agent: issue-implementer\nstatus: pr_opened\nissue: 354\n"


class FakeGit:
    """`subprocess.run` 互換のスタブ。

    ``git worktree list --porcelain`` は porcelain 形式を実際に組み立てて返し
    （先頭レコード＝main worktree）、``git worktree remove`` は実ディレクトリを消して
    git の副作用を模す。呼び出し履歴は ``calls`` に残る。
    """

    def __init__(self, root, linked=(), fail_branch_delete=False):
        self.root = Path(root)
        self.linked = list(linked)
        self.calls = []
        self.fail_branch_delete = fail_branch_delete

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "worktree", "list"]:
            return subprocess.CompletedProcess(argv, 0, self._porcelain(), "")
        if argv[:3] == ["git", "worktree", "remove"]:
            shutil.rmtree(argv[-1], ignore_errors=True)
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "branch", "-D"]:
            if self.fail_branch_delete:
                return subprocess.CompletedProcess(
                    argv, 1, "", "error: branch not found\n"
                )
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def _porcelain(self):
        blocks = [f"worktree {self.root}\nHEAD {'0' * 40}\nbranch refs/heads/main\n"]
        for relative in self.linked:
            blocks.append(
                f"worktree {self.root / relative}\nHEAD {'0' * 40}\n"
                f"branch refs/heads/claude/issue-354\n"
            )
        return "\n".join(blocks) + "\n"

    @property
    def removals(self):
        return [argv for argv in self.calls if argv[:3] == ["git", "worktree", "remove"]]

    @property
    def branch_deletes(self):
        return [argv for argv in self.calls if argv[:3] == ["git", "branch", "-D"]]


class ForbiddenGit:
    """呼ばれたら即失敗する runner（「git に到達しない」ことの assert 用）。"""

    def __call__(self, argv, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError(f"git must not run, but got: {argv!r}")


class LedgerFixture(unittest.TestCase):
    """台帳付きの一時 repo-root を用意する共通土台。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def make_worktree(self, relative=WT_REL, *, handoff=HANDOFF_REL, body=HANDOFF_BODY):
        directory = self.root / relative
        directory.mkdir(parents=True)
        if handoff is not None:
            target = directory / handoff
            target.parent.mkdir(parents=True)
            target.write_bytes(body)
        return directory

    def open_entry(self, *, issue=354, agent_type="issue-implementer", handoff=HANDOFF_REL):
        return worktree_ledger.open_entry(
            self.root,
            issue=issue,
            agent_type=agent_type,
            round=None,
            branch_name="claude/issue-354-pr2",
            handoff_path=handoff,
            now=FIXED_NOW,
        )

    def bound_entry(self, *, worktree=WT_REL, **kwargs):
        entry_id = self.open_entry(**kwargs)
        bound = worktree_ledger.bind_agent(
            self.root,
            agent_type=kwargs.get("agent_type", "issue-implementer"),
            agent_id=AGENT_ID,
            worktree_path=worktree,
        )
        self.assertEqual(bound, entry_id)
        return entry_id

    def entry_with_status(self, status, **kwargs):
        """``running`` から目的の状態まで**正規ルートを辿って**遷移させる。

        ``running`` → ``collected`` の直行辺は無い（Issue #354 F-354-01）ので、回収済みを
        作るには ``stopped`` を経由する。テスト側で近道を作ると状態機械の意味が崩れる。
        """
        entry_id = self.bound_entry(**kwargs)
        route = {
            "running": (),
            "stopped": ("stopped",),
            "collected": ("stopped", "collected"),
            "released": ("stopped", "collected", "released"),
            "stale": ("stale",),
            "abandoned": ("abandoned",),
        }[status]
        for step in route:
            worktree_ledger.mark(self.root, entry_id, step, now=FIXED_NOW)
        return entry_id

    def status_of(self, entry_id):
        entry = worktree_ledger.find_by_agent_id(self.root, AGENT_ID)
        if entry is not None and entry.get("entry_id") == entry_id:
            return entry.get("status")
        for item in worktree_ledger.read_ledger(self.root)["entries"]:
            if item.get("entry_id") == entry_id:
                return item.get("status")
        return None

    def entry(self, entry_id):
        for item in worktree_ledger.read_ledger(self.root)["entries"]:
            if item.get("entry_id") == entry_id:
                return item
        return None


# ---------------------------------------------------------------------------
# パス検証（純粋な構文検査・FS には触らない）
# ---------------------------------------------------------------------------


class ValidateWorktreePathTests(unittest.TestCase):
    def test_accepts_the_exact_shape(self):
        self.assertEqual(validate_worktree_path(WT_REL), WT_REL)
        self.assertEqual(validate_worktree_path("./" + WT_REL), WT_REL)
        self.assertEqual(validate_worktree_path(WT_REL + "/"), WT_REL)

    def test_rejects_absolute_and_home_paths(self):
        for value in [
            "/tmp/x",
            f"/repo/{WT_REL}",
            "~/repo/.claude/worktrees/agent-x",
            "C:/repo/.claude/worktrees/agent-x",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(value)

    def test_rejects_parent_references_before_normalization(self):
        # `.claude/worktrees/agent-x/../../../etc` は正規化すると repo 外を指す。正規化に
        # 吸収させず、`..` という要素が在ることそれ自体で拒否する。
        for value in [
            ".claude/worktrees/../../etc",
            ".claude/worktrees/agent-x/..",
            ".claude/worktrees/agent-x/../agent-y",
            "../.claude/worktrees/agent-x",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(value)

    def test_rejects_paths_outside_the_worktree_root(self):
        for value in [
            "docs/agent-x",
            "worktrees/agent-x",
            ".claude/agents/agent-x",
            ".claude/worktrees",
            "",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(value)

    def test_rejects_non_agent_directory_names(self):
        for name in ["notagent", "agent", "agent-", "Agent-x", "agent-x!", "agent-" + "y" * 65]:
            with self.subTest(name=name):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(f".claude/worktrees/{name}")

    def test_rejects_deeper_paths(self):
        for value in [
            ".claude/worktrees/agent-x/sub",
            ".claude/worktrees/agent-x/tmp/_handoff",
            ".claude/worktrees/agent-x/.git",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(value)

    def test_rejects_control_characters_and_backslashes(self):
        for value in [
            ".claude/worktrees/agent-x\n",
            ".claude/worktrees/agent-x\0",
            ".claude\\worktrees\\agent-x",
        ]:
            with self.subTest(value=repr(value)):
                with self.assertRaises(WorktreeError):
                    validate_worktree_path(value)


class ValidateHandoffRelpathTests(unittest.TestCase):
    def test_accepts_with_and_without_suffix(self):
        for value in [
            "tmp/_handoff/issue-implementer--issue-354.yaml",
            "tmp/_handoff/issue-implementer--issue-354-pr2.yaml",
            "tmp/_handoff/issue-fixer--issue-354-round2.yaml",
        ]:
            with self.subTest(value=value):
                self.assertEqual(validate_handoff_relpath(value), value)

    def test_boundary_check_rejects_a_different_issue_number(self):
        # 境界検査が無いと `issue: 354` の呼び出しで `…--issue-3541.yaml` を受理してしまう。
        with self.assertRaises(WorktreeError) as ctx:
            validate_handoff_relpath(
                "tmp/_handoff/issue-implementer--issue-3541.yaml", expected_issue=354
            )
        self.assertEqual(ctx.exception.reason, "COLLECT_HANDOFF_ISSUE_MISMATCH")
        # 同じ Issue の別ラウンド（サフィックス違い）は受理する（上書き破壊を避けるため
        # サフィックスの有無・内容そのものは問わない）。
        self.assertTrue(
            validate_handoff_relpath(
                "tmp/_handoff/issue-implementer--issue-354-pr2.yaml", expected_issue=354
            )
        )

    def test_rejects_shape_violations(self):
        for value in [
            "/tmp/_handoff/a--issue-1.yaml",
            "~/tmp/_handoff/a--issue-1.yaml",
            "tmp/_handoff/../_worktree/ledger.json",
            "tmp/_handoff/sub/a--issue-1.yaml",
            "tmp/_worktree/a--issue-1.yaml",
            "_handoff/a--issue-1.yaml",
            "tmp/_handoff",
            "",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_handoff_relpath(value)

    def test_rejects_filename_violations(self):
        for name in [
            "issue-354.yaml",             # `<agent>--` が無い
            "a--issue-.yaml",             # 番号が無い
            "a--issue-354.txt",           # 拡張子違い
            "a--issue-354 pr2.yaml",      # 空白
            "a--issue-354;sh.yaml",       # シェル記号
            "a--issue-354/x.yaml",        # パス区切り（要素数で先に落ちる）
            "-a--issue-354.yaml",         # 先頭 `-`
        ]:
            with self.subTest(name=name):
                with self.assertRaises(WorktreeError):
                    validate_handoff_relpath(f"tmp/_handoff/{name}")


class ValidateCollectDestTests(unittest.TestCase):
    def test_accepts_paths_under_the_handoff_directory(self):
        value = "tmp/_handoff/collected/wl-abc123def456--x.yaml"
        self.assertEqual(validate_collect_dest(value), value)

    def test_rejects_paths_outside_the_handoff_directory(self):
        for value in [
            "/etc/passwd",
            "../outside.yaml",
            "tmp/_worktree/ledger.json",
            "docs/collected.yaml",
            "tmp/_handoff",
            "tmp/_handoff/../_worktree/x.yaml",
            "tmp/_handoff/-weird.yaml",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(WorktreeError):
                    validate_collect_dest(value)


# ---------------------------------------------------------------------------
# 引数スキーマ
# ---------------------------------------------------------------------------


class ParseArgsTests(unittest.TestCase):
    def test_release_requires_a_positional_path(self):
        for args in [[], ["--entry", "wl-0123456789ab"], ["--force-uncollected"]]:
            with self.subTest(args=args):
                with self.assertRaises(WorktreeError):
                    parse_worktree_release_args(args)

    def test_release_force_requires_a_reason(self):
        with self.assertRaises(WorktreeError) as ctx:
            parse_worktree_release_args([WT_REL, "--force-uncollected"])
        self.assertEqual(ctx.exception.reason, "WORKTREE_REASON_EMPTY")
        request = parse_worktree_release_args(
            [WT_REL, "--force-uncollected", "--reason", "orphan cleanup"]
        )
        self.assertTrue(request.force_uncollected)
        self.assertEqual(request.reason, "orphan cleanup")

    def test_release_rejects_unknown_and_duplicate_flags(self):
        for args in [
            [WT_REL, "--force"],
            [WT_REL, "--entry"],
            [WT_REL, "--entry", "wl-0123456789ab", "--entry", "wl-0123456789ab"],
            [WT_REL, "--entry", "not-an-entry-id"],
            [WT_REL, "--force-uncollected", "--force-uncollected", "--reason", "x"],
        ]:
            with self.subTest(args=args):
                with self.assertRaises(WorktreeError):
                    parse_worktree_release_args(args)

    def test_collect_accepts_both_forms(self):
        by_entry = parse_collect_worktree_args(["--entry", "wl-0123456789ab"])
        self.assertEqual(by_entry.entry_id, "wl-0123456789ab")
        self.assertIsNone(by_entry.worktree_path)
        explicit = parse_collect_worktree_args([WT_REL, "--handoff", HANDOFF_REL])
        self.assertEqual(explicit.worktree_path, WT_REL)
        self.assertEqual(explicit.handoff_path, HANDOFF_REL)

    def test_collect_requires_a_target(self):
        with self.assertRaises(WorktreeError):
            parse_collect_worktree_args([])

    def test_collect_explicit_form_requires_handoff(self):
        with self.assertRaises(WorktreeError):
            parse_collect_worktree_args([WT_REL])

    def test_collect_allow_missing_handoff_requires_a_reason(self):
        with self.assertRaises(WorktreeError):
            parse_collect_worktree_args(
                [WT_REL, "--handoff", HANDOFF_REL, "--allow-missing-handoff"]
            )
        request = parse_collect_worktree_args(
            [WT_REL, "--handoff", HANDOFF_REL, "--allow-missing-handoff", "--reason", "crashed"]
        )
        self.assertTrue(request.allow_missing_handoff)

    def test_forget_requires_entry_and_reason(self):
        with self.assertRaises(WorktreeError):
            parse_worktree_forget_args([])
        with self.assertRaises(WorktreeError) as ctx:
            parse_worktree_forget_args(["--entry", "wl-0123456789ab"])
        self.assertEqual(ctx.exception.reason, "WORKTREE_FORGET_REASON_REQUIRED")
        with self.assertRaises(WorktreeError):
            parse_worktree_forget_args(["--reason", "x"])
        request = parse_worktree_forget_args(
            ["--entry", "wl-0123456789ab", "--reason", "worktree already gone"]
        )
        self.assertEqual(request.entry_id, "wl-0123456789ab")

    def test_forget_rejects_a_positional_argument(self):
        with self.assertRaises(WorktreeError):
            parse_worktree_forget_args([WT_REL, "--entry", "wl-0123456789ab", "--reason", "x"])


# ---------------------------------------------------------------------------
# worktree-release
# ---------------------------------------------------------------------------


class WorktreeReleasePathGuardTests(LedgerFixture):
    """パスガードを通らないものに対して ``git worktree remove`` を1度も呼ばない。"""

    def assert_never_touches_git(self, path, **kwargs):
        git = ForbiddenGit()
        with self.assertRaises(WorktreeError):
            worktree_release(self.root, path, now=FIXED_NOW, runner=git, **kwargs)

    def test_syntactic_rejections_never_reach_git(self):
        for path in [
            "/tmp/evil",
            "~/evil",
            "../.claude/worktrees/agent-x",
            ".claude/worktrees/../../etc",
            ".claude/worktrees/agent-x/..",
            "docs/agent-x",
            ".claude/worktrees/notagent",
            ".claude/worktrees/agent-x/sub",
            ".claude/worktrees/agent-x/tmp/_handoff",
            ".claude\\worktrees\\agent-x",
            "",
        ]:
            with self.subTest(path=path):
                self.assert_never_touches_git(
                    path, force_uncollected=True, reason="guard test"
                )

    def test_symlinked_components_are_rejected_without_removing(self):
        # `.claude/worktrees/agent-<id>` 自体が symlink（外部ディレクトリへの誘導）。
        outside = self.root / "outside"
        outside.mkdir()
        link_parent = self.root / ".claude" / "worktrees"
        link_parent.mkdir(parents=True)
        os.symlink(outside, link_parent / f"agent-{AGENT_ID}")
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root,
                WT_REL,
                force_uncollected=True,
                reason="guard test",
                now=FIXED_NOW,
                runner=git,
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_PATH_SYMLINK")
        self.assertEqual(git.removals, [])
        self.assertTrue(outside.exists())

    def test_symlinked_intermediate_directory_is_rejected(self):
        # `.claude/worktrees` がまるごと symlink のケース。
        outside = self.root / "elsewhere"
        (outside / f"agent-{AGENT_ID}").mkdir(parents=True)
        (self.root / ".claude").mkdir()
        os.symlink(outside, self.root / ".claude" / "worktrees")
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root,
                WT_REL,
                force_uncollected=True,
                reason="guard test",
                now=FIXED_NOW,
                runner=git,
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_PATH_SYMLINK")
        self.assertEqual(git.removals, [])

    def test_directory_not_registered_with_git_is_not_removed(self):
        # 形は合っているが git の linked worktree ではない＝ただのディレクトリ。消さない。
        self.make_worktree()
        git = FakeGit(self.root, linked=[])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root,
                WT_REL,
                force_uncollected=True,
                reason="guard test",
                now=FIXED_NOW,
                runner=git,
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_NOT_GIT_MANAGED")
        self.assertEqual(git.removals, [])
        self.assertTrue((self.root / WT_REL).is_dir())


class WorktreeReleaseStatusTests(LedgerFixture):
    def test_running_entry_is_never_released_even_with_force(self):
        entry_id = self.entry_with_status("running")
        self.make_worktree()
        for kwargs in [
            {},
            {"force_uncollected": True, "reason": "I really mean it"},
        ]:
            with self.subTest(kwargs=kwargs):
                git = FakeGit(self.root, linked=[WT_REL])
                with self.assertRaises(WorktreeError) as ctx:
                    worktree_release(
                        self.root, WT_REL, now=FIXED_NOW, runner=git, **kwargs
                    )
                self.assertEqual(ctx.exception.reason, "WORKTREE_LIVE")
                self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "running")
        self.assertTrue((self.root / WT_REL).is_dir())

    def test_stopped_entry_is_never_released_before_collection(self):
        # `stopped`＝まだ回収を試みていない。`stale`（回収を試みて失敗した）と違って
        # `--force-uncollected` の逃げ道を共有しない——共有すると両者の区別が消える。
        entry_id = self.entry_with_status("stopped")
        self.make_worktree()
        for kwargs in [
            {},
            {"force_uncollected": True, "reason": "回収を飛ばしたい"},
        ]:
            with self.subTest(kwargs=kwargs):
                git = FakeGit(self.root, linked=[WT_REL])
                with self.assertRaises(WorktreeError) as ctx:
                    worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git, **kwargs)
                self.assertEqual(ctx.exception.reason, "WORKTREE_NOT_COLLECTED")
                self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stopped")
        self.assertTrue((self.root / WT_REL).is_dir())

    def test_reason_without_force_is_recorded_in_the_notes(self):
        # F-354-04: 受理・検証まで通った `--reason` は必ず台帳に残す。
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        worktree_release(
            self.root, WT_REL, reason="PR-3 の掃引から解放", now=FIXED_NOW, runner=git
        )
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn("worktree-release: PR-3 の掃引から解放", notes)

    def test_open_entry_is_rejected_as_not_bound(self):
        entry_id = self.open_entry()
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        # `open` は worktree_path が未束縛なので `--entry` で指す。
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root, WT_REL, entry_id=entry_id, now=FIXED_NOW, runner=git
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_NOT_BOUND")
        self.assertEqual(git.removals, [])

    def test_collected_entry_is_released(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertTrue(outcome.removed)
        self.assertEqual(outcome.status, "released")
        self.assertEqual(len(git.removals), 1)
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertFalse((self.root / WT_REL).exists())

    def test_stale_entry_requires_force_with_reason(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "WORKTREE_NOT_COLLECTED")
        self.assertEqual(git.removals, [])
        with self.assertRaises(WorktreeError):
            worktree_release(
                self.root, WT_REL, force_uncollected=True, now=FIXED_NOW, runner=git
            )
        self.assertEqual(git.removals, [])
        outcome = worktree_release(
            self.root,
            WT_REL,
            force_uncollected=True,
            reason="handoff は回収不能だった",
            now=FIXED_NOW,
            runner=git,
        )
        self.assertTrue(outcome.removed)
        self.assertEqual(self.status_of(entry_id), "released")
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn(
            "worktree-release --force-uncollected: handoff は回収不能だった", notes
        )

    def test_orphan_worktree_requires_force_with_reason(self):
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "WORKTREE_ORPHAN_REQUIRES_FORCE")
        self.assertEqual(git.removals, [])
        outcome = worktree_release(
            self.root,
            WT_REL,
            force_uncollected=True,
            reason="台帳に無い残留 worktree の掃除",
            now=FIXED_NOW,
            runner=git,
        )
        self.assertTrue(outcome.removed)
        self.assertIsNone(outcome.entry_id)

    def test_entry_and_path_must_agree(self):
        entry_id = self.entry_with_status("collected")
        other = ".claude/worktrees/agent-deadbeef"
        self.make_worktree(other, handoff=None)
        git = FakeGit(self.root, linked=[other])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root, other, entry_id=entry_id, now=FIXED_NOW, runner=git
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_ENTRY_PATH_MISMATCH")
        self.assertEqual(git.removals, [])

    def test_unknown_entry_id_is_rejected(self):
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(
                self.root, WT_REL, entry_id="wl-000000000000", now=FIXED_NOW, runner=git
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_ENTRY_NOT_FOUND")
        self.assertEqual(git.removals, [])


class WorktreeReleaseIdempotencyTests(LedgerFixture):
    """FR-W5: 冪等であること（二重実行・対象不在で成功する）。"""

    def test_second_release_is_a_no_op_success(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        first = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertTrue(first.removed)
        second = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertFalse(second.removed)
        self.assertEqual(second.status, "released")
        # 2回目は削除を呼ばない（既に released なので git に触れる必要が無い）。
        self.assertEqual(len(git.removals), 1)
        self.assertEqual(self.status_of(entry_id), "released")

    def test_missing_directory_with_collected_entry_succeeds(self):
        entry_id = self.entry_with_status("collected")
        git = FakeGit(self.root, linked=[])
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertFalse(outcome.removed)
        self.assertEqual(outcome.status, "released")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "released")

    def test_abandoned_entry_with_residue_is_removed_without_leaving_the_terminal_state(self):
        # F-354-02: `worktree-forget` は台帳を `abandoned` にするだけで実体を消さない。
        # ここで実体を見ずに早期 return すると、forget 後に残った worktree を消す経路が
        # どこにも無くなる（PR-3 の unclaimed deny が恒久化する）。
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        worktree_forget(self.root, entry_id, reason="回収不能", now=FIXED_NOW)
        self.assertTrue((self.root / WT_REL).is_dir())
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = worktree_release(
            self.root, WT_REL, reason="forget 後の残留を掃除", now=FIXED_NOW, runner=git
        )
        self.assertTrue(outcome.removed)
        self.assertEqual(len(git.removals), 1)
        self.assertFalse((self.root / WT_REL).exists())
        # 台帳は `abandoned` のまま（`released` へ進めると「諦めた」記録が消える）。
        self.assertEqual(outcome.status, "abandoned")
        self.assertEqual(self.status_of(entry_id), "abandoned")
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn("worktree-release: 終端状態（abandoned）の残留実体を削除した", notes)
        self.assertIn("worktree-release: forget 後の残留を掃除", notes)

    def test_terminal_entry_without_residue_is_a_no_op(self):
        entry_id = self.entry_with_status("abandoned")
        git = FakeGit(self.root, linked=[])
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertFalse(outcome.removed)
        self.assertEqual(outcome.status, "abandoned")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "abandoned")
        self.assertEqual(self.entry(entry_id)["notes"], [])

    def test_terminal_residue_that_is_not_git_managed_is_not_removed(self):
        # 終端状態でも「消してよいパスか」の判定は緩めない。
        entry_id = self.entry_with_status("abandoned")
        self.make_worktree()
        git = FakeGit(self.root, linked=[])
        with self.assertRaises(WorktreeError) as ctx:
            worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "WORKTREE_NOT_GIT_MANAGED")
        self.assertEqual(git.removals, [])
        self.assertTrue((self.root / WT_REL).is_dir())
        self.assertEqual(self.status_of(entry_id), "abandoned")


# ---------------------------------------------------------------------------
# worktree-release: ローカルブランチ ref の後始末（Issue #426）
# ---------------------------------------------------------------------------


class WorktreeReleaseBranchRefCleanupTests(LedgerFixture):
    """worktree 実体の削除に成功した後、台帳の ``branch_name`` に対応するローカル ref も
    削除する（``_cleanup_branch_ref``）。放置すると、次の ``issue-fixer`` の
    ``gitgate adopt-branch`` が ``BRANCH_ADOPT_LOCAL_EXISTS`` で失敗する（本 Issue の core）。
    """

    def test_release_deletes_the_local_branch_ref_and_records_success(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertTrue(outcome.removed)
        self.assertEqual(
            git.branch_deletes, [["git", "branch", "-D", "claude/issue-354-pr2"]]
        )
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn(
            "worktree-release: ローカルブランチ ref claude/issue-354-pr2 を削除した", notes
        )

    def test_terminal_state_residual_cleanup_also_deletes_the_branch_ref(self):
        # F-354-02 の残留実体削除経路（`released`/`abandoned` で実体だけ残っている場合）でも
        # 同じくブランチ ref を削除する。
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        worktree_forget(self.root, entry_id, reason="回収不能", now=FIXED_NOW)
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = worktree_release(
            self.root, WT_REL, reason="forget 後の残留を掃除", now=FIXED_NOW, runner=git
        )
        self.assertTrue(outcome.removed)
        self.assertEqual(
            git.branch_deletes, [["git", "branch", "-D", "claude/issue-354-pr2"]]
        )
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn(
            "worktree-release: ローカルブランチ ref claude/issue-354-pr2 を削除した", notes
        )

    def test_branch_ref_deletion_failure_does_not_fail_the_release_but_is_recorded(self):
        # A: git branch -D の失敗は worktree_release() 全体をフェイルさせない
        #    （フェイルオープン）——ただし成否は必ず notes に残す。
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL], fail_branch_delete=True)
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertTrue(outcome.removed)
        self.assertEqual(outcome.status, "released")
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertFalse((self.root / WT_REL).exists())
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertTrue(
            any(
                note.startswith(
                    "worktree-release: ローカルブランチ ref claude/issue-354-pr2 の削除に失敗した"
                )
                for note in notes
            ),
            notes,
        )

    def test_no_branch_name_on_the_entry_skips_cleanup_without_error(self):
        # `branch_name` が無い（旧エントリ／`round`/`handoff` 拡張前等）場合は単に何もしない。
        entry_id = worktree_ledger.open_entry(
            self.root,
            issue=354,
            agent_type="issue-implementer",
            round=None,
            branch_name=None,
            handoff_path=HANDOFF_REL,
            now=FIXED_NOW,
        )
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id=AGENT_ID, worktree_path=WT_REL
        )
        for step in ("stopped", "collected"):
            worktree_ledger.mark(self.root, entry_id, step, now=FIXED_NOW)
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        self.assertTrue(outcome.removed)
        self.assertEqual(git.branch_deletes, [])

    def test_crossover_stray_ref_left_behind_no_longer_blocks_a_later_adopt(self):
        # クロスオーバー回帰（Issue #426）: worktree X を保持していたエントリを解放したら、
        # その worktree が保持していたブランチのローカル ref も一緒に消える。これにより
        # 別の adopt_branch() 呼び出し（別 worktree・同じブランチ名）が
        # `BRANCH_ADOPT_LOCAL_EXISTS` を引かなくなる（gitgate.adopt 側の検証は
        # tests/unit/test_gitgate_adopt.py が担当。ここでは A 側の削除実行を固定する）。
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        # 削除対象が「そのエントリが束縛していたブランチ名」ちょうどであること
        # （adopt-branch が同名で衝突検査するのはこのブランチ）。
        deleted_branches = {argv[3] for argv in git.branch_deletes}
        self.assertEqual(deleted_branches, {"claude/issue-354-pr2"})


# ---------------------------------------------------------------------------
# collect-worktree
# ---------------------------------------------------------------------------


class CollectWorktreeTests(LedgerFixture):
    def test_collects_verifies_then_releases_in_one_operation(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(
            self.root, entry_id=entry_id, now=FIXED_NOW, runner=git
        )
        expected_dest = (
            f"tmp/_handoff/collected/{entry_id}--issue-implementer--issue-354-pr2.yaml"
        )
        self.assertEqual(outcome.collected_to, expected_dest)
        self.assertTrue(outcome.released)
        self.assertEqual((self.root / expected_dest).read_bytes(), HANDOFF_BODY)
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertFalse((self.root / WT_REL).exists())
        self.assertEqual(len(git.removals), 1)
        self.assertEqual(self.entry(entry_id)["collected_to"], expected_dest)

    def test_stopped_entry_walks_the_full_route_to_released(self):
        # F-354-01: PR-3 の `SubagentStop` は `running` → `stopped` へ落としてから
        # `collect-worktree --entry` を呼ぶ。その正規ルートが端まで通ることを固定する。
        entry_id = self.entry_with_status("stopped")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        expected_dest = (
            f"tmp/_handoff/collected/{entry_id}--issue-implementer--issue-354-pr2.yaml"
        )
        self.assertEqual(outcome.collected_to, expected_dest)
        self.assertTrue(outcome.released)
        self.assertEqual((self.root / expected_dest).read_bytes(), HANDOFF_BODY)
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertFalse((self.root / WT_REL).exists())

    def test_entry_and_path_mismatch_stops_before_any_side_effect(self):
        # F-354-03: 食い違いを段6（解放段）まで持ち越すと、別 worktree の handoff を
        # 回収した上で台帳を `collected` と誤記録した後で落ちる。
        entry_id = self.entry_with_status("stopped")
        other = ".claude/worktrees/agent-deadbeef"
        self.make_worktree()
        self.make_worktree(other)
        git = FakeGit(self.root, linked=[WT_REL, other])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(
                self.root,
                entry_id=entry_id,
                worktree_path=other,
                now=FIXED_NOW,
                runner=git,
            )
        self.assertEqual(ctx.exception.reason, "WORKTREE_ENTRY_PATH_MISMATCH")
        # FS への副作用も台帳への副作用も1つも起きていない。
        self.assertEqual(git.calls, [])
        self.assertFalse((self.root / "tmp/_handoff/collected").exists())
        self.assertEqual(self.status_of(entry_id), "stopped")
        self.assertIsNone(self.entry(entry_id)["collected_to"])
        self.assertTrue((self.root / other).is_dir())
        self.assertTrue((self.root / WT_REL).is_dir())

    def test_reason_is_recorded_even_when_the_handoff_is_collected(self):
        # F-354-04: 回収に成功した経路でも `--reason` を落とさない。
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        collect_worktree(
            self.root,
            entry_id=entry_id,
            reason="SubagentStop からの自動回収",
            now=FIXED_NOW,
            runner=git,
        )
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertEqual(
            notes.count("collect-worktree: SubagentStop からの自動回収"),
            1,
            f"理由はちょうど1回だけ記録される: {notes!r}",
        )

    def test_reason_is_recorded_when_the_entry_was_already_collected(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        collect_worktree(
            self.root, entry_id=entry_id, reason="解放だけやり直す", now=FIXED_NOW, runner=git
        )
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertEqual(notes.count("collect-worktree: 解放だけやり直す"), 1, repr(notes))

    def test_explicit_form_without_a_ledger_entry(self):
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(
            self.root,
            worktree_path=WT_REL,
            handoff_path=HANDOFF_REL,
            now=FIXED_NOW,
            runner=git,
        )
        expected_dest = (
            f"tmp/_handoff/collected/agent-{AGENT_ID}"
            "--issue-implementer--issue-354-pr2.yaml"
        )
        self.assertEqual(outcome.collected_to, expected_dest)
        self.assertEqual((self.root / expected_dest).read_bytes(), HANDOFF_BODY)
        self.assertTrue(outcome.released)

    def test_into_overrides_the_destination(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(
            self.root,
            entry_id=entry_id,
            into="tmp/_handoff/collected/custom.yaml",
            now=FIXED_NOW,
            runner=git,
        )
        self.assertEqual(outcome.collected_to, "tmp/_handoff/collected/custom.yaml")
        self.assertEqual(
            (self.root / "tmp/_handoff/collected/custom.yaml").read_bytes(), HANDOFF_BODY
        )

    def test_destination_collision_is_refused_and_nothing_is_released(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        dest = (
            self.root
            / f"tmp/_handoff/collected/{entry_id}--issue-implementer--issue-354-pr2.yaml"
        )
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"previous round\n")
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "COLLECT_DEST_EXISTS")
        # 既存の回収物は上書きされない（消さない）。解放段にも到達していない。
        self.assertEqual(dest.read_bytes(), b"previous round\n")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue((self.root / WT_REL).is_dir())

    def test_missing_handoff_refuses_and_does_not_release(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree(handoff=None)
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "COLLECT_HANDOFF_MISSING")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue((self.root / WT_REL).is_dir())

    def test_allow_missing_handoff_records_the_reason_and_releases(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree(handoff=None)
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(
            self.root,
            entry_id=entry_id,
            allow_missing_handoff=True,
            reason="agent crashed before writing the handoff",
            now=FIXED_NOW,
            runner=git,
        )
        self.assertIsNone(outcome.collected_to)
        self.assertTrue(outcome.released)
        self.assertEqual(self.status_of(entry_id), "released")
        notes = [item["note"] for item in self.entry(entry_id)["notes"]]
        self.assertIn(
            "collect-worktree --allow-missing-handoff: "
            "agent crashed before writing the handoff",
            notes,
        )

    def test_symlinked_handoff_is_refused_and_nothing_is_released(self):
        entry_id = self.entry_with_status("stale")
        directory = self.make_worktree(handoff=None)
        secret = self.root / "secret.yaml"
        secret.write_bytes(b"not yours\n")
        handoff = directory / HANDOFF_REL
        handoff.parent.mkdir(parents=True)
        os.symlink(secret, handoff)
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "COLLECT_HANDOFF_SYMLINK")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stale")

    def test_oversized_handoff_is_refused_and_nothing_is_released(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree(body=b"x" * 4096)
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(
                self.root, entry_id=entry_id, now=FIXED_NOW, runner=git, max_bytes=1024
            )
        self.assertEqual(ctx.exception.reason, "COLLECT_HANDOFF_TOO_LARGE")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stale")

    def test_sha256_mismatch_does_not_release_and_removes_the_bad_copy(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])

        def tampering_write(dest, data):
            with open(dest, "wb") as handle:
                handle.write(data + b"tampered")

        with patch("gitgate.worktree._write_collected", tampering_write):
            with self.assertRaises(WorktreeError) as ctx:
                collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "COLLECT_VERIFY_MISMATCH")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue((self.root / WT_REL).is_dir())
        # 壊れた回収物は残さない（残すと O_EXCL で再試行が詰む）。
        self.assertFalse(
            (self.root / "tmp/_handoff/collected").exists()
            and any((self.root / "tmp/_handoff/collected").iterdir())
        )

    def test_running_entry_is_refused(self):
        # live な dispatch の worktree を回収も解放もしない（PR-3 の停止段が
        # running から抜けたあとに呼ぶ手続き）。
        entry_id = self.entry_with_status("running")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(self.root, entry_id=entry_id, now=FIXED_NOW, runner=git)
        self.assertEqual(ctx.exception.reason, "WORKTREE_LIVE")
        self.assertEqual(git.removals, [])
        self.assertEqual(self.status_of(entry_id), "running")

    def test_already_collected_entry_skips_to_release(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        outcome = collect_worktree(
            self.root, entry_id=entry_id, now=FIXED_NOW, runner=git
        )
        self.assertTrue(outcome.released)
        self.assertEqual(self.status_of(entry_id), "released")
        # 段2〜5 はスキップされる＝回収先には何も書かれない。
        self.assertFalse((self.root / "tmp/_handoff/collected").exists())

    def test_already_released_entry_is_a_no_op(self):
        entry_id = self.entry_with_status("collected")
        worktree_ledger.mark(self.root, entry_id, "released", now=FIXED_NOW)
        git = FakeGit(self.root, linked=[])
        outcome = collect_worktree(
            self.root, entry_id=entry_id, now=FIXED_NOW, runner=git
        )
        self.assertFalse(outcome.released)
        self.assertEqual(git.calls, [])
        self.assertEqual(self.status_of(entry_id), "released")

    def test_handoff_issue_number_must_match_the_entry(self):
        entry_id = self.entry_with_status("stale", issue=354)
        self.make_worktree(handoff="tmp/_handoff/issue-implementer--issue-3541.yaml")
        git = FakeGit(self.root, linked=[WT_REL])
        with self.assertRaises(WorktreeError) as ctx:
            collect_worktree(
                self.root,
                entry_id=entry_id,
                handoff_path="tmp/_handoff/issue-implementer--issue-3541.yaml",
                now=FIXED_NOW,
                runner=git,
            )
        self.assertEqual(ctx.exception.reason, "COLLECT_HANDOFF_ISSUE_MISMATCH")
        self.assertEqual(git.removals, [])

    def test_bad_paths_never_reach_git(self):
        for kwargs in [
            {"worktree_path": "/tmp/evil", "handoff_path": HANDOFF_REL},
            {"worktree_path": "../x", "handoff_path": HANDOFF_REL},
            {"worktree_path": WT_REL, "handoff_path": "/etc/passwd"},
            {"worktree_path": WT_REL, "handoff_path": "tmp/_handoff/../_worktree/x.yaml"},
            {"worktree_path": WT_REL, "handoff_path": "docs/x--issue-1.yaml"},
        ]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(WorktreeError):
                    collect_worktree(
                        self.root, now=FIXED_NOW, runner=ForbiddenGit(), **kwargs
                    )


# ---------------------------------------------------------------------------
# worktree-forget
# ---------------------------------------------------------------------------


class WorktreeForgetTests(LedgerFixture):
    def test_marks_abandoned_without_deleting_the_entry_or_the_worktree(self):
        entry_id = self.entry_with_status("stale")
        self.make_worktree()
        before = len(worktree_ledger.read_ledger(self.root)["entries"])
        entry = worktree_forget(
            self.root, entry_id, reason="worktree が手で消されていて回収不能", now=FIXED_NOW
        )
        self.assertEqual(entry["status"], "abandoned")
        # エントリは消さない（PR8 区分1＝決定履歴の保全）。
        self.assertEqual(len(worktree_ledger.read_ledger(self.root)["entries"]), before)
        self.assertIsNotNone(self.entry(entry_id))
        # worktree も消さない（消すのは worktree-release。責務を混ぜない）。
        self.assertTrue((self.root / WT_REL).is_dir())
        notes = [item["note"] for item in entry["notes"]]
        self.assertIn("worktree-forget: worktree が手で消されていて回収不能", notes)

    def test_reason_is_mandatory(self):
        entry_id = self.entry_with_status("stale")
        for reason in ["", "   ", "\t"]:
            with self.subTest(reason=repr(reason)):
                with self.assertRaises(WorktreeError):
                    worktree_forget(self.root, entry_id, reason=reason, now=FIXED_NOW)
        self.assertEqual(self.status_of(entry_id), "stale")

    def test_unknown_entry_is_rejected(self):
        with self.assertRaises(WorktreeError) as ctx:
            worktree_forget(self.root, "wl-000000000000", reason="x", now=FIXED_NOW)
        self.assertEqual(ctx.exception.reason, "WORKTREE_ENTRY_NOT_FOUND")

    def test_repeating_forget_only_appends_a_note(self):
        entry_id = self.entry_with_status("stale")
        worktree_forget(self.root, entry_id, reason="first", now=FIXED_NOW)
        entry = worktree_forget(self.root, entry_id, reason="second", now=FIXED_NOW)
        self.assertEqual(entry["status"], "abandoned")
        notes = [item["note"] for item in entry["notes"]]
        self.assertIn("worktree-forget: first", notes)
        self.assertIn("worktree-forget (repeat): second", notes)


# ---------------------------------------------------------------------------
# 時刻の扱い（`.claude/rules/04-test-data.md`）
# ---------------------------------------------------------------------------


class NoWallClockReadTests(LedgerFixture):
    def test_module_never_reads_the_wall_clock(self):
        # 時刻を読むのは CLI 境界（gitgate/cli.py の `_now`）だけ。ロジック側に
        # wall clock 読み取りが混ざると、コード変更なしに時間経過でテストが壊れる。
        # 「呼び出しを grep する」のではなく「時計モジュールを import していない」ことを見る
        # ——import が無ければ読みようがない（散文中の `datetime.now()` に反応もしない）。
        source = Path(__file__).resolve().parents[2] / "gitgate" / "worktree.py"
        import_lines = [
            line.strip()
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.startswith(("import ", "from "))
        ]
        for line in import_lines:
            with self.subTest(line=line):
                self.assertNotIn("datetime", line)
                self.assertNotIn("calendar", line)
                self.assertNotEqual(line, "import time")
                self.assertFalse(line.startswith("from time import"))

    def test_injected_now_is_what_lands_in_the_ledger(self):
        entry_id = self.entry_with_status("collected")
        self.make_worktree()
        git = FakeGit(self.root, linked=[WT_REL])
        worktree_release(self.root, WT_REL, now=FIXED_NOW, runner=git)
        entry = self.entry(entry_id)
        self.assertEqual(entry["closed_at"], "2026-08-19T12:00:00Z")
        self.assertEqual(entry["dispatched_at"], "2026-08-19T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
