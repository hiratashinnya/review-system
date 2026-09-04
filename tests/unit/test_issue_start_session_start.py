"""``SessionStart`` フック ``issue_start.session_start`` の単体テスト（Issue #464・F-464-06）。

毎 dispatch の ``issue-start-gate``（``issue_start.gate._finish_deferred_releases``）は
``cleanup_branch_ref=False`` で削除だけを再試行し、``git fetch`` を伴うローカルブランチ ref
掃除をホットパスから外している（対をなす固定は
``tests/unit/test_issue_start_gate.py::DeferredReleaseGateTests
.test_deferred_release_does_not_fetch_or_delete_the_branch_ref``）。ここでは
``SessionStart`` 側——``cleanup_branch_ref=True``（既定）でのフル掃除——を固定する。

**fail-close は弱めない**：このモジュールはベストエフォートで deny を一切しない
（判定・統制は ``issue-start-gate`` 側に残る）。失敗しても ``release_pending`` のまま
持ち越されることを確認する。
"""

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from issue_start import session_start, worktree_ledger

ROOT = Path(__file__).resolve().parents[2]
HOOK_SCRIPT = ROOT / ".claude" / "hooks" / "session-start-worktree-release.sh"
_HAS_GIT = shutil.which("git") is not None
_HAS_BASH = shutil.which("bash") is not None
FIXED_NOW = datetime(2026, 8, 19, 4, 11, 7, tzinfo=timezone.utc)


class FakeGit:
    """`subprocess.run` 互換のスタブ（`git worktree list/remove` のみ実装）。"""

    def __init__(self, root, *, linked=(), remove_stderr=None):
        self.root = Path(root)
        self.linked = list(linked)
        self.remove_stderr = remove_stderr
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "worktree", "list"]:
            blocks = [f"worktree {self.root}\nHEAD {'0' * 40}\nbranch refs/heads/main\n"]
            for rel in self.linked:
                blocks.append(
                    f"worktree {self.root / rel}\nHEAD {'0' * 40}\n"
                    "branch refs/heads/claude/issue-464-fix\n"
                )
            return subprocess.CompletedProcess(argv, 0, "\n".join(blocks) + "\n", "")
        if argv[:3] == ["git", "worktree", "remove"]:
            if self.remove_stderr is not None:
                return subprocess.CompletedProcess(argv, 1, "", self.remove_stderr)
            shutil.rmtree(argv[-1], ignore_errors=True)
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")


class SessionStartWorktreeReleaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def make_worktree(self, name="agent-rp"):
        path = self.root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path

    def entry_at(self, *statuses, agent_id="rp", branch_name="claude/issue-464-fix"):
        self.make_worktree(f"agent-{agent_id}")
        worktree_ledger.open_entry(
            self.root, issue=464, agent_type="issue-implementer", round=None,
            branch_name=branch_name, handoff_path=None, now=FIXED_NOW,
        )
        entry_id = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )
        for status in statuses:
            worktree_ledger.mark(self.root, entry_id, status, now=FIXED_NOW)
        return entry_id

    def status_of(self, entry_id):
        for item in worktree_ledger.read_ledger(self.root)["entries"]:
            if item.get("entry_id") == entry_id:
                return item.get("status")
        return None

    def test_stdout_is_always_silent(self):
        self.entry_at("stopped", "collected", "release_pending")
        git = FakeGit(self.root, linked=[".claude/worktrees/agent-rp"])
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.root, now=FIXED_NOW, runner=git
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "SessionStart は統制しない・出力もしない")

    def test_full_cleanup_deletes_the_worktree_and_the_branch_ref(self):
        entry_id = self.entry_at("stopped", "collected", "release_pending")
        git = FakeGit(self.root, linked=[".claude/worktrees/agent-rp"])
        stdout, stderr = io.StringIO(), io.StringIO()
        session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.root, now=FIXED_NOW, runner=git
        )
        self.assertEqual(self.status_of(entry_id), "released")
        # cleanup_branch_ref は既定 True（フル掃除・F-464-06）——毎 dispatch 経路
        # （cleanup_branch_ref=False）と対をなす。
        fetch_calls = [argv for argv in git.calls if argv[:2] == ["git", "fetch"]]
        self.assertEqual(len(fetch_calls), 1, "フル掃除では git fetch が走る")
        branch_delete_calls = [
            argv for argv in git.calls if argv[:3] == ["git", "branch", "-D"]
        ]
        self.assertEqual(
            branch_delete_calls, [["git", "branch", "-D", "claude/issue-464-fix"]]
        )

    def test_no_deferred_entries_is_a_silent_no_op(self):
        git = FakeGit(self.root, linked=[])
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.root, now=FIXED_NOW, runner=git
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        evidence = json.loads(stderr.getvalue())
        self.assertEqual(evidence["finished"], [])

    def test_repeated_failure_is_best_effort_and_does_not_raise(self):
        """fail-close の代替ではない: 失敗しても release_pending のまま持ち越され、
        issue-start-gate の residue/stale 判定と次 dispatch の deny は従来どおり効く
        （このモジュール自身は deny を一切しない）。"""
        entry_id = self.entry_at("stopped", "collected", "release_pending")
        git = FakeGit(
            self.root, linked=[".claude/worktrees/agent-rp"],
            remove_stderr=(
                "fatal: cannot remove a locked working tree, lock reason: still busy\n"
            ),
        )
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.root, now=FIXED_NOW, runner=git
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.status_of(entry_id), "release_pending")
        evidence = json.loads(stderr.getvalue())
        self.assertFalse(evidence["finished"][0]["released"])
        self.assertEqual(evidence["finished"][0]["error"], "WORKTREE_REMOVE_FAILED")

    def test_unresolvable_repo_root_is_a_silent_no_op(self):
        (self.root / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.root, now=FIXED_NOW,
            runner=FakeGit(self.root),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("REPO_ROOT_UNRESOLVED", stderr.getvalue())


@unittest.skipUnless(_HAS_GIT, "git が無い環境では実 worktree の統合検証をしない")
class SessionStartRealGitIntegrationTests(unittest.TestCase):
    """実 git・実 linked worktree・実 origin での通し検証（Issue #464・F-464-06）。

    毎 dispatch 経路（``issue_start.gate``）が ``release_pending`` にしたエントリの削除と
    branch ref 掃除を、SessionStart がフル掃除として完了させることを固定する。
    """

    def git(self, *args, cwd=None):
        completed = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=str(cwd or self.repo), text=True, capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        # `_cleanup_branch_ref` は fresh fetch した origin を読むため、実物の bare repo を使う。
        self.origin = base / "origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(self.origin)],
            check=True, capture_output=True, text=True,
        )
        self.repo = base / "repo"
        subprocess.run(
            ["git", "clone", "-q", str(self.origin), str(self.repo)],
            check=True, capture_output=True, text=True,
        )
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "init")
        self.git("push", "-q", "origin", "main")
        self.worktree_rel = ".claude/worktrees/agent-ss01"
        self.branch = "claude/issue-464-session-start-it"
        (self.repo / ".claude" / "worktrees").mkdir(parents=True)
        self.git("worktree", "add", "-q", "-b", self.branch, self.worktree_rel, "main")
        worktree_dir = self.repo / self.worktree_rel
        (worktree_dir / "note.txt").write_text("work\n", encoding="utf-8")
        self.git("add", "note.txt", cwd=worktree_dir)
        self.git("commit", "-qm", "work", cwd=worktree_dir)
        self.git("push", "-q", "origin", self.branch, cwd=worktree_dir)

        worktree_ledger.open_entry(
            self.repo, issue=464, agent_type="issue-implementer", round=None,
            branch_name=self.branch, handoff_path=None, now=FIXED_NOW,
        )
        self.entry_id = worktree_ledger.bind_agent(
            self.repo, agent_type="issue-implementer", agent_id="ss01",
            worktree_path=self.worktree_rel,
        )
        for status in ("stopped", "collected", "release_pending"):
            worktree_ledger.mark(self.repo, self.entry_id, status, now=FIXED_NOW)

    def _local_ref_oid(self):
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{self.branch}"],
            cwd=str(self.repo), text=True, capture_output=True,
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    def entry(self):
        return worktree_ledger.find_by_agent_id(self.repo, "ss01")

    def test_session_start_finishes_the_release_and_cleans_up_the_branch_ref(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = session_start.run(
            stdout=stdout, stderr=stderr, cwd=self.repo, now=FIXED_NOW, runner=subprocess.run
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "SessionStart は停止も deny もしない")
        self.assertEqual(self.entry()["status"], "released")
        self.assertFalse((self.repo / self.worktree_rel).exists())
        self.assertIsNone(
            self._local_ref_oid(), "SessionStart はフル掃除でローカルブランチ ref も消す"
        )


@unittest.skipUnless(_HAS_BASH, "bash が無い環境ではフック起動口を検証しない")
class LauncherWiringTests(unittest.TestCase):
    """``.sh`` 起動口の存在と ``issue_start.session_start`` への配線だけを確認する。

    **実リポジトリの台帳には触れない**：`.claude/hooks/*.sh` は
    `cd "$CLAUDE_PROJECT_DIR"` してから起動するため（F-309-01・cwd 非依存の共通作法）、
    `CLAUDE_PROJECT_DIR` を実 ROOT に向けると実際の worktree 台帳を読みにいく
    （他の launcher テストは対象外 payload で早期 return する経路しか踏まないため無害だが、
    このモジュールに「対象外」の概念は無い）。したがって、ここでは実行はせず
    ``python3 -c`` 相当の import 可能性だけをモジュール直import で検証する
    （launcher の cwd 非依存起動作法そのものは他フックの ``LauncherWiringTests`` が
    既に固定済みで、起動作法は同一テンプレートを踏襲しているため重複検証しない）。
    """

    def test_launcher_script_exists_and_delegates_to_the_module(self):
        self.assertTrue(HOOK_SCRIPT.is_file())
        body = HOOK_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("python3 -m issue_start.session_start", body)
        self.assertIn('cd "$PROJECT_ROOT"', body)
        self.assertIn("PYTHONSAFEPATH", body)

    def test_module_is_importable_and_exposes_main(self):
        self.assertTrue(callable(session_start.main))
        self.assertTrue(callable(session_start.run))


if __name__ == "__main__":
    unittest.main()
