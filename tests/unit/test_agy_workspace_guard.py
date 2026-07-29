"""agy-workspace-guard.sh（PreToolUse ゲート）の判定テスト。

守っている不変条件（PR #259 の調査で確定）:
  agy ブリッジは workspace を Windows Python の os.path.abspath で解決するため、ドライブレターの
  無い "/home/..." は MCP サーバの cwd 次第で別物になり、続く os.makedirs が**その空ディレクトリを
  無言で新規作成**する。agy はリポジトリを開かないまま自信のある回答を返し、エラーは出ない。
  → workspace は必ず「実在する Windows 絶対パス」で agy に届くこと（Linux パスは自動変換で救済）。

Codex レビュー（#259）で塞いだ穴もここで固定する:
  - updatedInput が tool_input 全体を保持すること（prompt 等の欠落＝BLOCKER）
  - 正規化時に permissionDecision フィールド自体を出力しないこと（許可判断を握らない
    ＝ no decision。明示的な "defer" を返すこととは別物なので、そう書かないこと）
  - agent_swarm / image_swarm が matcher と必須判定から漏れないこと
  - 実在しない Windows パス・未知構造・非 object ペイロードで fail-open しないこと
  - 終了要求に応答しない検査プロセスを内部期限内に強制終了して deny を返すこと
  - 内部完了表明の無い stdout（無出力・混在出力）を素通しさせないこと
  - tool_name の欠落・型不正・agy 名前空間外を deny すること（第4巡 HIGH）
  - 判定 JSON の構文・スキーマ・完了ステータスとの整合を外殻が検証すること（第4巡 BLOCKER）
  - wslpath 変換の往復が変換元と同一ディレクトリを指すこと（第4巡 MEDIUM）
  - `agy` / `gemini`（antigravity の確認済み alias）も変換対象になること（第4巡 LOW）
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "agy-workspace-guard.sh"
_HAS_BASH = shutil.which("bash") is not None

# wslpath は WSL にしか無いが、主要な回帰（入力全保持・権限判断不返却・変換の往復・
# 未知ツール deny）を WSL 以外の CI で skip すると守れない。実物が無ければ **同じ規則の
# 代替を PATH に差し込んで**全環境で回す（Codex 再レビュー MEDIUM: 環境依存 skip）。
_FAKE_WSLPATH = r"""#!/usr/bin/env python3
import sys
flag, path = sys.argv[1], sys.argv[2]
if flag == "-w":
    if path.startswith("/mnt/") and len(path) > 6:
        d = path[5]; sys.stdout.write(d.upper() + ":\\" + path[7:].replace("/", "\\"))
    else:
        sys.stdout.write("\\\\wsl.localhost\\Ubuntu" + path.replace("/", "\\"))
else:
    p = path.replace("\\", "/")
    if p.startswith("//wsl.localhost/Ubuntu"):
        sys.stdout.write(p[len("//wsl.localhost/Ubuntu"):] or "/")
    elif len(p) > 1 and p[1] == ":":
        sys.stdout.write("/mnt/" + p[0].lower() + p[2:])
    else:
        sys.stdout.write(p)
sys.stdout.write("\n")
"""

_shim_dir = None
# subprocess へ渡す env。shim を使うときだけ PATH を差し替えた**複製**を持つ。
# os.environ を書き換えると、復元漏れが同一プロセス内の他テストへ漏れる（Codex 第3巡 MEDIUM）。
#
# 下2つは setUpModule() で必ず代入される。**値を持たない型注釈だけ**にしてあるのは、
# `= None` にすると型が `X | None` に広がり全参照箇所が Optional 扱いになる（型チェッカの誤検知）ため。
# 注釈のみなら setUpModule が走らなかったときに NameError で即落ちる＝None が紛れ込むより失敗が早い。
ENV: dict[str, str]
# ROOT に対応する Windows 絶対パス。固定の `C:\...` を書くと純 Linux + shim 環境で
# 実在確認に失敗するので、**必ず ROOT から導出する**（同上）。
WIN_ROOT: str


def _wslpath(flag, path, env=None):
    return subprocess.run(
        ["wslpath", flag, path], capture_output=True, text=True, check=True, env=env
    ).stdout.strip()


def _real_wslpath_usable():
    """本物の wslpath が「PATH にある」ではなく「実際に往復変換できる」かを probe する。

    PATH 上に名前だけあって実行不能・別物というケースで shim が使われないと、
    以降のテストが環境依存で落ちる。
    """
    if shutil.which("wslpath") is None:
        return False
    try:
        win = _wslpath("-w", str(ROOT))
        if not (win.startswith("\\\\") or win[1:3] == ":\\"):
            return False
        back = _wslpath("-u", win)
    except (OSError, subprocess.SubprocessError):
        return False
    return os.path.realpath(back) == os.path.realpath(str(ROOT))


def setUpModule():
    """wslpath が使えない環境では代替を用意し、subprocess の env にだけ差し込む。"""
    global _shim_dir, ENV, WIN_ROOT
    ENV = dict(os.environ)
    if not _real_wslpath_usable():
        _shim_dir = tempfile.mkdtemp(prefix="wslpath_shim_")
        shim = Path(_shim_dir) / "wslpath"
        shim.write_text(_FAKE_WSLPATH, encoding="utf-8")
        shim.chmod(0o755)
        ENV["PATH"] = f"{_shim_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    WIN_ROOT = _wslpath("-w", str(ROOT), env=ENV)


def tearDownModule():
    if _shim_dir:
        shutil.rmtree(_shim_dir, ignore_errors=True)


def win_child(name):
    """WIN_ROOT 配下の Windows パスを組み立てる（固定パスを書かないため）。"""
    return WIN_ROOT.rstrip("\\") + "\\" + name


def run_guard(payload, env=None):
    """フックを実行し、返った hookSpecificOutput（無出力＝素通しなら None）を返す。"""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    result = subprocess.run(
        [str(HOOK)], input=raw, text=True, capture_output=True, check=True,
        env=env if env is not None else ENV,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def expect_decision(payload, env=None, msg="判定が返るべき入力が素通しした"):
    """フックが何か返すことを要求し、その hookSpecificOutput を返す（素通しなら失敗）。

    `run_guard` は素通し時に None を返すので、呼び出し側で assertIsNotNone してから
    添字アクセスすると型チェッカが narrowing できない。**素通しを許さないケースは必ず
    こちらを使う**こと（None を戻り値から締め出す）。
    """
    out = run_guard(payload, env=env)
    if out is None:
        raise AssertionError(msg)
    return out


# 内部期限(10s) + kill-after(2s) を上回る余裕。settings.json の外殻 25s は超えない。
HANG_TIMEOUT = 20


def run_with_fake_python(script):
    """検査本体(python3)を差し替えてフックを実行し、返った hookSpecificOutput を返す。

    フックは `python3 - <payload> <verdict>` で呼ぶので、代替側から見て $2=payload・$3=verdict。
    """
    d = tempfile.mkdtemp(prefix="fakepy_")
    try:
        fake = Path(d) / "python3"
        fake.write_text(script, encoding="utf-8")
        fake.chmod(0o755)
        env = dict(ENV, PATH=f"{d}{os.pathsep}{ENV['PATH']}")
        r = subprocess.run(
            [str(HOOK)], input=json.dumps(ask(prompt="x")), text=True,
            capture_output=True, check=True, env=env, timeout=HANG_TIMEOUT,
        )
        return json.loads(r.stdout)["hookSpecificOutput"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def ask(**tool_input):
    return {"tool_name": "mcp__agy__antigravity_ask", "tool_input": tool_input}


def swarm(*tasks):
    return {"tool_name": "mcp__agy__agent_swarm", "tool_input": {"tasks": list(tasks)}}


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestScope(unittest.TestCase):
    """検査対象の絞り込み。過剰拒否しないこと。"""

    def test_other_backend_tool_without_workspace_passes_through(self):
        # codex/copilot/cursor は同じブリッジだが Windows 形式を期待するか未検証＝対象外（意図的）。
        self.assertIsNone(
            run_guard({"tool_name": "mcp__agy__codex_status", "tool_input": {}})
        )

    def test_status_without_workspace_passes_through(self):
        # workspace を取らないツールを必須扱いして塞がないこと。
        self.assertIsNone(
            run_guard({"tool_name": "mcp__agy__antigravity_status", "tool_input": {}})
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestDeny(unittest.TestCase):
    def _deny_reason(self, payload):
        out = expect_decision(payload)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertNotIn("updatedInput", out, "deny 時に入力を書き換えないこと")
        return out["permissionDecisionReason"]

    def test_missing_workspace_is_denied(self):
        # 省略＝cwd 依存。これが「別ツリーを見たまま答える」事故の入口だった。
        self.assertIn("workspace", self._deny_reason(ask(prompt="x")))

    def test_relative_path_is_denied(self):
        self.assertIn("相対パス", self._deny_reason(ask(workspace="./docs", prompt="x")))

    def test_nonexistent_linux_directory_is_denied(self):
        self.assertIn(
            "存在しない",
            self._deny_reason(ask(workspace="/home/__no_such_dir_for_test__", prompt="x")),
        )

    def test_nonexistent_windows_directory_is_denied(self):
        # 旧版は Windows 形式なら無検証で通していた。存在しない Windows パスはブリッジ側
        # makedirs が作ってしまう典型なので、ここで止める。
        # パスは WIN_ROOT から導出する（固定 `C:\...` は shim 環境で実在確認できない）。
        self.assertIn(
            "存在しない",
            self._deny_reason(ask(workspace=win_child("__no_such_dir_for_test__"), prompt="x")),
        )

    def test_empty_workspace_is_denied(self):
        self._deny_reason(ask(workspace="   ", prompt="x"))

    def test_unparsable_payload_fails_closed(self):
        self._deny_reason("not json at all")

    def test_non_object_payload_fails_closed(self):
        self.assertIn("object でない", self._deny_reason([1, 2, 3]))

    def test_swarm_task_without_workspace_is_denied(self):
        # matcher が antigravity_ 前方一致だった頃はここが素通りしていた（Codex 指摘のバイパス）。
        self.assertIn(
            "workspace",
            self._deny_reason(swarm({"backend": "antigravity", "prompt": "x"})),
        )

    def test_swarm_task_without_backend_is_denied(self):
        self.assertIn(
            "backend",
            self._deny_reason(swarm({"prompt": "x", "workspace": str(ROOT)})),
        )

    def test_swarm_unknown_task_structure_is_denied(self):
        # 未知構造を素通しにすると検査を回避できてしまう（fail-open を塞ぐ）。
        self._deny_reason(swarm("not-an-object"))

    def test_image_swarm_without_workspaces_is_denied(self):
        self.assertIn(
            "workspaces",
            self._deny_reason(
                {
                    "tool_name": "mcp__agy__antigravity_image_swarm",
                    "tool_input": {"prompts": ["a"]},
                }
            ),
        )

    def test_empty_workspaces_list_is_denied(self):
        self._deny_reason(
            {
                "tool_name": "mcp__agy__antigravity_image_swarm",
                "tool_input": {"prompts": ["a"], "workspaces": []},
            }
        )

    def test_too_many_items_is_denied(self):
        self.assertIn(
            "上限",
            self._deny_reason(
                {
                    "tool_name": "mcp__agy__antigravity_image_swarm",
                    "tool_input": {"prompts": ["a"], "workspaces": [str(ROOT)] * 65},
                }
            ),
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestToolName(unittest.TestCase):
    """tool_name そのものが検査の起点。壊れていたら素通しさせない（Codex 第4巡 HIGH）。

    本フックは settings.json の matcher `mcp__agy__.*` 専用なので、ここへ届く payload の
    tool_name は必ず agy 名前空間の文字列のはず。欠落・型不正・名前空間外は「payload が壊れて
    いる」か「matcher が変わった」のどちらかで、いずれも検査が成立していない＝fail-close する。
    """

    def _deny_reason(self, payload):
        out = expect_decision(payload)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertNotIn("updatedInput", out, "deny 時に入力を書き換えないこと")
        return out["permissionDecisionReason"]

    def test_non_agy_tool_name_is_denied(self):
        # 旧版は素通ししていた（agy 以外は対象外という扱い）。matcher が agy 専用である以上、
        # ここに非 agy が来ること自体が異常なので拒否する。
        self.assertIn(
            "agy 名前空間",
            self._deny_reason({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
        )

    def test_missing_tool_name_is_denied(self):
        self.assertIn("tool_name", self._deny_reason({"tool_input": {"workspace": str(ROOT)}}))

    def test_non_string_tool_name_is_denied(self):
        for bad in (123, ["mcp__agy__antigravity_ask"], {"a": 1}, None, True):
            with self.subTest(tool_name=bad):
                self.assertIn(
                    "tool_name", self._deny_reason({"tool_name": bad, "tool_input": {}})
                )

    def test_blank_tool_name_is_denied(self):
        self.assertIn("tool_name", self._deny_reason({"tool_name": "   ", "tool_input": {}}))


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestAllow(unittest.TestCase):
    def test_existing_windows_path_passes_unchanged(self):
        self.assertIsNone(
            run_guard(ask(workspace=WIN_ROOT, prompt="x")), "既に正しい値は書き換えないこと"
        )

    def test_linux_path_is_converted(self):
        out = expect_decision(ask(workspace=str(ROOT), prompt="x"))
        converted = out["updatedInput"]["workspace"]
        self.assertTrue(
            converted.startswith("\\\\") or converted[1:3] == ":\\",
            f"Windows 絶対パスでない: {converted!r}",
        )
        # 変換先が元と同じディレクトリを指していること（別ツリーへすり替えていない）。
        back = _wslpath("-u", converted, env=ENV)
        self.assertEqual(os.path.realpath(back), os.path.realpath(str(ROOT)))

    def test_updated_input_preserves_all_other_fields(self):
        """BLOCKER 回帰: updatedInput が workspace だけだと prompt が失われうる。"""
        out = expect_decision(
            ask(workspace=str(ROOT), prompt="KEEP_ME", timeout_s=180, watch=False)
        )
        updated = out["updatedInput"]
        self.assertEqual(updated["prompt"], "KEEP_ME")
        self.assertEqual(updated["timeout_s"], 180)
        self.assertIs(updated["watch"], False)

    def test_normalization_does_not_decide_permission(self):
        """正規化はフックの仕事だが、許可判断は通常フローに委ねる。

        `permissionDecision` フィールド**自体を出力しない**（= no decision）ことを固定する。
        明示的な `"defer"` を返すこととは別物なので、そう書かないこと。
        """
        out = expect_decision(ask(workspace=str(ROOT), prompt="x"))
        self.assertNotIn(
            "permissionDecision", out, "正規化時に許可判断を握らないこと（権限境界を動かさない）"
        )

    def test_swarm_antigravity_task_is_converted_and_keeps_siblings(self):
        out = expect_decision(
            swarm(
                {
                    "backend": "antigravity",
                    "prompt": "P",
                    "workspace": str(ROOT),
                    "model": "M",
                }
            )
        )
        task = out["updatedInput"]["tasks"][0]
        self.assertTrue(task["workspace"].startswith("\\\\") or task["workspace"][1:3] == ":\\")
        self.assertEqual(task["prompt"], "P")
        self.assertEqual(task["model"], "M")
        self.assertEqual(task["backend"], "antigravity")

    def test_swarm_antigravity_aliases_are_converted(self):
        """`agy` / `gemini` は antigravity の**確認済み alias**（Codex 第4巡 LOW）。

        出典＝ブリッジ `swarm.py` の `_BACKEND_ALIASES`（agy-mcp-bridge v0.21.4）で
        `antigravity` / `agy` / `gemini` はすべて antigravity に解決される。ここを取りこぼすと
        同じバックエンドが呼び方によって変換されたりされなかったりする。
        比較は `strip().lower()` なので大文字・前後空白も同一視されること。
        """
        for backend in ("antigravity", "agy", "gemini", "GEMINI", "  Agy  "):
            with self.subTest(backend=backend):
                out = expect_decision(
                    swarm({"backend": backend, "prompt": "P", "workspace": str(ROOT)})
                )
                ws = out["updatedInput"]["tasks"][0]["workspace"]
                self.assertTrue(
                    ws.startswith("\\\\") or ws[1:3] == ":\\", f"変換されていない: {ws!r}"
                )

    def test_other_backend_windows_path_passes_unchanged(self):
        """契約未検証のバックエンドでも、既に Windows 絶対パスなら触らず通す。

        パスは WIN_ROOT から導出する（固定 `C:\\Users` は純 Linux + shim 環境で実在しない）。
        """
        self.assertIsNone(
            run_guard(
                {
                    "tool_name": "mcp__agy__codex_ask",
                    "tool_input": {"workspace": WIN_ROOT, "prompt": "x"},
                }
            )
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestFailClose(unittest.TestCase):
    """検査できなかったときに素通しさせない（Codex 再レビュー BLOCKER）。

    非0終了は exit 2 以外ツール実行を止めないため、フックが落ちた・固まった場合に
    deny を返せないと、検証されていない入力のままツールが走ってしまう。
    """

    _run_with_fake_python = staticmethod(run_with_fake_python)

    def test_interpreter_crash_is_denied(self):
        out = self._run_with_fake_python("#!/bin/sh\nexit 3\n")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("異常終了", out["permissionDecisionReason"])

    def test_interpreter_hang_is_denied(self):
        out = self._run_with_fake_python("#!/bin/sh\nsleep 60\n")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("期限", out["permissionDecisionReason"])

    def test_interpreter_ignoring_termination_is_killed_and_denied(self):
        """終了要求を無視するプロセスも内部期限内に強制終了して deny すること。

        kill-after が無いと `timeout` は TERM を無視する子を待ち続け、settings.json 側の
        外殻期限(25s)でフックごと打ち切られる。そのとき deny を返せない＝未検査の入力が
        そのまま走る（fail-open・Codex 第3巡 BLOCKER）。
        """
        out = self._run_with_fake_python(
            '#!/bin/sh\ntrap "" TERM\nsleep 60 >/dev/null 2>&1 &\nwait\n'
        )
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("期限", out["permissionDecisionReason"])

    def test_silent_success_is_denied(self):
        """rc=0 でも完了表明が無ければ「検査できた」証拠が無いので素通しさせない。"""
        out = self._run_with_fake_python("#!/bin/sh\nexit 0\n")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("完了表明", out["permissionDecisionReason"])

    def test_unvalidated_stdout_is_not_forwarded(self):
        """rc=0 で任意の JSON を stdout に出しても、そのまま転送しないこと。

        旧版は非空 stdout を無検証で転送していたため、初期化出力や非 JSON が
        Claude Code 側の解析を壊し、元入力が続行され得た。
        """
        out = self._run_with_fake_python(
            '#!/bin/sh\necho "init noise"\necho \'{"hookSpecificOutput":{"permissionDecision":"allow"}}\'\nexit 0\n'
        )
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertNotIn("allow", json.dumps(out))

    def test_stray_stdout_around_verdict_does_not_break_decision(self):
        """判定 JSON は stdout でなく専用ファイルで受けるので、混在出力に汚されないこと。

        stdout に要求するのは**完了表明がちょうど1本あること**だけで、それ以外の行
        （sitecustomize 等の初期化ノイズ）は無視する契約。「stdout 全体が1行」ではない。

        フックは `python3 - <payload> <verdict>` で呼ぶので、代替側の $2=payload・$3=verdict。
        """
        out = self._run_with_fake_python(
            "#!/bin/sh\n"
            'echo "sitecustomize noise"\n'
            'printf \'{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"}}\\n\' > "$3"\n'
            'echo "AGY_GUARD_DONE:deny"\n'
            "exit 0\n"
        )
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertEqual(out["permissionDecisionReason"], "FAKE")


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestVerdictValidation(unittest.TestCase):
    """判定 JSON の構文・スキーマ・完了ステータス整合を外殻が検証すること（第4巡 BLOCKER）。

    旧版は `{"hookSpecificOutput":…}` という**外形一致**しか見ておらず、壊れた JSON でも転送した。
    転送先で解析が失敗すると判定そのものが失われ、元の入力のまま続行され得る＝fail-open。
    外殻生成の deny に落ちること（＝内部が申告した判定が採用されないこと）を固定する。
    """

    _VALID_DENY = (
        '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
        ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"}}'
    )

    _run_with_fake_python = staticmethod(run_with_fake_python)

    def _fake_writing(self, verdict_body, status="deny"):
        """代替 python3 に「任意の verdict を書いて status を表明する」振る舞いをさせる。"""
        return self._run_with_fake_python(
            "#!/bin/sh\n"
            f"printf '%s\\n' '{verdict_body}' > \"$3\"\n"
            f'echo "AGY_GUARD_DONE:{status}"\n'
            "exit 0\n"
        )

    def _assert_shell_deny(self, out):
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertNotIn("FAKE", json.dumps(out), "不正な判定を採用していないこと")
        return out["permissionDecisionReason"]

    def test_malformed_verdict_json_is_denied(self):
        # 途中で切れた JSON。外形は `{"hookSpecificOutput":` で始まるので旧版は通していた。
        self._assert_shell_deny(
            self._fake_writing(
                '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
                ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"'
            )
        )

    def test_verdict_with_unknown_permission_decision_is_denied(self):
        out = self._fake_writing(
            '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "permissionDecision": "allow", "permissionDecisionReason": "FAKE"}}'
        )
        self._assert_shell_deny(out)
        self.assertNotIn("allow", json.dumps(out))

    def test_verdict_with_wrong_hook_event_is_denied(self):
        self._assert_shell_deny(
            self._fake_writing(
                '{"hookSpecificOutput": {"hookEventName": "PostToolUse",'
                ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"}}'
            )
        )

    def test_verdict_with_extra_top_level_key_is_denied(self):
        self._assert_shell_deny(
            self._fake_writing(
                '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
                ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"},'
                ' "continue": false}'
            )
        )

    def test_status_deny_with_updated_input_verdict_is_denied(self):
        """完了表明が deny なのに中身が updatedInput＝内部矛盾。"""
        self._assert_shell_deny(
            self._fake_writing(
                '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
                ' "updatedInput": {"workspace": "FAKE"}}}',
                status="deny",
            )
        )

    def test_status_updated_with_deny_verdict_is_denied(self):
        """完了表明が updated なのに中身が deny＝内部矛盾。"""
        self._assert_shell_deny(self._fake_writing(self._VALID_DENY, status="updated"))

    def test_status_pass_with_verdict_file_is_denied(self):
        """pass を名乗りながら判定 JSON を書いているのは矛盾（素通しさせない）。"""
        self._assert_shell_deny(self._fake_writing(self._VALID_DENY, status="pass"))

    def test_multiline_verdict_is_denied(self):
        out = self._run_with_fake_python(
            "#!/bin/sh\n"
            'printf \'{"hookSpecificOutput":\\n{"hookEventName": "PreToolUse",'
            ' "permissionDecision": "deny", "permissionDecisionReason": "FAKE"}}\\n\' > "$3"\n'
            'echo "AGY_GUARD_DONE:deny"\n'
            "exit 0\n"
        )
        self._assert_shell_deny(out)

    def test_empty_verdict_file_is_denied(self):
        out = self._run_with_fake_python(
            "#!/bin/sh\n: > \"$3\"\necho \"AGY_GUARD_DONE:deny\"\nexit 0\n"
        )
        self.assertEqual(out["permissionDecision"], "deny")

    def test_valid_deny_verdict_is_forwarded(self):
        """対偶: スキーマに適合していれば内部の判定はそのまま転送されること（過剰拒否しない）。"""
        out = self._fake_writing(self._VALID_DENY)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertEqual(out["permissionDecisionReason"], "FAKE")

    def test_valid_updated_verdict_is_forwarded(self):
        out = self._fake_writing(
            '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "updatedInput": {"workspace": "W", "prompt": "KEEP", "n": 1, "b": true}}}',
            status="updated",
        )
        self.assertEqual(out["updatedInput"]["prompt"], "KEEP")
        self.assertNotIn("permissionDecision", out)


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestUnknownTool(unittest.TestCase):
    def test_unknown_agy_tool_is_denied(self):
        """将来 workspace を取るツールが増えたとき、列挙漏れで素通ししない。"""
        out = expect_decision({"tool_name": "mcp__agy__future_tool", "tool_input": {"foo": 1}})
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("未知", out["permissionDecisionReason"])

    def test_unknown_agy_tool_with_non_object_input_is_denied(self):
        """分類はツール名で先に決めること（Codex 第3巡 MEDIUM）。

        旧版は tool_input の型を先に見ていたため、未知ツール＋非 object の
        tool_input が「検査対象外」として素通りした。
        """
        for bad_input in ("not-an-object", 1, ["a"], None):
            with self.subTest(tool_input=bad_input):
                out = expect_decision(
                    {"tool_name": "mcp__agy__future_tool", "tool_input": bad_input}
                )
                self.assertEqual(out["permissionDecision"], "deny")
                self.assertIn("未知", out["permissionDecisionReason"])

    def test_unknown_agy_tool_without_tool_input_is_denied(self):
        out = expect_decision({"tool_name": "mcp__agy__future_tool"})
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("未知", out["permissionDecisionReason"])

    def test_enforced_tool_with_non_object_input_is_denied(self):
        out = expect_decision(
            {"tool_name": "mcp__agy__antigravity_ask", "tool_input": "not-an-object"}
        )
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("object でない", out["permissionDecisionReason"])

    def test_other_backend_linux_path_is_denied(self):
        """契約未検証のバックエンドに Linux パスを渡したら、推測変換せず deny する。"""
        out = expect_decision(
            {
                "tool_name": "mcp__agy__codex_ask",
                "tool_input": {"workspace": str(ROOT), "prompt": "x"},
            }
        )
        self.assertEqual(out["permissionDecision"], "deny")

    def test_swarm_non_antigravity_aliases_are_not_converted(self):
        """codex / copilot / cursor の alias は変換対象に入れないこと（推測変換しない）。

        ブリッジの `_BACKEND_ALIASES` には `openai`→codex・`github`/`gh`→copilot もある。
        これらを取り込むと契約未検証のまま変換してしまうので、Linux パスは deny のままでよい。
        """
        for backend in ("codex", "openai", "copilot", "github", "gh", "cursor"):
            with self.subTest(backend=backend):
                out = expect_decision(
                    swarm({"backend": backend, "prompt": "P", "workspace": str(ROOT)})
                )
                self.assertEqual(out["permissionDecision"], "deny")
                self.assertIn("Windows 絶対パスでない", out["permissionDecisionReason"])


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestConversionRoundTrip(unittest.TestCase):
    """変換結果が変換元と**同じ実在ディレクトリ**を指すことまで確認する（Codex 第4巡 MEDIUM）。

    形式（Windows 絶対パス）と変換元の実在だけでは「別の実在ディレクトリへ化けた」を検出できない。
    化けたまま通すと agy は実在するが意図と違うツリーで走り、エラーも出さずに答える。
    """

    _BAD_WSLPATH = """#!/usr/bin/env python3
import sys
flag = sys.argv[1]
# -w は「それらしい Windows 絶対パス」を返すが、-u で戻すと常に / になる（= 別ディレクトリ）。
sys.stdout.write("\\\\\\\\wsl.localhost\\\\Ubuntu\\\\home\\n" if flag == "-w" else "/\\n")
"""

    def test_conversion_landing_elsewhere_is_denied(self):
        d = tempfile.mkdtemp(prefix="badwslpath_")
        try:
            bad = Path(d) / "wslpath"
            bad.write_text(self._BAD_WSLPATH, encoding="utf-8")
            bad.chmod(0o755)
            env = dict(ENV, PATH=f"{d}{os.pathsep}{ENV['PATH']}")
            out = expect_decision(
                ask(workspace=str(ROOT), prompt="x"),
                env=env,
                msg="往復が別ディレクトリを指す変換を素通ししないこと",
            )
            self.assertEqual(out["permissionDecision"], "deny")
            self.assertIn("往復", out["permissionDecisionReason"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
