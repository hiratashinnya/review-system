"""SubagentStart / SubagentStop フックの単体テスト（Issue #309・PR-1 ＋ Issue #354・PR-3）。

最重要の不変条件は「**フック自身は worktree を消さない**」こと。解放は
`python3 -m gitgate collect-worktree`（回収→検証→解放の段構造）を起動する形だけで行い、
実体を消してよいかの判断は `gitgate/worktree.py` に集約されている。
:class:`NoDeletionPathTests` が、出荷コードに直接の削除経路が生えていないことを機械的に固定し、
:class:`ReleaseStageTests` / :class:`ReleaseStageIntegrationTests` が「回収できなければ
解放しない」（FR-W2）と `running` → `stopped` の遷移順序（F-354-01）を固定する。
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
_HAS_GIT = shutil.which("git") is not None

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


class ReleaseStageTests(HookTestCase):
    """Issue #354 PR-3: `SubagentStop` の回収・解放段。

    **最重要の順序**は `running` → `stopped` → `collect-worktree`。`collect-worktree` は
    台帳 status `running` を `WORKTREE_LIVE` で拒否し `stopped` のみ受理する（PR-2 の
    F-354-01 是正）ため、遷移を挟まないと自動解放は一度も成功しない。
    """

    def bind(self, *, agent_type="issue-implementer", agent_id="abc", issue=354):
        self.make_worktree(f"agent-{agent_id}")
        worktree_ledger.open_entry(
            self.root, issue=issue, agent_type=agent_type, round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )
        return worktree_ledger.bind_agent(
            self.root, agent_type=agent_type, agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )

    def write_handoff(self, agent_id, *names):
        directory = self.root / ".claude" / "worktrees" / f"agent-{agent_id}" / "tmp" / "_handoff"
        directory.mkdir(parents=True, exist_ok=True)
        for name in names:
            (directory / name).write_text("agent: issue-implementer\n", encoding="utf-8")
        return directory

    def stop(self, *, agent_type="issue-implementer", agent_id="abc", results=(FakeCompleted(0),)):
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": agent_type, "agent_id": agent_id}),
            stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW, runner=self.runner(*results),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        return rc

    def status_of(self, entry_id):
        return {item["entry_id"]: item for item in self.entries()}[entry_id]["status"]

    def collect_calls(self):
        return [call for call in self.runner_calls if "collect-worktree" in call]

    def test_running_is_moved_to_stopped_before_collect_is_invoked(self):
        entry_id = self.bind()
        self.write_handoff("abc", "issue-implementer--issue-354.yaml")
        observed = {}

        def run(argv, **kwargs):
            self.runner_calls.append(list(argv))
            self.runner_kwargs.append(kwargs)
            # `collect-worktree` が起動された**時点の**台帳状態を捕まえる。
            observed["status"] = self.status_of(entry_id)
            return FakeCompleted(0)

        subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-implementer", "agent_id": "abc"}),
            stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW, runner=run,
        )
        self.assertEqual(
            observed["status"], "stopped",
            "collect-worktree は running を WORKTREE_LIVE で拒否する（F-354-01）",
        )
        self.assertEqual(
            self.runner_calls[0][1:],
            [
                "-m", "gitgate", "collect-worktree", "--entry", entry_id,
                "--handoff", "tmp/_handoff/issue-implementer--issue-354.yaml",
            ],
        )
        self.assertEqual(self.runner_kwargs[0]["cwd"], str(self.root))
        self.assertFalse(self.runner_kwargs[0]["shell"])
        self.assertEqual(self.runner_kwargs[0]["timeout"], subagent_hooks.COLLECT_TIMEOUT_S)

    def test_stopped_note_records_the_owner_stop(self):
        entry_id = self.bind()
        self.write_handoff("abc", "issue-implementer--issue-354.yaml")
        self.stop()
        notes = [item["note"] for item in self.entries()[0]["notes"]]
        self.assertTrue(any("停止を確認した" in note for note in notes))
        self.assertEqual(self.entries()[0]["notes"][0]["at"], "2026-08-19T04:11:07Z")
        evidence = [line for line in self.evidence_lines() if line.get("result") == "release-ok"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["entry_id"], entry_id)
        self.assertEqual(evidence[0]["how"], "unique")

    def test_collect_failure_marks_stale_and_never_removes_the_worktree(self):
        """回収に失敗したらブロックせず `stale` に落として制御を主文脈へ返す。

        次 dispatch を gate が `ISSUE_START_WORKTREE_RESIDUE` で deny するので気づける。
        **`git worktree remove` は呼ばれない**（＝FR-W2「回収できなければ解放しない」）。
        """
        entry_id = self.bind()
        self.write_handoff("abc", "issue-implementer--issue-354.yaml")
        self.stop(results=(FakeCompleted(2, stderr="gitgate: COLLECT_HANDOFF_MISSING"),))
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())
        tokens = {token for call in self.runner_calls for token in call}
        self.assertNotIn("remove", tokens, "フックは git worktree remove を直接呼ばない")
        notes = [item["note"] for item in self.entries()[0]["notes"]]
        self.assertTrue(any("COLLECT_HANDOFF_MISSING" in note for note in notes))

    def test_unrunnable_or_timed_out_collect_marks_stale_without_deleting(self):
        for label, error in (
            ("unrunnable", OSError("python3 not found")),
            ("timeout", subprocess.TimeoutExpired(cmd="gitgate", timeout=45.0)),
        ):
            with self.subTest(label=label):
                self.setUp()
                entry_id = self.bind()
                self.write_handoff("abc", "issue-implementer--issue-354.yaml")

                def boom(argv, **kwargs):
                    self.runner_calls.append(list(argv))
                    raise error

                rc = subagent_hooks.run_stop(
                    stdin=self.stdin({"agent_type": "issue-implementer", "agent_id": "abc"}),
                    stdout=self.stdout, stderr=self.stderr,
                    cwd=self.root, now=FIXED_NOW, runner=boom,
                )
                self.assertEqual(rc, 0)
                self.assertSilentAllow()
                self.assertEqual(self.status_of(entry_id), "stale")
                self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())

    def test_absent_own_handoff_defers_instead_of_collecting(self):
        """自分の handoff が無い停止は**保留**する（Issue #423）。

        旧実装は「列挙して0件」を「終了したが渡すものが無い」と読み、その場で
        ``--allow-missing-handoff`` を付けて回収を試みていた。だがこの0件は
        **「まだ自分の handoff を書く段に到達していない」（入れ子委譲待ちで一時停止中）**と
        コード上まったく区別がつかない。区別できないものを「終了」と決めつけると、
        回収試行が失敗して ``stale`` に落ち、その ``stale`` が residue として
        **同じ dispatch 自身の次の委譲**を gate に拒否させる（#423 の実害）。

        したがって: 台帳は ``running`` のまま・``collect-worktree`` は起動しない・
        worktree は消さない。判定材料は stderr の evidence に残す。
        """
        entry_id = self.bind()
        self.stop()
        self.assertEqual(self.collect_calls(), [], "終了と断定できないなら回収を起動しない")
        self.assertEqual(self.status_of(entry_id), "running", "台帳を一切進めない")
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())
        evidence = [
            line for line in self.evidence_lines() if line.get("result") == "release-deferred"
        ]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["reason"], "HANDOFF_PENDING")
        notes = [item["note"] for item in self.entries()[0]["notes"]]
        self.assertTrue(any(subagent_hooks.HANDOFF_PENDING_MARKER in note for note in notes))

    def test_deferring_keeps_the_worktree_out_of_the_residue_report(self):
        """保留は gate の残留判定に出ない＝**自分の次の入れ子委譲を塞がない**（#423 の核心）。

        ``stopped`` / ``stale`` はどちらも
        :data:`worktree_ledger.RESIDUE_STATUSES` に入るため、保留をそこへ落とすと
        ``issue-start-gate`` が ``ISSUE_START_WORKTREE_RESIDUE`` で**同じ dispatch 自身の**
        次の ``Task`` 委譲を拒否する。``running`` のままなら residue にも unclaimed にも
        現れない。
        """
        self.bind()
        self.stop()
        report = worktree_ledger.residue_report(self.root)
        self.assertEqual(report["stale"], [], "保留は残留として deny の材料にならない")
        self.assertEqual(report["unclaimed"], [], "占有は正当なので孤児にもならない")
        self.assertEqual(report["running"], [".claude/worktrees/agent-abc"])

    def test_repeated_deferrals_record_only_one_note(self):
        """入れ子委譲のたびに停止イベントが届いても台帳へ積み増さない。

        毎回 notes を足すと観測ログで台帳が埋まるうえ、``update_ledger`` のロック取得回数が
        dispatch あたり水増しされる（#423 が並列 dispatch のロック競合リスクとして指摘した
        増幅要因そのもの）。2回目以降は stderr の evidence だけにする。
        """
        entry_id = self.bind()
        for _round in range(3):
            self.stdout, self.stderr = io.StringIO(), io.StringIO()
            self.stop()
        notes = [item["note"] for item in self.entries()[0]["notes"]]
        pending = [note for note in notes if subagent_hooks.HANDOFF_PENDING_MARKER in note]
        self.assertEqual(len(pending), 1, f"1行だけのはず: {notes}")
        self.assertEqual(self.status_of(entry_id), "running")

    def test_handoffs_of_delegated_agents_are_not_mistaken_for_mine(self):
        """入れ子委譲先の handoff は**自分の成果物ではない**（Issue #423）。

        ``issue-implementer`` が ``verification-author`` → ``reconciliation-validator`` →
        ``reconciliation`` と委譲すると、委譲先の handoff が**同じ** ``tmp/_handoff/`` に
        溜まる。所有者を見ずに件数だけ数える旧実装は、1件目を自分の成果物と誤認して回収し
        （#338 実測）、2件目以降で ``ambiguous`` に落ちて回収不能になっていた。
        """
        entry_id = self.bind()
        self.write_handoff("abc", "verification-author--issue-354-fnd.yaml")
        self.stop()
        self.assertEqual(self.collect_calls(), [], "他人の handoff を自分の成果物にしない")
        self.assertEqual(self.status_of(entry_id), "running")
        # 委譲先が増えても ambiguous にはならない（保留のまま）。
        self.write_handoff("abc", "reconciliation--issue-354-batch.yaml")
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.stop()
        self.assertEqual(self.collect_calls(), [])
        self.assertEqual(self.status_of(entry_id), "running")

    def test_nested_delegation_chain_completes_without_manual_intervention(self):
        """**Issue #338 と同型の多段入れ子 dispatch の通し回帰**（#423 の受け入れ条件）。

        委譲のたびに届く停止イベントを3回模擬し、そのあいだ台帳が一度も residue にならない
        こと（＝gate が同じ dispatch 自身の次の委譲を拒否しないこと）と、最後に自分の
        handoff を書いた停止で初めて回収・解放が走ることを固定する。旧実装ではこの通しが
        1回目の停止で ``stale`` に落ち、以降すべての委譲が deny されていた。
        """
        entry_id = self.bind()
        delegated = [
            "verification-author--issue-354-fnd.yaml",
            "reconciliation-validator--issue-354.yaml",
            "reconciliation--issue-354-batch.yaml",
        ]
        for index, name in enumerate(delegated, start=1):
            self.stdout, self.stderr = io.StringIO(), io.StringIO()
            self.stop()  # 委譲へ入る直前の一時停止
            self.assertEqual(self.status_of(entry_id), "running", f"{index} 回目で進めない")
            self.assertEqual(
                worktree_ledger.residue_report(self.root)["stale"], [],
                f"{index} 回目の停止で residue を作らない（次の委譲を塞がない）",
            )
            self.write_handoff("abc", name)  # 委譲先が成果物を置いて戻る
        self.assertEqual(self.collect_calls(), [], "ここまで一度も回収を起動しない")

        # 実装者本人が自分の handoff を書いて終了する＝初めての「終了」signal。
        self.write_handoff("abc", "issue-implementer--issue-354.yaml")
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.stop()
        argv = self.collect_calls()[0]
        self.assertIn("--handoff", argv)
        self.assertIn("tmp/_handoff/issue-implementer--issue-354.yaml", argv)
        self.assertEqual(self.status_of(entry_id), "stopped", "台帳を進めるのは gitgate 側")

    def test_early_stop_is_collected_once_it_writes_its_stop_reason_handoff(self):
        """Step 0 で早期 STOP した ``issue-fixer`` も自動で回収・解放される。

        両ロールの契約は「STOP 時は stop_reason に…必ず書く」であり、``stop_reason`` は
        **ハンドオフのフィールド**である（`.ai/agents/issue-fixer.md`「出力とハンドオフ」）。
        つまり早期 STOP でもハンドオフは書かれるので、それが「終了した」signal として働く。
        実装は何も書かず ``status: stop`` だけのハンドオフでよい。
        """
        entry_id = self.bind(agent_type="issue-fixer", agent_id="fix")
        directory = (
            self.root / ".claude" / "worktrees" / "agent-fix" / "tmp" / "_handoff"
        )
        directory.mkdir(parents=True)
        (directory / "issue-fixer--issue-354-r1.yaml").write_text(
            "agent: issue-fixer\nstatus: stop\nstop_reason: ブランチを取得できない\n",
            encoding="utf-8",
        )
        self.write_active({"issue": 354, "round": 1})
        subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-fixer", "agent_id": "fix"}),
            stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
            runner=self.runner(FakeCompleted(0), FakeCompleted(0)),
        )
        self.assertSilentAllow()
        argv = self.collect_calls()[0]
        self.assertIn("tmp/_handoff/issue-fixer--issue-354-r1.yaml", argv)
        self.assertEqual(self.status_of(entry_id), "stopped")

    def test_already_collected_entry_is_released_without_rediscovering_handoff(self):
        """回収済みなら handoff を探し直さない（重複再検出で詰まらせない・#423 案3）。

        回収に成功したあと解放だけが失敗すると（worktree が git lock 中など）、台帳は
        ``collected`` で worktree は残る。次の停止で handoff を探し直すと、回収済みの
        ファイルや委譲先の handoff を再検出して ``ambiguous`` → ``stale`` に落ち、
        解放をやり直せなくなる。``collected`` なら探索段ごと飛ばす。
        """
        entry_id = self.bind()
        self.write_handoff(
            "abc",
            "issue-implementer--issue-354.yaml",
            "issue-implementer--issue-354-r2.yaml",
        )
        for status in ("stopped", "collected"):
            worktree_ledger.mark(self.root, entry_id, status, now=FIXED_NOW)
        self.stop()
        argv = self.collect_calls()[0]
        self.assertEqual(argv[1:], ["-m", "gitgate", "collect-worktree", "--entry", entry_id])
        self.assertNotIn("--handoff", argv)
        self.assertEqual(self.status_of(entry_id), "collected", "解放するのは gitgate 側")

    def test_multiple_handoff_candidates_are_not_released(self):
        """どれが今回の成果物か決められないなら**解放しない**（成果物喪失を避ける）。"""
        entry_id = self.bind()
        self.write_handoff(
            "abc",
            "issue-implementer--issue-354.yaml",
            "issue-implementer--issue-354-r2.yaml",
        )
        self.stop()
        self.assertEqual(self.collect_calls(), [], "回収対象が曖昧なら起動もしない")
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())

    def test_symlinked_handoff_directory_is_not_treated_as_missing(self):
        """F-354-07: `tmp/_handoff` が symlink なら「列挙して0件」に丸めず解放しない。

        旧実装は ``directory.is_symlink() or not directory.is_dir()`` を一括で
        ``"empty"`` に倒しており、symlink 越しに誘導された（実際には中身があるかもしれない）
        ディレクトリを「回収するものが無いと確認した」と誤認していた。symlink を辿らず、
        列挙もせず、``--allow-missing-handoff`` を使わずに ``stale`` へ落とすことを確認する。
        """
        entry_id = self.bind()
        worktree_dir = self.root / ".claude" / "worktrees" / "agent-abc"
        elsewhere = self.root / "elsewhere-handoff"
        elsewhere.mkdir()
        (elsewhere / "issue-implementer--issue-354.yaml").write_text(
            "agent: issue-implementer\n", encoding="utf-8"
        )
        (worktree_dir / "tmp").mkdir(parents=True)
        (worktree_dir / "tmp" / "_handoff").symlink_to(elsewhere, target_is_directory=True)
        self.stop()
        self.assertEqual(self.collect_calls(), [], "symlink は列挙せず起動もしない")
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue(worktree_dir.is_dir(), "回収できないので worktree は残す")
        reasons = [line.get("reason") for line in self.evidence_lines()]
        self.assertIn("HANDOFF_AMBIGUOUS", reasons)

    def test_non_directory_handoff_path_is_not_treated_as_missing(self):
        """`tmp/_handoff` が regular file（非ディレクトリ）でも同様に解放しない。"""
        entry_id = self.bind()
        worktree_dir = self.root / ".claude" / "worktrees" / "agent-abc"
        (worktree_dir / "tmp").mkdir(parents=True)
        (worktree_dir / "tmp" / "_handoff").write_text("not a directory\n", encoding="utf-8")
        self.stop()
        self.assertEqual(self.collect_calls(), [], "非ディレクトリは列挙せず起動もしない")
        self.assertEqual(self.status_of(entry_id), "stale")
        self.assertTrue(worktree_dir.is_dir())

    def test_entry_not_found_marks_only_the_open_entry_stale(self):
        """自分のエントリを引けないとき、他人の `running` を `stale` へ落とさない。

        `running` → `stale` は `WORKTREE_LIVE` の保護を外す＝live な worktree を
        `--force-uncollected` で強制解放できる状態にする。推測でそこへ落とすのは
        「削除は fail-safe 側へ倒す」に反するので、落としてよいのは**まだ何も掴んで
        いない** `open` だけにする。
        """
        live = self.bind(agent_id="live")
        pending = worktree_ledger.open_entry(
            self.root, issue=354, agent_type="issue-implementer", round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )
        self.stop(agent_id="unbound-id")
        self.assertEqual(self.status_of(live), "running", "他人の live を潰さない")
        self.assertEqual(self.status_of(pending), "stale")
        self.assertEqual(self.collect_calls(), [])

    def test_no_ledger_entry_at_all_deletes_nothing(self):
        self.make_worktree("agent-abc")
        self.stop()
        self.assertEqual(self.entries(), [], "エントリを新規作成しない")
        self.assertEqual(self.collect_calls(), [])
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())
        reasons = [line.get("reason") for line in self.evidence_lines()]
        self.assertIn("ENTRY_NOT_FOUND", reasons)

    def test_unresolvable_repo_root_deletes_nothing(self):
        (self.root / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        self.stop()
        reasons = [line.get("reason") for line in self.evidence_lines()]
        self.assertIn("REPO_ROOT_UNRESOLVED", reasons)
        self.assertEqual(self.collect_calls(), [])

    def test_terminal_entry_is_left_alone(self):
        entry_id = self.bind()
        for status in ("stopped", "collected", "released"):
            worktree_ledger.mark(self.root, entry_id, status, now=FIXED_NOW)
        self.stop()
        self.assertEqual(self.status_of(entry_id), "released")
        self.assertEqual(self.collect_calls(), [])

    def test_release_pending_entry_is_skipped_at_subagent_stop(self):
        """Issue #464: 回収済み・削除だけ git ロックで遅延したエントリの再停止では何もしない。

        ロックはこの停止イベントの時点ではまだエージェントプロセスが握っているので
        ``collect-worktree`` を再起動しても無駄。削除は次 dispatch の gate が引き取る。
        台帳を ``stale`` にも進めず、worktree も消さない。
        """
        entry_id = self.bind()
        for status in ("stopped", "collected", "release_pending"):
            worktree_ledger.mark(self.root, entry_id, status, now=FIXED_NOW)
        self.stop()
        self.assertEqual(self.collect_calls(), [], "release_pending では回収を起動しない")
        self.assertEqual(self.status_of(entry_id), "release_pending", "台帳を進めない")
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-abc").is_dir())
        reasons = [line.get("reason") for line in self.evidence_lines()]
        self.assertIn("RELEASE_PENDING_DEFERRED", reasons)

    def test_release_stage_is_idempotent_for_a_repeated_stop(self):
        """FR-W5: 同じ停止が2回届いても状態機械は壊れない（`stopped` は冪等）。"""
        entry_id = self.bind()
        self.write_handoff("abc", "issue-implementer--issue-354.yaml")
        for _round in range(2):
            self.stdout, self.stderr = io.StringIO(), io.StringIO()
            self.stop()
        self.assertEqual(len(self.collect_calls()), 2)
        self.assertEqual(self.status_of(entry_id), "stopped")

    def test_fixer_blocked_by_the_karte_gate_never_reaches_the_release_stage(self):
        """**最重要の競合ケース**: block＝エージェントは継続する＝worktree を消してはならない。"""
        entry_id = self.bind(agent_type="issue-fixer", agent_id="fix")
        self.write_handoff("fix", "issue-fixer--issue-354-r1.yaml")
        self.write_active({"issue": 354, "round": 1})
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-fixer", "agent_id": "fix"}),
            stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
            runner=self.runner(FakeCompleted(4, stderr="NG: 未クローズの Attempt")),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(self.stdout.getvalue())["decision"], "block")
        self.assertEqual(self.collect_calls(), [], "block したら解放段へ進まない")
        self.assertEqual(self.status_of(entry_id), "running", "台帳も進めない")
        self.assertTrue((self.root / ".claude" / "worktrees" / "agent-fix").is_dir())

    def test_fixer_passing_the_karte_gate_reaches_the_release_stage(self):
        entry_id = self.bind(agent_type="issue-fixer", agent_id="fix")
        self.write_handoff("fix", "issue-fixer--issue-354-r1.yaml")
        self.write_active({"issue": 354, "round": 1})
        subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-fixer", "agent_id": "fix"}),
            stdout=self.stdout, stderr=self.stderr,
            cwd=self.root, now=FIXED_NOW,
            runner=self.runner(FakeCompleted(0), FakeCompleted(0)),
        )
        self.assertSilentAllow()
        self.assertEqual(self.runner_calls[0][2], "karte")
        self.assertEqual(len(self.collect_calls()), 1)
        self.assertEqual(self.status_of(entry_id), "stopped")


@unittest.skipUnless(_HAS_GIT, "git が無い環境では実 worktree の統合検証をしない")
class ReleaseStageIntegrationTests(unittest.TestCase):
    """`SubagentStop` → 実 `gitgate collect-worktree` の**通し**検証（Issue #354 PR-3）。

    単体テストは `runner` を差し替えるため「argv を組み立てた」ところまでしか見ない。
    ここでは実 git リポジトリ・実 linked worktree・実 `gitgate` サブプロセスで、
    **`running` → `stopped` → `collected` → `released` が最後まで通る**ことを確かめる。
    この通しが無いと F-354-01（`running` のまま `collect-worktree` を呼んで
    `WORKTREE_LIVE` で必ず落ちる）と同種の取りこぼしを検出できない。
    """

    ISSUE = 354
    HANDOFF = "issue-implementer--issue-354.yaml"

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
        self.repo = Path(self._tmp.name).resolve() / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "init")
        self.worktree_rel = ".claude/worktrees/agent-int01"
        (self.repo / ".claude" / "worktrees").mkdir(parents=True)
        self.git("worktree", "add", "--detach", "-q", self.worktree_rel, "HEAD")
        handoff_dir = self.repo / self.worktree_rel / "tmp" / "_handoff"
        handoff_dir.mkdir(parents=True)
        (handoff_dir / self.HANDOFF).write_text(
            "agent: issue-implementer\nstatus: pr_opened\n", encoding="utf-8"
        )
        worktree_ledger.open_entry(
            self.repo, issue=self.ISSUE, agent_type="issue-implementer", round=None,
            branch_name="claude/issue-354", handoff_path=None, now=FIXED_NOW,
        )
        self.entry_id = worktree_ledger.bind_agent(
            self.repo, agent_type="issue-implementer", agent_id="int01",
            worktree_path=self.worktree_rel,
        )

    def real_runner(self, argv, **kwargs):
        """実サブプロセス実行（`gitgate` を import できるよう PYTHONPATH を渡す）。"""
        return subprocess.run(
            argv, env={**os.environ, "PYTHONPATH": str(ROOT)}, **kwargs
        )

    def entry(self):
        return worktree_ledger.find_by_agent_id(self.repo, "int01")

    def test_stop_collects_the_handoff_and_releases_the_worktree(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = subagent_hooks.run_stop(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "agent_id": "int01",
            })),
            stdout=stdout, stderr=stderr,
            cwd=self.repo, now=FIXED_NOW, runner=self.real_runner,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "解放段は停止をブロックしない")

        entry = self.entry()
        self.assertEqual(entry["status"], "released")
        # 回収物がメインワークツリーへ退避され、内容が保たれている。
        collected = self.repo / entry["collected_to"]
        self.assertTrue(collected.is_file(), entry["collected_to"])
        self.assertIn("status: pr_opened", collected.read_text(encoding="utf-8"))
        self.assertTrue(entry["collected_to"].startswith("tmp/_handoff/collected/"))
        # 実体も git の登録も消えている（FR-W12: `git worktree list` で事後検証できる）。
        self.assertFalse((self.repo / self.worktree_rel).exists())
        listing = self.git("worktree", "list", "--porcelain").stdout
        self.assertNotIn("agent-int01", listing)

    def test_stop_does_not_release_when_the_handoff_cannot_be_read(self):
        """回収に失敗したら**解放しない**（FR-W2）。worktree は残り、台帳は `stale`。"""
        target = self.repo / self.worktree_rel / "tmp" / "_handoff" / self.HANDOFF
        target.unlink()
        # symlink は `collect-worktree` の `resolve_within` が拒否する（回収不能の一例）。
        target.symlink_to(self.repo / "README.md")
        stdout, stderr = io.StringIO(), io.StringIO()
        subagent_hooks.run_stop(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "agent_id": "int01",
            })),
            stdout=stdout, stderr=stderr,
            cwd=self.repo, now=FIXED_NOW, runner=self.real_runner,
        )
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.entry()["status"], "stale")
        self.assertTrue((self.repo / self.worktree_rel).is_dir(), "解放していない")

    def test_a_running_entry_is_never_released_by_gitgate(self):
        """FR-W3 の直接検証: `running` のまま呼ぶと `gitgate` が `WORKTREE_LIVE` で拒む。

        解放段が `stopped` 遷移を落としたら、この経路に落ちて自動解放が一度も
        成功しなくなる（F-354-01 の再発検出器）。
        """
        completed = self.real_runner(
            subagent_hooks.collect_worktree_argv(
                self.entry_id, handoff=f"tmp/_handoff/{self.HANDOFF}"
            ),
            cwd=str(self.repo), text=True, capture_output=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("WORKTREE_LIVE", completed.stderr)
        self.assertTrue((self.repo / self.worktree_rel).is_dir())
        self.assertEqual(self.entry()["status"], "running")

    def test_release_is_idempotent_for_a_repeated_stop(self):
        """FR-W5: 解放後にもう一度停止が届いても壊れない（終端状態は素通し）。"""
        payload = json.dumps({"agent_type": "issue-implementer", "agent_id": "int01"})
        for _round in range(2):
            stdout = io.StringIO()
            rc = subagent_hooks.run_stop(
                stdin=io.StringIO(payload), stdout=stdout, stderr=io.StringIO(),
                cwd=self.repo, now=FIXED_NOW, runner=self.real_runner,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.entry()["status"], "released")

    def test_locked_worktree_defers_release_then_the_gate_finishes_it(self):
        """Issue #464 の通し回帰（実 git・実 worktree ロック）。

        SubagentStop 時点で worktree が git ロックされていると ``git worktree remove`` が
        失敗する。handoff の回収（main worktree 側への退避）は成功しているので ``stale`` に
        落とさず ``release_pending`` にし、次 dispatch の gate（``assert_no_worktree_residue``）
        がロックの外れた後に削除を完了させる。手動の ``collect-worktree`` /
        ``worktree-release --force-uncollected`` を要しない。
        """
        from issue_start.gate import assert_no_worktree_residue

        self.git("worktree", "lock", self.worktree_rel)
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = subagent_hooks.run_stop(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "agent_id": "int01",
            })),
            stdout=stdout, stderr=stderr,
            cwd=self.repo, now=FIXED_NOW, runner=self.real_runner,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "解放段は停止をブロックしない")

        entry = self.entry()
        self.assertEqual(entry["status"], "release_pending", "stale に落とさない")
        collected = self.repo / entry["collected_to"]
        self.assertTrue(collected.is_file(), entry["collected_to"])
        self.assertIn("status: pr_opened", collected.read_text(encoding="utf-8"))
        self.assertTrue((self.repo / self.worktree_rel).is_dir(), "削除はロックで失敗")

        # 次 dispatch: 残留判定は release_pending を residue/unclaimed として扱わない。
        # ロックが外れた（＝エージェント終了）想定で unlock してから gate を回す。
        self.git("worktree", "unlock", self.worktree_rel)
        report = assert_no_worktree_residue(
            repo_root=self.repo, now=FIXED_NOW, runner=subprocess.run
        )
        self.assertEqual(report["stale"], [])
        self.assertEqual(report["unclaimed"], [])
        finished = report["deferred_release_finished"]
        self.assertEqual([item["entry_id"] for item in finished], [entry["entry_id"]])
        self.assertTrue(finished[0]["released"])
        self.assertEqual(self.entry()["status"], "released")
        self.assertFalse((self.repo / self.worktree_rel).exists())


class NoDeletionPathTests(HookTestCase):
    """解放は `gitgate collect-worktree` 経由に限る（フックは直接 worktree を消さない）。

    PR-1（#309）では「worktree を1つも削除しない」が不変条件だった。PR-3（#354）で
    自動解放が入ったが、**実体を消す判断（台帳の状態・パス形状・git 管理下かの検査・
    回収→検証→解放の段構造）は `gitgate/worktree.py` に集約されたまま**である。
    ここではフック側に削除経路が生えていないことを固定する。
    """

    def test_hooks_never_spawn_a_bare_worktree_remove(self):
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
                cwd=self.root, now=FIXED_NOW, runner=self.runner(completed),
            )
        self.assertTrue(self.runner_calls, "karte check は起動されている（前提の確認）")
        for call in self.runner_calls:
            self.assertNotIn("git", call)
            self.assertNotIn("worktree", call, "裸の `worktree` サブコマンドは現れない")
            self.assertNotIn("remove", call)
        # worktree ディレクトリも台帳エントリも、フック自身の手では消えていない。
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

    def test_collect_argv_can_never_ask_for_a_missing_handoff_release(self):
        """フックは ``--allow-missing-handoff`` を**組み立てられない**（Issue #423）。

        「回収するものが無いことを列挙で確認した」という判断は、入れ子委譲待ちの一時停止と
        見分けがつかない以上フックが自動で下してよいものではない。判断の是非を検査で守るのでは
        なく、**その argv を作る経路自体を無くす**ことで構造的に守る（同フラグは ``gitgate``
        側に残り、主文脈が明示的に使う operator 用の逃げ道であり続ける）。
        """
        for handoff in (None, "tmp/_handoff/issue-implementer--issue-423.yaml"):
            with self.subTest(handoff=handoff):
                argv = subagent_hooks.collect_worktree_argv("wl-0123456789ab", handoff=handoff)
                self.assertNotIn("--allow-missing-handoff", argv)
                self.assertNotIn("--reason", argv)
        source = (ROOT / "issue_start" / "subagent_hooks.py").read_text(encoding="utf-8")
        literals = {
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("--allow-missing-handoff", literals)


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
        self.assertEqual(len(pre_tool_use), 4)
        self.assertEqual(
            pre_tool_use[0],
            "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/pr-merge-gate.sh",
        )
        self.assertEqual(
            pre_tool_use[3],
            "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/issue-start-gate.sh",
        )
        self.assertEqual(
            self.commands("PostToolUse"),
            [
                "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/pr-merge-gate.sh",
                "${CLAUDE_PROJECT_DIR}/.claude/hooks/check-governance-drift.sh",
            ],
        )
        self.assertEqual(
            self.commands("UserPromptSubmit"),
            ["${CLAUDE_PROJECT_DIR}/.claude/hooks/inject-governance.sh"],
        )

    def test_gate_registrations_quote_project_dir(self):
        commands = [
            command
            for command in self.commands("PreToolUse")
            if "agent-command-gate.sh" in command
        ]
        self.assertEqual(
            commands,
            [
                "\"${CLAUDE_PROJECT_DIR}/.claude/hooks/agent-command-gate.sh\"",
                "\"${CLAUDE_PROJECT_DIR}/.claude/hooks/agent-command-gate.sh\"",
            ],
        )


class ParallelStopLockContentionTests(HookTestCase):
    """並列 dispatch が同時に停止イベントを起こしたときの台帳ロック競合（Issue #423 の案4）。

    #423 は「根本原因バグが1 dispatch あたりのロック取得・解放回数を水増しするため、
    並列度と組み合わさるとロック競合リスクが増える」と**理論的リスク**として指摘し、
    実測は未了だった。ここでその実測を置く。

    * 保留（``running`` のまま何もしない）に変わったことで、**入れ子委譲1回あたりの
      ロック取得回数は 2（``stopped`` + ``stale``）から 0〜1（初回の note だけ）へ減る**。
      増幅要因そのものが消えるので、タイムアウト値を触る前にまず母数が下がる。
    * ``_acquire_lock`` は wall clock を読まず「``LOCK_RETRY_INTERVAL_S``（50ms）× 固定回数」で
      待つ。既定 5.0 秒＝**100 回**のリトライで、臨界区間は JSON の読み書き1往復（ミリ秒未満）。

    下の2本は、既定値のまま並列停止が詰まらないことを機械的に固定する（値を変える提案を
    する場合、この2本が「変える必要がある」ことの根拠になるべき検出器）。
    """

    def test_concurrent_ledger_updates_all_succeed_under_the_default_timeout(self):
        import threading

        worktree_ledger.open_entry(
            self.root, issue=423, agent_type="issue-implementer", round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )
        entry_id = self.entries()[0]["entry_id"]
        writers = 8
        rounds = 5
        errors: list = []
        barrier = threading.Barrier(writers)

        def worker(index):
            try:
                barrier.wait()
                for step in range(rounds):
                    worktree_ledger.add_note(
                        self.root, entry_id, now=FIXED_NOW, note=f"w{index}-{step}"
                    )
            except Exception as exc:  # LEDGER_LOCK_TIMEOUT 等を落とさず集める
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(writers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([str(item) for item in errors], [])
        notes = self.entries()[0]["notes"]
        self.assertEqual(len(notes), writers * rounds, "1件も取りこぼさない（原子的置換）")

    def test_the_deferred_path_takes_the_ledger_lock_at_most_once(self):
        """保留経路のロック取得回数を固定する（水増しの再発検出器）。

        旧実装は停止1回につき ``mark(stopped)`` と ``mark(stale)`` で必ず2回書いていた。
        新実装は初回の note だけで、2回目以降は**1回も書かない**。
        """
        entry_id = self.bind_running()
        acquired: list = []
        original = worktree_ledger._acquire_lock

        def counting(directory, **kwargs):
            acquired.append(str(directory))
            return original(directory, **kwargs)

        worktree_ledger._acquire_lock = counting
        self.addCleanup(setattr, worktree_ledger, "_acquire_lock", original)
        for _round in range(3):
            self.stdout, self.stderr = io.StringIO(), io.StringIO()
            subagent_hooks.run_stop(
                stdin=self.stdin({"agent_type": "issue-implementer", "agent_id": "abc"}),
                stdout=self.stdout, stderr=self.stderr,
                cwd=self.root, now=FIXED_NOW, runner=self.runner(),
            )
        self.assertEqual(len(acquired), 1, "初回の note だけ／2回目以降は書かない")
        self.assertEqual(
            {item["entry_id"]: item for item in self.entries()}[entry_id]["status"], "running"
        )

    def bind_running(self):
        path = self.root / ".claude" / "worktrees" / "agent-abc"
        path.mkdir(parents=True)
        worktree_ledger.open_entry(
            self.root, issue=423, agent_type="issue-implementer", round=None,
            branch_name=None, handoff_path=None, now=FIXED_NOW,
        )
        return worktree_ledger.bind_agent(
            self.root, agent_type="issue-implementer", agent_id="abc",
            worktree_path=".claude/worktrees/agent-abc",
        )


if __name__ == "__main__":
    unittest.main()
