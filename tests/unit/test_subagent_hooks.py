"""Issue #309（PR-1）SubagentStart / SubagentStop フックの単体テスト。

本 PR の最重要の不変条件は「**worktree を1つも削除しない**」こと。
:class:`NoDeletionPathTests` が、出荷コードに削除経路が存在しないことと、
フックが起動するサブプロセスに `git worktree remove` が一度も現れないことを機械的に固定する。
"""

import ast
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from issue_start import subagent_hooks, worktree_ledger


ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = ROOT / ".claude" / "hooks"
HOOK_SCRIPTS = {
    "karte-inject": HOOK_DIR / "subagent-karte-inject.sh",
    "bind": HOOK_DIR / "subagent-worktree-bind.sh",
    "stop": HOOK_DIR / "subagent-stop-gate.sh",
}
SHIPPED_MODULES = [
    ROOT / "issue_start" / "subagent_hooks.py",
    ROOT / "issue_start" / "worktree_ledger.py",
    ROOT / "issue_start" / "gate.py",
    ROOT / "issue_start" / "hook.py",
]
_HAS_BASH = shutil.which("bash") is not None

FIXED_NOW = datetime(2026, 8, 19, 4, 11, 7, tzinfo=timezone.utc)

# 対象外の agent_type（欠落・別ロール・非文字列）。どの verb でも無出力 exit 0 になる。
OUT_OF_SCOPE_PAYLOADS = [
    ("missing", {}),
    ("pr-reviewer", {"agent_type": "pr-reviewer"}),
    ("general-purpose", {"agent_type": "general-purpose"}),
    ("empty", {"agent_type": ""}),
    ("non-string", {"agent_type": 3}),
    ("nested-only", {"tool_input": {"subagent_type": "issue-fixer"}}),
]


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class HookTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.runner_calls = []
        self.runner_kwargs = []

    def stdin(self, payload):
        return io.StringIO(json.dumps(payload))

    def runner(self, *results):
        queue = list(results) or [FakeCompleted(0)]

        def run(argv, **kwargs):
            self.runner_calls.append(list(argv))
            self.runner_kwargs.append(kwargs)
            return queue.pop(0) if len(queue) > 1 else queue[0]

        return run

    def write_active(self, payload):
        directory = self.root / "tmp" / "_karte"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "active.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def make_worktree(self, name):
        path = self.root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path

    def open_entry(self, *, agent_type="issue-fixer", issue=309):
        return worktree_ledger.open_entry(
            self.root, issue=issue, agent_type=agent_type, round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )

    def entries(self):
        return worktree_ledger.read_ledger(self.root)["entries"]

    def assertSilentAllow(self):
        self.assertEqual(self.stdout.getvalue(), "", "対象外は stdout に何も出さない")

    def evidence_lines(self, stderr=None):
        """stderr の evidence（1行1 JSON）を dict のリストで返す。

        evidence が JSON として読めること自体を検査に含める——人が読む散文ではなく
        **機械可読な観測ログ**であることが要件（V-1/V-2 の post-merge 実測で使う）。
        """
        text = (self.stderr if stderr is None else stderr).getvalue()
        return [json.loads(line) for line in text.splitlines() if line.strip()]


class OutOfScopeTests(HookTestCase):
    """対象外ロール・`agent_type` 欠落は **どの verb でも無出力 exit 0**。

    `SubagentStart`/`SubagentStop` の `matcher` が `agent_type` 名で効くかは本 repo で未実測
    （要実測事項 V-2）なので、matcher に依存せずスクリプト側でも判定する
    （`agent-command-gate.sh` の「対象外ロールは常に許可」不変条件と同型）。
    """

    def test_karte_inject_is_silent_for_every_non_fixer_role(self):
        for label, payload in OUT_OF_SCOPE_PAYLOADS + [("implementer", {"agent_type": "issue-implementer"})]:
            with self.subTest(label=label):
                stdout, stderr = io.StringIO(), io.StringIO()
                rc = subagent_hooks.run_karte_inject(
                    stdin=self.stdin(payload), stdout=stdout, stderr=stderr,
                    project_root=ROOT, cwd=self.root, runner=self.runner(),
                )
                self.assertEqual(rc, 0)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(self.runner_calls, [], "対象外でサブプロセスを起動しない")
                self.assertEqual(self.evidence_lines(stderr)[0]["result"], "skip")

    def test_every_verb_writes_one_evidence_line_for_out_of_scope_payloads(self):
        """対象外・payload 不読でも stderr に evidence を1行残す（F-309-05）。

        無出力 exit 0 のままだと、merge 直後の実測（V-1 / V-2）で「フックが発火しなかった」と
        「発火したが対象外と判定した」を区別できない——まさに知りたいケース
        （`agent_type` の綴り違い・payload が読めない）で診断材料がゼロになる。
        """
        cases = OUT_OF_SCOPE_PAYLOADS + [("unreadable", None)]
        for verb, call in (
            ("karte-inject", lambda **kw: subagent_hooks.run_karte_inject(
                project_root=ROOT, cwd=self.root, runner=self.runner(), **kw)),
            ("bind", lambda **kw: subagent_hooks.run_bind(
                cwd=self.root, now=FIXED_NOW, **kw)),
            ("stop", lambda **kw: subagent_hooks.run_stop(
                cwd=self.root, runner=self.runner(), **kw)),
        ):
            for label, payload in cases:
                with self.subTest(verb=verb, label=label):
                    stdout, stderr = io.StringIO(), io.StringIO()
                    stdin = io.StringIO("{not json") if payload is None else self.stdin(payload)
                    rc = call(stdin=stdin, stdout=stdout, stderr=stderr)
                    self.assertEqual(rc, 0)
                    self.assertEqual(stdout.getvalue(), "", "stdout は無出力のまま")
                    lines = self.evidence_lines(stderr)
                    self.assertEqual(len(lines), 1, "evidence はちょうど1行")
                    line = lines[0]
                    self.assertEqual(line["hook"], f"subagent-{verb}")
                    self.assertEqual(line["result"], "skip")
                    if payload is None:
                        self.assertEqual(line["reason"], "PAYLOAD_UNREADABLE")
                        self.assertIsNone(line["payload_keys"], "読めない payload はキーも無い")
                    else:
                        self.assertEqual(line["reason"], "OUT_OF_SCOPE")
                        # 観測したキー集合が載る＝V-2（綴り）の判定材料。値は載せない。
                        self.assertEqual(line["payload_keys"], sorted(payload))
                        self.assertNotIn("issue-fixer", json.dumps(line, ensure_ascii=False))

    def test_bind_is_silent_and_writes_no_ledger_for_out_of_scope_roles(self):
        for label, payload in OUT_OF_SCOPE_PAYLOADS:
            with self.subTest(label=label):
                rc = subagent_hooks.run_bind(
                    stdin=self.stdin(payload), stdout=self.stdout, stderr=self.stderr,
                    cwd=self.root, now=FIXED_NOW,
                )
                self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertFalse((self.root / "tmp").exists(), "対象外で台帳を作らない")

    def test_stop_is_silent_and_runs_nothing_for_out_of_scope_roles(self):
        for label, payload in OUT_OF_SCOPE_PAYLOADS:
            with self.subTest(label=label):
                rc = subagent_hooks.run_stop(
                    stdin=self.stdin(payload), stdout=self.stdout, stderr=self.stderr,
                    cwd=self.root, runner=self.runner(),
                )
                self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertEqual(self.runner_calls, [], "対象外でサブプロセスを起動しない")

    def test_unreadable_payload_is_treated_as_out_of_scope(self):
        for verb, kwargs in (
            ("bind", {"cwd": self.root, "now": FIXED_NOW}),
            ("stop", {"cwd": self.root, "runner": self.runner()}),
        ):
            with self.subTest(verb=verb):
                func = subagent_hooks.run_bind if verb == "bind" else subagent_hooks.run_stop
                stdout = io.StringIO()
                rc = func(stdin=io.StringIO("{not json"), stdout=stdout,
                          stderr=io.StringIO(), **kwargs)
                self.assertEqual(rc, 0)
                self.assertEqual(stdout.getvalue(), "")


class KarteInjectTests(HookTestCase):
    """注入本文＝**手順書 ＋ ``karte render`` の出力**（K-14・F-309-04）。

    ``karte/cli.py::cmd_render`` の docstring は「SubagentStart フックがこれを実行し
    標準出力を ``additionalContext`` として自動注入する」と定めており、是正エージェント
    自身に ``render`` を呼ばせる設計は「呼び忘れたら過去の試行を知らないまま修正に入る」
    ため**明示的に却下されている**。手順書だけの注入は K-14 を満たさない
    （手順書は「render を呼べ」という規範であって render の出力ではない）。
    """

    PROTOCOL = None
    RENDER_STDOUT = "=== Karte: issue-309 / round 1 ===\n## Prior attempts（DO NOT repeat these）\n  - X"

    def setUp(self):
        super().setUp()
        self.PROTOCOL = (ROOT / subagent_hooks.KARTE_PROTOCOL_REL).read_text(
            encoding="utf-8"
        ).strip()

    def inject(self, *, project_root=ROOT, results=(FakeCompleted(0),), payload=None):
        rc = subagent_hooks.run_karte_inject(
            stdin=self.stdin(payload or {"agent_type": "issue-fixer"}),
            stdout=self.stdout, stderr=self.stderr,
            project_root=project_root, cwd=self.root, runner=self.runner(*results),
        )
        self.assertEqual(rc, 0)
        return rc

    def context(self):
        specific = json.loads(self.stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SubagentStart")
        return specific["additionalContext"]

    def test_fixer_receives_the_protocol_and_the_rendered_karte(self):
        self.write_active({"issue": 309, "round": 1})
        self.inject(results=(FakeCompleted(0, stdout=self.RENDER_STDOUT + "\n"),))
        body = self.context()
        # 1節目＝手順書（シェルからも python からも分離されたファイルが唯一の出所）。
        self.assertIn("python3 -m karte append", body)
        self.assertIn("python3 -m karte check", body)
        # 2節目＝render の出力そのもの（手順書の文言ではなくカルテの中身）。
        self.assertEqual(
            body, self.PROTOCOL + subagent_hooks.INJECT_SEPARATOR + self.RENDER_STDOUT
        )
        self.assertIn("Prior attempts", body, "過去の試行が本文として届いている")

    def test_render_is_invoked_with_an_explicit_issue_from_the_active_pointer(self):
        """``--issue`` は必ず明示する（並行運用時に別 Issue のカルテを読ませない）。"""
        self.write_active({"issue": 309, "round": 4})
        self.inject(results=(FakeCompleted(0, stdout=self.RENDER_STDOUT),))
        self.assertEqual(
            self.runner_calls[0][1:], ["-m", "karte", "render", "--issue", "309"]
        )
        self.assertEqual(self.runner_kwargs[0]["cwd"], str(self.root))
        self.assertFalse(self.runner_kwargs[0]["shell"])

    def test_render_failure_degrades_to_the_protocol_only_fail_open(self):
        """注入は助言なので、render が落ちても手順書だけで注入を続ける（fail-open）。

        停止ゲート（run_stop）の fail-close とは方向が逆であることに注意。
        """
        self.write_active({"issue": 309, "round": 1})
        for label, results in (
            ("exit-2", (FakeCompleted(2, stderr="未検出"),)),
            ("empty-stdout", (FakeCompleted(0, stdout="  \n"),)),
        ):
            with self.subTest(label=label):
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                self.inject(results=results)
                self.assertEqual(self.context(), self.PROTOCOL)
                reasons = [line.get("reason") for line in self.evidence_lines()]
                self.assertIn("KARTE_RENDER_FAILED", reasons)

    def test_unrunnable_render_degrades_to_the_protocol_only(self):
        self.write_active({"issue": 309, "round": 1})

        def boom(argv, **kwargs):
            self.runner_calls.append(list(argv))
            raise OSError("python3 not found")

        subagent_hooks.run_karte_inject(
            stdin=self.stdin({"agent_type": "issue-fixer"}),
            stdout=self.stdout, stderr=self.stderr,
            project_root=ROOT, cwd=self.root, runner=boom,
        )
        self.assertEqual(self.context(), self.PROTOCOL)
        self.assertIn("KARTE_RENDER_UNRUNNABLE", self.stderr.getvalue())

    def test_missing_active_pointer_skips_render_without_running_it(self):
        self.inject()
        self.assertEqual(self.context(), self.PROTOCOL)
        self.assertEqual(self.runner_calls, [], "issue が決まらないなら render を起動しない")
        reasons = [line.get("reason") for line in self.evidence_lines()]
        self.assertIn("ACTIVE_POINTER_UNREADABLE", reasons)

    def test_rendered_karte_is_injected_even_without_the_protocol_file(self):
        """2節は独立している——片方が落ちてももう片方は届く。"""
        self.write_active({"issue": 309, "round": 1})
        self.inject(
            project_root=self.root,  # 手順書が存在しない一時ルート
            results=(FakeCompleted(0, stdout=self.RENDER_STDOUT),),
        )
        self.assertEqual(self.context(), self.RENDER_STDOUT)

    def test_missing_or_empty_protocol_and_no_karte_injects_nothing_fail_open(self):
        for label, prepare in (
            ("missing", lambda root: None),
            ("empty", lambda root: (root / subagent_hooks.KARTE_PROTOCOL_REL).write_text(
                "\n", encoding="utf-8")),
        ):
            with self.subTest(label=label):
                (self.root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
                prepare(self.root)
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                rc = subagent_hooks.run_karte_inject(
                    stdin=self.stdin({"agent_type": "issue-fixer"}),
                    stdout=self.stdout, stderr=self.stderr,
                    project_root=self.root, cwd=self.root, runner=self.runner(),
                )
                self.assertEqual(rc, 0)
                self.assertEqual(self.stdout.getvalue(), "", "注入は助言＝fail-open")
                self.assertIn("skip", self.stderr.getvalue())
                reasons = [line.get("reason") for line in self.evidence_lines()]
                self.assertIn("NOTHING_TO_INJECT", reasons)


class BindTests(HookTestCase):
    def payload(self, *, agent_type="issue-implementer", agent_id="abc"):
        payload = {"agent_type": agent_type}
        if agent_id is not None:
            payload["agent_id"] = agent_id
        return payload

    def test_direct_agent_id_match_binds_the_open_entry(self):
        entry_id = self.open_entry(agent_type="issue-implementer")
        self.make_worktree("agent-abc")
        rc = subagent_hooks.run_bind(
            stdin=self.stdin(self.payload()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        entry = self.entries()[0]
        self.assertEqual(entry["entry_id"], entry_id)
        self.assertEqual(entry["status"], "running")
        self.assertEqual(entry["agent_id"], "abc")
        self.assertEqual(entry["worktree_path"], ".claude/worktrees/agent-abc")
        self.assertIn('"how":"agent_id"', self.stderr.getvalue())

    def test_diff_detection_binds_when_agent_id_does_not_match_the_directory(self):
        """選択肢 BIND-1 案A: payload の `agent_id` と worktree 名が一致しなくても束縛する。

        要実測事項 V-1（`agent-<id>` の `<id>` が payload の `agent_id` と一致するか）が
        「一致しない」だった場合の経路。payload の内部形式に依存しない。
        """
        self.open_entry(agent_type="issue-implementer")
        self.make_worktree("agent-a14df44b4e4136a73")
        subagent_hooks.run_bind(
            stdin=self.stdin(self.payload(agent_id="totally-different")),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, now=FIXED_NOW,
        )
        entry = self.entries()[0]
        self.assertEqual(entry["status"], "running")
        self.assertEqual(entry["worktree_path"], ".claude/worktrees/agent-a14df44b4e4136a73")
        # 束縛キーは payload の agent_id を優先する（SubagentStop が同じキーで引くため）。
        self.assertEqual(entry["agent_id"], "totally-different")
        self.assertIn('"how":"diff"', self.stderr.getvalue())

    def test_missing_agent_id_falls_back_to_the_directory_name(self):
        self.open_entry(agent_type="issue-fixer")
        self.make_worktree("agent-abc")
        subagent_hooks.run_bind(
            stdin=self.stdin(self.payload(agent_type="issue-fixer", agent_id=None)),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, now=FIXED_NOW,
        )
        self.assertEqual(self.entries()[0]["agent_id"], "abc")

    def test_absent_worktree_only_adds_a_note_and_binds_nothing(self):
        entry_id = self.open_entry(agent_type="issue-implementer")
        subagent_hooks.run_bind(
            stdin=self.stdin(self.payload()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
        )
        entry = self.entries()[0]
        self.assertEqual(entry["entry_id"], entry_id)
        self.assertEqual(entry["status"], "open", "推測して running にしない")
        self.assertIsNone(entry["worktree_path"])
        self.assertEqual(len(entry["notes"]), 1)
        self.assertIn("束縛しなかった", entry["notes"][0]["note"])
        self.assertEqual(entry["notes"][0]["at"], "2026-08-19T04:11:07Z")
        self.assertSilentAllow()

    def test_ambiguous_running_dispatch_is_not_bound(self):
        first = self.open_entry(agent_type="issue-implementer")
        self.make_worktree("agent-live")
        self.make_worktree("agent-new")
        worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="live",
            worktree_path=".claude/worktrees/agent-live",
        )
        second = self.open_entry(agent_type="issue-implementer")
        subagent_hooks.run_bind(
            stdin=self.stdin(self.payload(agent_id="unknown-id")),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, now=FIXED_NOW,
        )
        by_id = {item["entry_id"]: item for item in self.entries()}
        self.assertEqual(by_id[first]["worktree_path"], ".claude/worktrees/agent-live")
        self.assertEqual(by_id[second]["status"], "open")
        self.assertIn("ambiguous-running", by_id[second]["notes"][0]["note"])

    def test_no_open_entry_is_reported_without_creating_one(self):
        self.make_worktree("agent-abc")
        subagent_hooks.run_bind(
            stdin=self.stdin(self.payload()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
        )
        self.assertEqual(self.entries(), [], "フックはエントリを新規作成しない（起票は gate）")
        self.assertSilentAllow()

    def test_broken_ledger_does_not_block_the_dispatch(self):
        path = worktree_ledger.ledger_path(self.root, create_dir=True)
        path.write_text("{broken", encoding="utf-8")
        rc = subagent_hooks.run_bind(
            stdin=self.stdin(self.payload()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertIn("LEDGER_INVALID_JSON", self.stderr.getvalue())


class StopKarteGateTests(HookTestCase):
    def fixer(self):
        return {"agent_type": "issue-fixer", "agent_id": "abc"}

    def decision(self):
        return json.loads(self.stdout.getvalue())

    def test_karte_check_success_lets_the_subagent_stop(self):
        self.write_active({"issue": 309, "round": 2})
        rc = subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, runner=self.runner(FakeCompleted(0)),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertEqual(
            self.runner_calls[0][1:],
            ["-m", "karte", "check", "--issue", "309", "--round", "2"],
        )

    def test_karte_check_failure_blocks_with_exit_code_zero(self):
        self.write_active({"issue": 309, "round": 2})
        rc = subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root,
            runner=self.runner(FakeCompleted(4, stderr="NG: 未クローズの Attempt が残っている: 1")),
        )
        # exit code は 0 のまま（既存ハーネスの check=True 前提を壊さない）。
        self.assertEqual(rc, 0)
        decision = self.decision()
        self.assertEqual(decision["decision"], "block")
        reason = decision["reason"]
        self.assertIn("python3 -m karte append", reason)
        self.assertIn("python3 -m karte close-attempt", reason)
        self.assertIn("--issue 309", reason)
        self.assertIn("--round 2", reason)
        self.assertIn("未クローズの Attempt", reason, "karte の stderr を握り潰さない")

    def test_missing_or_broken_active_pointer_blocks_fail_close(self):
        cases = [
            ("missing", None),
            ("broken-json", "{not json"),
            ("not-an-object", json.dumps([1, 2])),
            ("no-issue", {"round": 2}),
            ("no-round", {"issue": 309}),
            ("issue-not-int", {"issue": "309", "round": 2}),
            ("round-zero", {"issue": 309, "round": 0}),
            ("round-bool", {"issue": 309, "round": True}),
        ]
        for label, payload in cases:
            with self.subTest(label=label):
                active = self.root / "tmp" / "_karte" / "active.json"
                if active.exists():
                    active.unlink()
                if payload is not None:
                    self.write_active(payload)
                stdout = io.StringIO()
                rc = subagent_hooks.run_stop(
                    stdin=self.stdin(self.fixer()), stdout=stdout, stderr=io.StringIO(),
                    cwd=self.root, runner=self.runner(),
                )
                self.assertEqual(rc, 0)
                decision = json.loads(stdout.getvalue())
                self.assertEqual(decision["decision"], "block")
                self.assertIn("判定不能は fail-close", decision["reason"])
        self.assertEqual(self.runner_calls, [], "判定不能なら karte check を起動しない")

    def test_symlinked_karte_place_blocks_fail_close(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.root / "tmp").mkdir()
        (self.root / "tmp" / "_karte").symlink_to(elsewhere, target_is_directory=True)
        subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, runner=self.runner(),
        )
        self.assertEqual(self.decision()["decision"], "block")

    def test_unrunnable_karte_check_blocks_fail_close(self):
        self.write_active({"issue": 309, "round": 1})

        def boom(argv, **kwargs):
            self.runner_calls.append(list(argv))
            raise OSError("python3 not found")

        subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, runner=boom,
        )
        decision = self.decision()
        self.assertEqual(decision["decision"], "block")
        self.assertIn("起動できなかった", decision["reason"])

    def test_reentrant_stop_is_not_blocked_again(self):
        """一度 block した後の再入（``stop_hook_active``）は判定せず通す（F-309-02）。

        block reason が指す脱出手順は、条件によっては**ブロックされた当人には実行できない**
        （進行ポインタの再生成に要る ``karte ingest-review`` は是正当事者に許されない＝
        Issue #308 / #341）。再入判定が無いと、満たしようのない条件を突きつけられたまま
        永久に停止できない。
        """
        # active.json は無い＝1回目なら必ず block する条件。
        for label, key in (("stop_hook_active", "stop_hook_active"),
                           ("subagent_stop_hook_active", "subagent_stop_hook_active")):
            with self.subTest(label=label):
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                payload = {**self.fixer(), key: True}
                rc = subagent_hooks.run_stop(
                    stdin=self.stdin(payload), stdout=self.stdout, stderr=self.stderr,
                    cwd=self.root, runner=self.runner(),
                )
                self.assertEqual(rc, 0)
                self.assertSilentAllow()
                self.assertEqual(self.runner_calls, [], "再入では karte check も起動しない")
                reasons = [line.get("reason") for line in self.evidence_lines()]
                self.assertIn("STOP_HOOK_REENTRY", reasons)

    def test_first_stop_still_blocks_before_the_reentry_escape(self):
        """再入で通すのは**2回目以降**——1回目は必ず止めて理由を届ける（ゲートを弱めない）。"""
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({**self.fixer(), "stop_hook_active": False}),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.decision()["decision"], "block")

    def test_block_reason_only_lists_steps_the_fixer_can_perform(self):
        """脱出手順は**当人が実行できるもの**だけ（F-309-02）。

        旧 reason は「主文脈が ingest-review を実行すること」を指示していたが、
        それを読むのはブロックされた `issue-fixer` 自身であり、当の操作は当人には
        許されていない＝自力では条件を満たせない。
        """
        subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, runner=self.runner(),
        )
        reason = self.decision()["reason"]
        self.assertIn("判定不能は fail-close", reason)
        self.assertIn("1回だけ", reason, "再入で抜けられることを本人に伝える")
        self.assertIn("stop_reason", reason, "呼び出し元へ報告して停止する道を示す")
        self.assertIn("是正当事者には許されない", reason)

    def test_repo_root_failure_blocks_the_fixer_fail_close(self):
        """カルテの置き場を導出できない＝判定不能なので `issue-fixer` は block（fail-close）。"""
        (self.root / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        subagent_hooks.run_stop(
            stdin=self.stdin(self.fixer()), stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, runner=self.runner(),
        )
        self.assertEqual(self.decision()["decision"], "block")
        self.assertIn("REPO_ROOT_UNRESOLVED", self.stderr.getvalue())

    def test_implementer_survives_an_unresolvable_repo_root(self):
        """`issue-implementer` の SubagentStop は台帳パスを導出しない（F-309-06）。

        本来なにもしない経路なのに導出が例外を投げて未捕捉のまま exit 1 になると、
        無関係な dispatch にエラーを出す。導出を `issue-fixer` 経路の内側へ移した回帰。
        """
        (self.root / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-implementer", "agent_id": "abc"}),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertEqual(self.runner_calls, [])

    def test_implementer_is_not_subject_to_the_karte_gate(self):
        """カルテ規律は是正ラウンド（`issue-fixer`）の契約。実装者は対象外。"""
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-implementer", "agent_id": "abc"}),
            stdout=self.stdout, stderr=self.stderr, cwd=self.root, runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertEqual(self.runner_calls, [])


class NoDeletionPathTests(HookTestCase):
    """**本 PR は worktree を1つも削除しない**（構造的にゼロ）ことの回帰固定。"""

    def test_hooks_never_spawn_a_worktree_subcommand(self):
        self.write_active({"issue": 309, "round": 1})
        self.make_worktree("agent-abc")
        self.open_entry(agent_type="issue-fixer")
        subagent_hooks.run_bind(
            stdin=self.stdin({"agent_type": "issue-fixer", "agent_id": "abc"}),
            stdout=io.StringIO(), stderr=io.StringIO(), cwd=self.root, now=FIXED_NOW,
        )
        for completed in (FakeCompleted(0), FakeCompleted(4)):
            subagent_hooks.run_stop(
                stdin=self.stdin({"agent_type": "issue-fixer", "agent_id": "abc"}),
                stdout=io.StringIO(), stderr=io.StringIO(),
                cwd=self.root, runner=self.runner(completed),
            )
        self.assertTrue(self.runner_calls, "karte check は起動されている（前提の確認）")
        tokens = {token for call in self.runner_calls for token in call}
        self.assertNotIn("worktree", tokens)
        self.assertNotIn("remove", tokens)
        # worktree ディレクトリも台帳エントリも残っている。
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())
        self.assertEqual(len(self.entries()), 1)

    def test_shipped_modules_contain_no_worktree_subcommand_literal(self):
        for path in SHIPPED_MODULES:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                literals = {
                    node.value
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                # argv の要素になりうる裸トークンだけを見る（散文・docstring 中の
                # 「git worktree remove を呼ばない」という記述は当然ヒットしない）。
                self.assertNotIn("worktree", literals)
                self.assertNotIn("remove", literals)
                self.assertNotIn("rmtree", literals)

    def test_hook_scripts_contain_no_worktree_command_outside_comments(self):
        for name, path in HOOK_SCRIPTS.items():
            with self.subTest(hook=name):
                code = "\n".join(
                    line for line in path.read_text(encoding="utf-8").splitlines()
                    if not line.lstrip().startswith("#")
                )
                self.assertNotIn("worktree", code)
                self.assertNotIn("rm ", code)

    def test_karte_argv_builders_are_the_only_subprocess_contract(self):
        """本 PR がサブプロセスを起動するのは `karte check` と `karte render` の2つだけ。

        どちらも `karte` の read-only / 検査 verb であり、`git worktree remove` は現れない。
        """
        self.assertEqual(
            subagent_hooks.karte_check_argv(7, 3)[1:],
            ["-m", "karte", "check", "--issue", "7", "--round", "3"],
        )
        self.assertEqual(
            subagent_hooks.karte_render_argv(7)[1:],
            ["-m", "karte", "render", "--issue", "7"],
        )
        for argv in (subagent_hooks.karte_check_argv(7, 3), subagent_hooks.karte_render_argv(7)):
            self.assertNotIn("worktree", argv)
            self.assertNotIn("remove", argv)


@unittest.skipUnless(_HAS_BASH, "bash が無い環境ではフック起動口を検証しない")
class LauncherWiringTests(unittest.TestCase):
    """`.sh` 起動口が **cwd に依らず** `$CLAUDE_PROJECT_DIR` 側の実体へ届くこと（F-309-01）。

    `python3 -m` は **sys.path[0] にプロセスの cwd を先に置く**ため、PYTHONPATH に
    `$CLAUDE_PROJECT_DIR` を入れるだけでは足りない——別ツリー（linked worktree・別 checkout）を
    cwd に起動されると cwd 側の `issue_start` が正本側を覆い隠し、`ModuleNotFoundError` で
    exit 1 になる。**停止ゲートにとってこれは fail-close の破れ**（block されず素通りする）。

    そこで全テストを、`issue_start` は持つが `subagent_hooks` を持たない**おとりディレクトリ**を
    cwd にして走らせる。旧実装（`cd` も `PYTHONSAFEPATH` も無い版）はここで必ず落ちる。

    副作用のある経路（台帳への書込・`karte check` 実行）は**実リポジトリを汚すので
    サブプロセスでは踏まない**。`karte render` は read-only なので踏んでよい。
    """

    @classmethod
    def setUpClass(cls):
        cls._decoy = tempfile.TemporaryDirectory(prefix="subagent-hooks-decoy-")
        decoy = Path(cls._decoy.name).resolve()
        package = decoy / "issue_start"
        package.mkdir()
        # `issue_start` はあるが `subagent_hooks` は無い＝cwd が優先されたら
        # ModuleNotFoundError になる形（レビューアが F-309-01 を再現した状況と同型）。
        (package / "__init__.py").write_text("", encoding="utf-8")
        cls.DECOY = decoy

    @classmethod
    def tearDownClass(cls):
        cls._decoy.cleanup()

    def run_hook(self, verb, payload, cwd=None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONSAFEPATH", None)
        return subprocess.run(
            ["bash", str(HOOK_SCRIPTS[verb])],
            input=json.dumps(payload), text=True, capture_output=True, env=env,
            cwd=str(self.DECOY if cwd is None else cwd), check=True,
        )

    def test_every_launcher_reaches_the_module_from_a_foreign_cwd(self):
        """外部 cwd から起動しても正本側の判定が動く（＝素通りしていない）。

        「無出力 exit 0」だけを見ると、判定が走った結果の対象外なのか、
        モジュールに届かず落ちたのかを区別できない。evidence 行の存在で前者を確認する
        （F-309-05 の evidence がここで F-309-01 の検出器としても効く）。
        """
        for verb in HOOK_SCRIPTS:
            with self.subTest(verb=verb):
                result = self.run_hook(verb, {"agent_type": "pr-reviewer"})
                self.assertEqual(result.stdout, "", "対象外は stdout に何も出さない")
                self.assertNotIn("ModuleNotFoundError", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                lines = [line for line in result.stderr.splitlines() if line.strip()]
                self.assertEqual(len(lines), 1, f"evidence 1行だけのはず: {result.stderr!r}")
                evidence = json.loads(lines[0])
                self.assertEqual(evidence["result"], "skip")
                self.assertEqual(evidence["agent_type"], "pr-reviewer")

    def test_karte_inject_launcher_emits_the_protocol_from_a_foreign_cwd(self):
        result = self.run_hook("karte-inject", {"agent_type": "issue-fixer"})
        specific = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SubagentStart")
        body = specific["additionalContext"]
        self.assertIn("python3 -m karte render", body)
        self.assertIn("python3 -m karte append", body)

    def test_unknown_verb_is_a_no_op(self):
        """モジュール直起動の usage 経路（起動口ではなくエントリポイントの契約）。

        cwd を明示するのは、テストランナーの cwd（別 checkout かもしれない）に
        判定結果を依存させないため——起動口側の cwd 非依存は上の2本が見ている。
        """
        env = {**os.environ, "PYTHONPATH": str(ROOT)}
        result = subprocess.run(
            ["python3", "-m", "issue_start.subagent_hooks", "release-worktree"],
            input="{}", text=True, capture_output=True, env=env,
            cwd=str(ROOT), check=True,
        )
        self.assertEqual(result.stdout, "")
        self.assertIn("usage:", result.stderr)

    def test_launchers_do_not_depend_on_an_inherited_pythonpath(self):
        """呼び出し元の PYTHONPATH が汚れていても正本側が勝つ。

        `$CLAUDE_PROJECT_DIR` は export される PYTHONPATH の**先頭**に積まれる。
        """
        result = self.run_hook("bind", {"agent_type": "pr-reviewer"})
        self.assertEqual(result.returncode, 0)
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT), "PYTHONPATH": str(self.DECOY)}
        polluted = subprocess.run(
            ["bash", str(HOOK_SCRIPTS["bind"])],
            input=json.dumps({"agent_type": "pr-reviewer"}), text=True,
            capture_output=True, env=env, cwd=str(self.DECOY), check=True,
        )
        self.assertEqual(polluted.stdout, "")
        self.assertNotIn("ModuleNotFoundError", polluted.stderr)
        self.assertEqual(json.loads(polluted.stderr.strip())["result"], "skip")


class SettingsRegistrationTests(unittest.TestCase):
    SETTINGS = ROOT / ".claude" / "settings.json"

    def setUp(self):
        self.settings = json.loads(self.SETTINGS.read_text(encoding="utf-8"))["hooks"]

    def commands(self, event):
        return [
            hook["command"]
            for entry in self.settings.get(event, [])
            for hook in entry["hooks"]
        ]

    def test_subagent_events_are_registered_with_role_matchers(self):
        start = {entry["matcher"]: entry for entry in self.settings["SubagentStart"]}
        self.assertEqual(set(start), {"issue-fixer", "issue-implementer|issue-fixer"})
        self.assertIn(
            "subagent-karte-inject.sh", start["issue-fixer"]["hooks"][0]["command"]
        )
        self.assertIn(
            "subagent-worktree-bind.sh",
            start["issue-implementer|issue-fixer"]["hooks"][0]["command"],
        )
        stop = self.settings["SubagentStop"]
        self.assertEqual([entry["matcher"] for entry in stop], ["issue-implementer|issue-fixer"])
        self.assertIn("subagent-stop-gate.sh", stop[0]["hooks"][0]["command"])

    def test_new_commands_quote_the_project_dir_and_reference_existing_scripts(self):
        for event in ("SubagentStart", "SubagentStop"):
            for command in self.commands(event):
                with self.subTest(command=command):
                    # Issue #270 の未引用問題に追随しない（新規行は最初から引用する）。
                    self.assertIn('"$CLAUDE_PROJECT_DIR"', command)
                    self.assertNotIn("${CLAUDE_PROJECT_DIR}", command)
                    script = HOOK_DIR / command.rsplit("/", 1)[-1]
                    self.assertTrue(script.is_file(), f"{script} が存在しない")

    def test_pre_existing_registrations_are_untouched(self):
        """AC「既存エントリに手を入れていない（追加のみ）」の回帰。"""
        pre_tool_use = self.commands("PreToolUse")
        self.assertEqual(len(pre_tool_use), 3)
        self.assertEqual(
            pre_tool_use[2],
            "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/issue-start-gate.sh",
        )
        self.assertEqual(
            self.commands("PostToolUse"),
            ["${CLAUDE_PROJECT_DIR}/.claude/hooks/check-governance-drift.sh"],
        )
        self.assertEqual(
            self.commands("UserPromptSubmit"),
            ["${CLAUDE_PROJECT_DIR}/.claude/hooks/inject-governance.sh"],
        )


if __name__ == "__main__":
    unittest.main()
