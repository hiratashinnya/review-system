"""Issue #309（PR-1）worktree 所有台帳の単体テスト。

本 PR のスコープは**記録だけ**である（削除経路を1つも持たない）ことを、
`tests/unit/test_subagent_hooks.py` の静的検査と合わせて固定する。

時刻の扱い（`.claude/rules/04-test-data.md`）: 台帳モジュールは `now` を必須引数で受け取り、
内部で wall clock を読まない。本ファイルの固定日時は wall clock と比較されない
（TTL・経過時間による判定が台帳に存在しない）ため、時間経過で反転する比較が構造的に無い。
その不変条件自体を :meth:`ClockDisciplineTests` が機械的に検査する。
"""

import ast
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from issue_start import worktree_ledger
from issue_start.worktree_ledger import LedgerError


FIXED_NOW = datetime(2026, 8, 19, 4, 11, 7, tzinfo=timezone.utc)
LATER = FIXED_NOW + timedelta(minutes=5)


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def open_entry(self, *, issue=354, agent_type="issue-implementer", branch_name="claude/x"):
        return worktree_ledger.open_entry(
            self.root,
            issue=issue,
            agent_type=agent_type,
            round=None,
            branch_name=branch_name,
            handoff_path=None,
            now=FIXED_NOW,
        )

    def entries(self):
        return worktree_ledger.read_ledger(self.root)["entries"]

    def make_worktree(self, name):
        path = self.root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path


class ReadLedgerTests(LedgerTestCase):
    def test_missing_ledger_is_the_normal_initial_state(self):
        # `tmp/` ごと無い状態は「まだ dispatch していない」＝正常。エラーにしない。
        document = worktree_ledger.read_ledger(self.root)
        self.assertEqual(
            document, {"schema_version": worktree_ledger.SCHEMA_VERSION, "entries": []}
        )
        self.assertFalse((self.root / "tmp").exists(), "read だけで tmp/ を作らない")

    def test_broken_json_and_schema_mismatch_fail_close(self):
        path = worktree_ledger.ledger_path(self.root, create_dir=True)
        cases = [
            ("{not json", "LEDGER_INVALID_JSON"),
            (json.dumps([]), "LEDGER_CORRUPT"),
            (json.dumps({"schema_version": "worktree-ledger/0", "entries": []}),
             "LEDGER_SCHEMA_MISMATCH"),
            (json.dumps({"schema_version": worktree_ledger.SCHEMA_VERSION, "entries": {}}),
             "LEDGER_CORRUPT"),
            (json.dumps({"schema_version": worktree_ledger.SCHEMA_VERSION, "entries": ["x"]}),
             "LEDGER_CORRUPT"),
        ]
        for raw, reason in cases:
            path.write_text(raw, encoding="utf-8")
            with self.subTest(reason=reason):
                with self.assertRaises(LedgerError) as ctx:
                    worktree_ledger.read_ledger(self.root)
                self.assertEqual(ctx.exception.reason, reason)

    def test_symlinked_places_are_refused(self):
        elsewhere = self.root / "escape-target"
        elsewhere.mkdir()
        (self.root / "tmp").symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.read_ledger(self.root)
        self.assertEqual(ctx.exception.reason, "LEDGER_TMP_SYMLINK")


class OpenEntryTests(LedgerTestCase):
    def test_open_entry_records_the_full_schema(self):
        entry_id = self.open_entry(issue=354, branch_name="claude/issue-354-x")
        entries = self.entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], {
            "entry_id": entry_id,
            "issue": 354,
            "agent_type": "issue-implementer",
            "round": None,
            "branch_name": "claude/issue-354-x",
            "handoff_path": None,
            "dispatched_at": "2026-08-19T04:11:07Z",
            "agent_id": None,
            "worktree_path": None,
            "status": "open",
            "collected_to": None,
            "closed_at": None,
            "notes": [],
        })
        self.assertRegex(entry_id, r"^wl-[0-9a-f]{12}$")

    def test_entry_ids_are_unique_across_dispatches(self):
        ids = {self.open_entry() for _ in range(5)}
        self.assertEqual(len(ids), 5)

    def test_invalid_binding_values_fail_close_without_writing(self):
        cases = [
            ({"issue": 0}, "LEDGER_ISSUE_INVALID"),
            ({"issue": True}, "LEDGER_ISSUE_INVALID"),
            ({"agent_type": "bad type"}, "LEDGER_AGENT_TYPE_INVALID"),
            ({"round": 0}, "LEDGER_ROUND_INVALID"),
            ({"branch_name": 3}, "LEDGER_BRANCH_INVALID"),
            ({"handoff_path": 3}, "LEDGER_HANDOFF_PATH_INVALID"),
        ]
        for override, reason in cases:
            kwargs = {
                "issue": 1, "agent_type": "issue-fixer", "round": None,
                "branch_name": None, "handoff_path": None, "now": FIXED_NOW,
            }
            kwargs.update(override)
            with self.subTest(reason=reason):
                with self.assertRaises(LedgerError) as ctx:
                    worktree_ledger.open_entry(self.root, **kwargs)
                self.assertEqual(ctx.exception.reason, reason)
        self.assertEqual(self.entries(), [])


class TransitionTests(LedgerTestCase):
    def test_forward_transitions_are_allowed(self):
        entry_id = self.open_entry()
        for status in ("running", "stopped", "collected", "released"):
            worktree_ledger.mark(self.root, entry_id, status, now=LATER)
            self.assertEqual(self.entries()[0]["status"], status)
        self.assertEqual(self.entries()[0]["closed_at"], "2026-08-19T04:16:07Z")

    def test_running_cannot_jump_straight_to_collected(self):
        # `collected` を作るのは `collect-worktree` 自身なので、`running` から直行できると
        # 「回収する前に回収済みにする」しか回収を始める手が無くなる（Issue #354 F-354-01）。
        entry_id = self.open_entry()
        worktree_ledger.mark(self.root, entry_id, "running", now=LATER)
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.mark(self.root, entry_id, "collected", now=LATER)
        self.assertEqual(ctx.exception.reason, "LEDGER_ILLEGAL_TRANSITION")
        self.assertEqual(self.entries()[0]["status"], "running")

    def test_stopped_is_the_route_from_running_to_collection(self):
        # `SubagentStop` が「所有者の停止を確認した」事実を記録する中間状態。
        entry_id = self.open_entry()
        worktree_ledger.mark(self.root, entry_id, "running", now=LATER)
        worktree_ledger.mark(self.root, entry_id, "stopped", now=LATER, note="所有者停止を確認")
        self.assertEqual(self.entries()[0]["status"], "stopped")
        self.assertEqual(self.entries()[0]["notes"][-1]["note"], "所有者停止を確認")
        # `stopped` は未解放（＝残留として数える）。
        self.assertIn("stopped", worktree_ledger.UNRELEASED_STATUSES)
        self.assertEqual(
            [item["entry_id"] for item in worktree_ledger.unreleased_entries(self.root)],
            [entry_id],
        )
        worktree_ledger.mark(self.root, entry_id, "collected", now=LATER)
        self.assertEqual(self.entries()[0]["status"], "collected")

    def test_stopped_cannot_go_back_to_running(self):
        entry_id = self.open_entry()
        for status in ("running", "stopped"):
            worktree_ledger.mark(self.root, entry_id, status, now=LATER)
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.mark(self.root, entry_id, "running", now=LATER)
        self.assertEqual(ctx.exception.reason, "LEDGER_ILLEGAL_TRANSITION")
        self.assertEqual(self.entries()[0]["status"], "stopped")

    def test_same_status_is_an_idempotent_no_op(self):
        entry_id = self.open_entry()
        worktree_ledger.mark(self.root, entry_id, "running", now=LATER)
        worktree_ledger.mark(self.root, entry_id, "running", now=LATER)
        self.assertEqual(self.entries()[0]["status"], "running")
        self.assertEqual(self.entries()[0]["notes"], [])

    def test_backward_transitions_are_refused(self):
        entry_id = self.open_entry()
        for status in ("running", "stopped", "collected", "released"):
            worktree_ledger.mark(self.root, entry_id, status, now=LATER)
        for status in ("open", "running", "stopped", "collected", "stale"):
            with self.subTest(status=status):
                with self.assertRaises(LedgerError) as ctx:
                    worktree_ledger.mark(self.root, entry_id, status, now=LATER)
                self.assertEqual(ctx.exception.reason, "LEDGER_ILLEGAL_TRANSITION")
        self.assertEqual(self.entries()[0]["status"], "released")

    def test_abandoned_is_reachable_from_every_non_terminal_state(self):
        # `worktree-forget --reason` は deny が恒久的にパイプラインを止めるのを防ぐ
        # 唯一の逃げ道なので、状態で塞がない。
        for status in ("open", "running", "stopped", "collected", "stale"):
            with self.subTest(status=status):
                entry_id = self.open_entry()
                if status != "open":
                    path = {"running": ["running"],
                            "stopped": ["running", "stopped"],
                            "collected": ["running", "stopped", "collected"],
                            "stale": ["running", "stale"]}[status]
                    for step in path:
                        worktree_ledger.mark(self.root, entry_id, step, now=LATER)
                worktree_ledger.mark(
                    self.root, entry_id, "abandoned", now=LATER, note="回収不能・原因不明"
                )
                entry = [e for e in self.entries() if e["entry_id"] == entry_id][0]
                self.assertEqual(entry["status"], "abandoned")
                self.assertEqual(entry["notes"][-1]["note"], "回収不能・原因不明")

    def test_notes_accumulate_and_are_never_dropped(self):
        entry_id = self.open_entry()
        worktree_ledger.add_note(self.root, entry_id, now=FIXED_NOW, note="1つめ")
        worktree_ledger.mark(self.root, entry_id, "stale", now=LATER, note="2つめ")
        notes = self.entries()[0]["notes"]
        self.assertEqual([item["note"] for item in notes], ["1つめ", "2つめ"])
        self.assertEqual(notes[0]["at"], "2026-08-19T04:11:07Z")

    def test_unknown_entry_and_status_fail_close(self):
        entry_id = self.open_entry()
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.mark(self.root, "wl-000000000000", "running", now=LATER)
        self.assertEqual(ctx.exception.reason, "LEDGER_ENTRY_NOT_FOUND")
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.mark(self.root, entry_id, "deleted", now=LATER)
        self.assertEqual(ctx.exception.reason, "LEDGER_STATUS_UNKNOWN")

    def test_entries_are_never_removed(self):
        first = self.open_entry()
        second = self.open_entry(agent_type="issue-fixer")
        worktree_ledger.mark(self.root, first, "abandoned", now=LATER, note="理由")
        self.assertEqual([item["entry_id"] for item in self.entries()], [first, second])


class UpdateLedgerAtomicityTests(LedgerTestCase):
    def test_lock_held_by_another_writer_times_out_fail_close(self):
        directory = worktree_ledger.ledger_dir(self.root, create=True)
        lock = directory / worktree_ledger.LEDGER_LOCK_FILENAME
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        self.addCleanup(lambda: os.close(fd))
        slept = []
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.update_ledger(
                self.root,
                lambda document: document["entries"].append({"entry_id": "wl-x"}),
                lock_timeout_s=0.2,
                sleep=slept.append,
            )
        self.assertEqual(ctx.exception.reason, "LEDGER_LOCK_TIMEOUT")
        # 実時間を待たずに（sleep を注入して）リトライしていること。
        self.assertEqual(slept, [worktree_ledger.LOCK_RETRY_INTERVAL_S] * 3)
        self.assertEqual(self.entries(), [], "タイムアウト時に部分書込を残さない")

    def test_lock_is_released_after_a_successful_update(self):
        self.open_entry()
        directory = worktree_ledger.ledger_dir(self.root)
        self.assertFalse((directory / worktree_ledger.LEDGER_LOCK_FILENAME).exists())
        self.assertFalse((directory / worktree_ledger.LEDGER_TMP_FILENAME).exists())

    def test_mutate_failure_writes_nothing_and_releases_the_lock(self):
        self.open_entry()
        def boom(document):
            document["entries"].clear()
            raise RuntimeError("mutate failed")
        with self.assertRaises(RuntimeError):
            worktree_ledger.update_ledger(self.root, boom)
        self.assertEqual(len(self.entries()), 1)
        directory = worktree_ledger.ledger_dir(self.root)
        self.assertFalse((directory / worktree_ledger.LEDGER_LOCK_FILENAME).exists())

    def test_mutate_producing_a_broken_document_is_refused(self):
        self.open_entry()
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.update_ledger(
                self.root, lambda document: document.update({"entries": "nope"})
            )
        self.assertEqual(ctx.exception.reason, "LEDGER_CORRUPT")
        self.assertEqual(len(self.entries()), 1)


class ClockDisciplineTests(unittest.TestCase):
    """`.claude/rules/04-test-data.md`: 台帳モジュールは wall clock を読まない。"""

    @staticmethod
    def _clock_calls(module):
        tree = ast.parse(inspect.getsource(module))
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                pair = (func.value.id, func.attr)
                if pair in (("datetime", "now"), ("datetime", "utcnow"), ("time", "time")):
                    found.append(f"{pair[0]}.{pair[1]}()")
        return found

    def test_module_never_reads_the_wall_clock(self):
        self.assertEqual(self._clock_calls(worktree_ledger), [])

    def test_now_is_a_required_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaises(TypeError):
                worktree_ledger.open_entry(
                    root, issue=1, agent_type="issue-fixer", round=None,
                    branch_name=None, handoff_path=None,
                )
            entry_id = worktree_ledger.open_entry(
                root, issue=1, agent_type="issue-fixer", round=None,
                branch_name=None, handoff_path=None, now=FIXED_NOW,
            )
            with self.assertRaises(TypeError):
                worktree_ledger.mark(root, entry_id, "running")

    def test_non_datetime_now_fails_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LedgerError) as ctx:
                worktree_ledger.open_entry(
                    Path(tmp).resolve(), issue=1, agent_type="issue-fixer", round=None,
                    branch_name=None, handoff_path=None, now="2026-08-19T04:11:07Z",
                )
            self.assertEqual(ctx.exception.reason, "LEDGER_NOW_REQUIRED")

    def test_naive_datetime_is_stamped_as_utc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            worktree_ledger.open_entry(
                root, issue=1, agent_type="issue-fixer", round=None,
                branch_name=None, handoff_path=None,
                now=datetime(2026, 8, 19, 4, 11, 7),
            )
            entries = worktree_ledger.read_ledger(root)["entries"]
            self.assertEqual(entries[0]["dispatched_at"], "2026-08-19T04:11:07Z")


class BindAgentTests(LedgerTestCase):
    def test_bind_attaches_to_the_latest_open_entry_of_the_same_role(self):
        older = self.open_entry(issue=100)
        newer = self.open_entry(issue=101)
        other_role = self.open_entry(issue=102, agent_type="issue-fixer")
        entry_id = worktree_ledger.bind_agent(
            self.root,
            agent_type="issue-implementer",
            agent_id="a14df44b",
            worktree_path=".claude/worktrees/agent-a14df44b",
        )
        self.assertEqual(entry_id, newer)
        by_id = {item["entry_id"]: item for item in self.entries()}
        self.assertEqual(by_id[newer]["status"], "running")
        self.assertEqual(by_id[newer]["agent_id"], "a14df44b")
        self.assertEqual(by_id[newer]["worktree_path"], ".claude/worktrees/agent-a14df44b")
        self.assertEqual(by_id[older]["status"], "open")
        self.assertEqual(by_id[other_role]["status"], "open")

    def test_bind_without_a_matching_open_entry_returns_none_and_guesses_nothing(self):
        running = self.open_entry()
        worktree_ledger.mark(self.root, running, "running", now=LATER)
        self.assertIsNone(
            worktree_ledger.bind_agent(
                self.root,
                agent_type="issue-implementer",
                agent_id="deadbeef",
                worktree_path=".claude/worktrees/agent-deadbeef",
            )
        )
        entry = self.entries()[0]
        self.assertIsNone(entry["agent_id"], "既存 running を上書きしない")
        self.assertIsNone(entry["worktree_path"])

    def test_bind_is_idempotent_for_a_repeated_subagent_start(self):
        self.open_entry()
        first = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="abc",
            worktree_path=".claude/worktrees/agent-abc",
        )
        second = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="abc",
            worktree_path=".claude/worktrees/agent-abc",
        )
        self.assertEqual(first, second)
        self.assertEqual(len(self.entries()), 1)

    def test_malformed_agent_id_or_worktree_path_fails_close(self):
        self.open_entry()
        bad_paths = [
            "/abs/.claude/worktrees/agent-x",
            ".claude/worktrees/../../etc",
            ".claude/worktrees/agent-x/sub",
            ".claude/worktrees/notagent",
            "agent-x",
        ]
        for path in bad_paths:
            with self.subTest(path=path):
                with self.assertRaises(LedgerError) as ctx:
                    worktree_ledger.bind_agent(
                        self.root, agent_type="issue-implementer",
                        agent_id="abc", worktree_path=path,
                    )
                self.assertEqual(ctx.exception.reason, "LEDGER_WORKTREE_PATH_INVALID")
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.bind_agent(
                self.root, agent_type="issue-implementer",
                agent_id="bad id", worktree_path=".claude/worktrees/agent-abc",
            )
        self.assertEqual(ctx.exception.reason, "LEDGER_AGENT_ID_INVALID")

    def test_find_by_agent_id(self):
        self.open_entry()
        entry_id = worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="abc",
            worktree_path=".claude/worktrees/agent-abc",
        )
        self.assertEqual(worktree_ledger.find_by_agent_id(self.root, "abc")["entry_id"], entry_id)
        self.assertIsNone(worktree_ledger.find_by_agent_id(self.root, "zzz"))


class OnDiskWorktreeTests(LedgerTestCase):
    def test_only_real_agent_directories_are_reported(self):
        self.make_worktree("agent-a14df44b4e4136a73")
        self.make_worktree("foo")
        (self.root / ".claude" / "worktrees" / ".ledger").mkdir()
        (self.root / ".claude" / "worktrees" / "agent-file").write_text("x", encoding="utf-8")
        (self.root / ".claude" / "worktrees" / "agent-link").symlink_to(
            self.root / ".claude" / "worktrees" / "agent-a14df44b4e4136a73",
            target_is_directory=True,
        )
        self.assertEqual(
            worktree_ledger.on_disk_worktrees(self.root),
            [".claude/worktrees/agent-a14df44b4e4136a73"],
        )

    def test_missing_or_symlinked_worktree_root_reports_nothing(self):
        self.assertEqual(worktree_ledger.on_disk_worktrees(self.root), [])
        target = self.root / "elsewhere"
        target.mkdir()
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "worktrees").symlink_to(target, target_is_directory=True)
        self.assertEqual(worktree_ledger.on_disk_worktrees(self.root), [])


class ResolveWorktreeTests(LedgerTestCase):
    def test_direct_agent_id_match_wins(self):
        self.make_worktree("agent-abc")
        self.make_worktree("agent-def")
        self.assertEqual(
            worktree_ledger.resolve_worktree_for_agent(self.root, agent_id="def"),
            (".claude/worktrees/agent-def", "agent_id"),
        )

    def test_diff_detection_binds_the_single_new_worktree(self):
        # 選択肢 BIND-1 案A: `running` が1件も無い状態で唯一出現した worktree なら一意。
        self.make_worktree("agent-abc")
        self.assertEqual(
            worktree_ledger.resolve_worktree_for_agent(self.root, agent_id="mismatched-id"),
            (".claude/worktrees/agent-abc", "diff"),
        )

    def test_diff_detection_refuses_when_a_running_dispatch_exists(self):
        self.make_worktree("agent-abc")
        self.make_worktree("agent-live")
        entry_id = self.open_entry()
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="live",
            worktree_path=".claude/worktrees/agent-live",
        )
        self.assertEqual(self.entries()[0]["entry_id"], entry_id)
        self.assertEqual(
            worktree_ledger.resolve_worktree_for_agent(self.root, agent_id=None),
            (None, "ambiguous-running"),
        )

    def test_no_candidate_cases_return_none(self):
        self.assertEqual(
            worktree_ledger.resolve_worktree_for_agent(self.root, agent_id="abc"),
            (None, "no-worktree"),
        )
        self.make_worktree("agent-abc")
        self.make_worktree("agent-def")
        self.assertEqual(
            worktree_ledger.resolve_worktree_for_agent(self.root, agent_id=None),
            (None, "no-unique-candidate"),
        )


class ResidueReportTests(LedgerTestCase):
    def test_report_separates_running_stale_and_unclaimed(self):
        self.make_worktree("agent-live")
        self.make_worktree("agent-orphan")
        live = self.open_entry(issue=1)
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="live",
            worktree_path=".claude/worktrees/agent-live",
        )
        stale = self.open_entry(issue=2)
        worktree_ledger.mark(self.root, stale, "stale", now=LATER)
        stopped = self.open_entry(issue=3)
        worktree_ledger.mark(self.root, stopped, "running", now=LATER)
        worktree_ledger.mark(self.root, stopped, "stopped", now=LATER)
        report = worktree_ledger.residue_report(self.root)
        self.assertEqual(report["running"], [".claude/worktrees/agent-live"])
        self.assertEqual(report["unclaimed"], [".claude/worktrees/agent-orphan"])
        # `stopped`＝所有者は停止したが未回収なので、残留として数える。
        self.assertEqual(
            [item["entry_id"] for item in report["stale"]], [stale, stopped]
        )
        self.assertNotIn(live, [item["entry_id"] for item in report["stale"]])

    def test_stopped_is_claimed_and_residue_at_the_same_time(self):
        """`stopped` の二重の性質（Issue #354・PR-3）を境界条件として固定する。

        * **claimed**（回収処理中の占有は正当）＝ `unclaimed` に出さない。ここを漏らすと
          `SubagentStop` が停止を記録してから `collect-worktree` が終わるまでの短い区間に
          走った dispatch が、回収中の worktree を孤児と誤診して
          `--force-uncollected` の掃除を促してしまう。
        * **residue**（回収がまだ完了していない）＝ `stale` に出す。ここを漏らすと
          「回収段が失敗して stopped のまま残った」状態に誰も気づかない。
        """
        self.make_worktree("agent-stopping")
        entry_id = self.open_entry(issue=354)
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="stopping",
            worktree_path=".claude/worktrees/agent-stopping",
        )
        worktree_ledger.mark(self.root, entry_id, "stopped", now=LATER)
        report = worktree_ledger.residue_report(self.root)
        self.assertEqual(report["stopped"], [".claude/worktrees/agent-stopping"])
        self.assertEqual(report["claimed"], [".claude/worktrees/agent-stopping"])
        self.assertEqual(report["running"], [], "stopped は running ではない")
        self.assertEqual(report["unclaimed"], [], "回収処理中の worktree は孤児ではない")
        self.assertEqual([item["entry_id"] for item in report["stale"]], [entry_id])

    def test_collected_is_residue_because_it_is_not_released_yet(self):
        self.make_worktree("agent-c")
        entry_id = self.open_entry(issue=354)
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="c",
            worktree_path=".claude/worktrees/agent-c",
        )
        for status in ("stopped", "collected"):
            worktree_ledger.mark(self.root, entry_id, status, now=LATER)
        report = worktree_ledger.residue_report(self.root)
        self.assertEqual([item["entry_id"] for item in report["stale"]], [entry_id])
        # `collected` は claimed ではない（回収は終わっている＝解放だけが残っている）。
        self.assertEqual(report["claimed"], [])
        self.assertEqual(report["unclaimed"], [".claude/worktrees/agent-c"])

    def test_released_entry_leaves_no_residue(self):
        entry_id = self.open_entry(issue=354)
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="r",
            worktree_path=".claude/worktrees/agent-r",
        )
        for status in ("stopped", "collected", "released"):
            worktree_ledger.mark(self.root, entry_id, status, now=LATER)
        report = worktree_ledger.residue_report(self.root)
        self.assertEqual(report["stale"], [])
        self.assertEqual(report["unclaimed"], [])
        self.assertEqual(report["claimed"], [])

    def test_unreleased_entries_exclude_terminal_states(self):
        released = self.open_entry(issue=1)
        for status in ("running", "stopped", "collected", "released"):
            worktree_ledger.mark(self.root, released, status, now=LATER)
        still_open = self.open_entry(issue=2)
        self.assertEqual(
            [item["entry_id"] for item in worktree_ledger.unreleased_entries(self.root)],
            [still_open],
        )


class SweepOrphansTests(LedgerTestCase):
    """`sweep_orphans`（Issue #354・PR-3）: 占有の主張と実在の突き合わせ。

    判定入力は**状態と実在だけ**（時刻は notes のスタンプにしか使わない）ので、
    時間経過でテストが反転する比較が構造的に無い（`.claude/rules/04-test-data.md`）。
    """

    def bound(self, *, agent_id, issue=354, agent_type="issue-implementer"):
        self.open_entry(issue=issue, agent_type=agent_type)
        return worktree_ledger.bind_agent(
            self.root, agent_type=agent_type, agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )

    def status_of(self, entry_id):
        return {item["entry_id"]: item for item in self.entries()}[entry_id]["status"]

    def test_running_entry_without_a_worktree_on_disk_becomes_stale(self):
        entry_id = self.bound(agent_id="gone")
        self.assertEqual(
            worktree_ledger.sweep_orphans(self.root, now=LATER), [entry_id]
        )
        self.assertEqual(self.status_of(entry_id), "stale")
        note = self.entries()[0]["notes"][-1]
        self.assertIn("sweep-orphans", note["note"])
        self.assertEqual(note["at"], "2026-08-19T04:16:07Z")

    def test_stopped_entry_without_a_worktree_on_disk_becomes_stale(self):
        entry_id = self.bound(agent_id="gone")
        worktree_ledger.mark(self.root, entry_id, "stopped", now=LATER)
        self.assertEqual(
            worktree_ledger.sweep_orphans(self.root, now=LATER), [entry_id]
        )
        self.assertEqual(self.status_of(entry_id), "stale")

    def test_claimed_entries_with_a_live_worktree_are_left_alone(self):
        self.make_worktree("agent-live")
        self.make_worktree("agent-stopping")
        running = self.bound(agent_id="live", issue=1)
        stopping = self.bound(agent_id="stopping", issue=2)
        worktree_ledger.mark(self.root, stopping, "stopped", now=LATER)
        self.assertEqual(worktree_ledger.sweep_orphans(self.root, now=LATER), [])
        self.assertEqual(self.status_of(running), "running")
        self.assertEqual(self.status_of(stopping), "stopped")

    def test_open_entries_are_never_swept(self):
        """`open` は掃引しない——live な dispatch と取り残しを状態だけでは区別できない。

        区別には経過時間が要るが、台帳は TTL 判定を1つも持たない（持たせない）。
        `open` を落とすと、まさに今起動した dispatch のエントリを `stale`＝強制解放の
        対象へ落としうる。
        """
        entry_id = self.open_entry()
        self.assertEqual(worktree_ledger.sweep_orphans(self.root, now=LATER), [])
        self.assertEqual(self.status_of(entry_id), "open")

    def test_terminal_entries_are_never_swept(self):
        released = self.bound(agent_id="a", issue=1)
        for status in ("stopped", "collected", "released"):
            worktree_ledger.mark(self.root, released, status, now=LATER)
        abandoned = self.bound(agent_id="b", issue=2)
        worktree_ledger.mark(self.root, abandoned, "abandoned", now=LATER)
        self.assertEqual(worktree_ledger.sweep_orphans(self.root, now=LATER), [])
        self.assertEqual(self.status_of(released), "released")
        self.assertEqual(self.status_of(abandoned), "abandoned")

    def test_sweep_is_idempotent(self):
        entry_id = self.bound(agent_id="gone")
        worktree_ledger.sweep_orphans(self.root, now=LATER)
        self.assertEqual(worktree_ledger.sweep_orphans(self.root, now=LATER), [])
        self.assertEqual(len(self.entries()[0]["notes"]), 1, "notes を二重に積まない")

    def test_nothing_to_sweep_does_not_touch_the_ledger_file(self):
        """正常系（掃引対象ゼロ）では台帳ファイルを作らない・触らない。

        gate は**全 dispatch** の直前にこれを呼ぶので、毎回書き込むと掃引そのものが
        新たな失敗要因（ロック競合・書込エラー）になる。
        """
        self.assertEqual(worktree_ledger.sweep_orphans(self.root, now=LATER), [])
        self.assertFalse((self.root / "tmp").exists())

    def test_sweep_does_not_delete_anything_on_disk(self):
        """掃引は状態を進めるだけ——実体の削除経路をこのモジュールは持たない。"""
        self.make_worktree("agent-other")
        entry_id = self.bound(agent_id="gone")
        worktree_ledger.sweep_orphans(self.root, now=LATER)
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-other").is_dir())
        self.assertEqual(len(self.entries()), 1)
        self.assertEqual(self.status_of(entry_id), "stale", "エントリも削除しない")


class MainWorktreeRootTests(unittest.TestCase):
    """linked worktree から呼んでも main worktree の台帳へ収束する（K-01 と同等の導出）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.main = Path(self._tmp.name).resolve() / "main"
        (self.main / ".git" / "worktrees" / "agent-abc").mkdir(parents=True)

    def _linked(self, *, with_commondir):
        linked = self.main / ".claude" / "worktrees" / "agent-abc"
        linked.mkdir(parents=True)
        gitdir = self.main / ".git" / "worktrees" / "agent-abc"
        (linked / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
        if with_commondir:
            (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        return linked

    def test_main_worktree_is_itself(self):
        self.assertEqual(worktree_ledger.main_worktree_root(self.main), self.main)

    def test_linked_worktree_converges_via_commondir(self):
        linked = self._linked(with_commondir=True)
        self.assertEqual(worktree_ledger.main_worktree_root(linked), self.main)

    def test_linked_worktree_converges_via_layout_fallback(self):
        linked = self._linked(with_commondir=False)
        self.assertEqual(worktree_ledger.main_worktree_root(linked), self.main)

    def test_plain_directory_without_git_is_returned_as_is(self):
        plain = Path(self._tmp.name).resolve() / "plain"
        plain.mkdir()
        self.assertEqual(worktree_ledger.main_worktree_root(plain), plain)

    def test_malformed_git_file_fails_close(self):
        broken = Path(self._tmp.name).resolve() / "broken"
        broken.mkdir()
        (broken / ".git").write_text("not-a-gitdir-line\n", encoding="utf-8")
        with self.assertRaises(LedgerError) as ctx:
            worktree_ledger.main_worktree_root(broken)
        self.assertEqual(ctx.exception.reason, "LEDGER_GIT_FILE_INVALID")

    def test_ledger_of_a_linked_worktree_lands_in_the_main_worktree(self):
        linked = self._linked(with_commondir=True)
        root = worktree_ledger.main_worktree_root(linked)
        worktree_ledger.open_entry(
            root, issue=309, agent_type="issue-implementer", round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )
        self.assertTrue((self.main / "tmp" / "_worktree" / "ledger.json").is_file())
        self.assertFalse((linked / "tmp").exists(), "linked worktree 側に台帳が分裂しない")


if __name__ == "__main__":
    unittest.main()
