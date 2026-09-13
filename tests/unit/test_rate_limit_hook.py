"""Unit tests for the Claude Code rate-limit auto-resume bash hooks (Issue #240).

Covers the pure, side-effect-light logic in
``.claude/hooks/resume-watcher.sh`` (and the shared ``lib-pane-guard.sh``),
which previously had NO automated coverage — only the Codex-side hooks did
(``test_codex_rate_limit_*``). Issue #240 D2 flagged this coverage gap.

``resume-watcher.sh`` can be sourced with ``CLAUDE_RL_SOURCE_FOR_TEST=1`` (and a
dummy pane-id positional arg) to expose its pure functions
(``parse_reset_from_text`` / ``build_continue_msg`` / ``text_has_banner`` / the
lib's ``rl_pane_slug`` / ``rl_hit_file``) without touching tmux, acquiring the
lock, or running the wait/inject loops — the same test hook the Codex watcher
uses (``CODEX_RL_SOURCE_FOR_TEST``). ``CLAUDE_RL_STATE_DIR`` redirects state
(logs / lock) into a temp dir so tests never write to ``~/.claude``.

The tests double as regression guards for the bug fixes made in this issue:
  * B1 — banner scan window unified (``BANNER_SCAN_LINES``, default 40).
  * B2 — reset regex accepts ``resets at 3pm`` / ``resets at Mon`` ("at" form).
  * B3 — a just-passed reset time is NOT rolled ~24h into tomorrow.
"""

import datetime
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = ROOT / ".claude" / "hooks"
LIB = HOOK_DIR / "lib-pane-guard.sh"
HOOK = HOOK_DIR / "on-rate-limit.sh"
WATCHER = HOOK_DIR / "resume-watcher.sh"
_HAS_BASH = shutil.which("bash") is not None


def _run(script_body, args=(), env_lines=""):
    """Source the watcher in test mode inside a temp state dir, then run
    ``script_body`` with positional ``args`` available as $1, $2, ..."""
    state_dir = tempfile.mkdtemp(prefix="claude-rl-test-")
    try:
        body = f'''
set -u
export CLAUDE_RL_SOURCE_FOR_TEST=1
export CLAUDE_RL_STATE_DIR="{state_dir}"
{env_lines}
source "{WATCHER}" dummy-pane
{script_body}
'''
        return subprocess.run(
            ["bash", "-c", body, "bash", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def parse_reset(text):
    return _run('parse_reset_from_text "$1"', [text]).stdout


def text_has_banner(text):
    return _run('text_has_banner "$1"', [text]).returncode == 0


def build_msg(hit_str="", reset_epoch="", override=""):
    body = (
        'HIT_STR="$1"; reset_epoch="$2"; CONTINUE_MSG_OVERRIDE="$3"; '
        "build_continue_msg"
    )
    return _run(body, [hit_str, reset_epoch, override]).stdout


def extract_var(var_name):
    """Resolve a ``${VAR:-default}`` config value as bash actually sets it."""
    return _run(f'printf "%s" "${var_name}"').stdout


@unittest.skipUnless(_HAS_BASH, "bash バイナリが必要")
class RateLimitHookTests(unittest.TestCase):
    def test_scripts_pass_bash_syntax_check(self):
        for script in (LIB, HOOK, WATCHER):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)], capture_output=True, text=True
                )
                self.assertEqual(
                    result.returncode, 0, f"bash -n failed: {result.stderr}"
                )

    # --- B2: reset regex must accept the "at" form ---------------------------
    def test_b2_reset_with_at_is_parsed(self):
        for text in (
            "You've hit your usage limit · limit resets at 3pm (Asia/Tokyo)",
            "limit resets at 11:59pm",
            "usage limit reached. resets at 9:00am",
        ):
            with self.subTest(text=text):
                self.assertRegex(
                    parse_reset(text).strip(),
                    r"^\d+$",
                    f"expected an epoch for {text!r}",
                )

    def test_reset_without_at_still_parsed(self):
        # Regression: the pre-existing "digit right after resets" form must
        # keep working after adding the optional "at".
        for text in ("resets 3pm", "session limit ... resets 10:50pm"):
            with self.subTest(text=text):
                self.assertRegex(parse_reset(text).strip(), r"^\d+$")

    def test_weekly_limit_detected_with_and_without_at(self):
        self.assertEqual(parse_reset("hit your weekly limit resets Mon").strip(), "WEEKLY")
        self.assertEqual(parse_reset("resets at Mon 9am").strip(), "WEEKLY")

    def test_no_reset_time_returns_empty(self):
        self.assertEqual(parse_reset("nothing to see here").strip(), "")

    # --- B3: a just-passed reset must not roll ~24h into tomorrow ------------
    def test_b3_just_passed_reset_not_rolled_to_tomorrow(self):
        now = datetime.datetime.now()
        # Avoid the midnight-crossing ambiguity: "a few minutes ago" must stay
        # on the same calendar day for this assertion to be meaningful.
        if now.hour == 0 and now.minute < 30:
            self.skipTest("near midnight; same-day 'past' assumption unsafe")
        past = now - datetime.timedelta(minutes=2)
        hhmm = past.strftime("%I:%M%p").lstrip("0").lower()  # e.g. "3:07pm"
        epoch = parse_reset(f"limit resets {hhmm}").strip()
        self.assertRegex(epoch, r"^\d+$")
        now_epoch = int(now.timestamp())
        # Within grace → treated as "just now", a few minutes in the past;
        # the pre-fix bug rolled this to tomorrow (~86400s away).
        self.assertLess(
            abs(int(epoch) - now_epoch),
            4000,
            "just-passed reset was wrongly rolled ~24h into tomorrow (B3)",
        )

    def test_future_reset_today_is_used_as_is(self):
        now = datetime.datetime.now()
        if now.hour >= 21:
            self.skipTest("near end of day; +2h may cross midnight")
        future = now + datetime.timedelta(hours=2)
        hhmm = future.strftime("%I:%M%p").lstrip("0").lower()
        epoch = parse_reset(f"limit resets {hhmm}").strip()
        self.assertRegex(epoch, r"^\d+$")
        delta = int(epoch) - int(now.timestamp())
        self.assertTrue(0 < delta < 3 * 3600, f"unexpected delta {delta}")

    # --- text_has_banner regex (B2 also widens the banner detector) ----------
    def test_banner_detector_matches_at_form(self):
        self.assertTrue(text_has_banner("limit resets at 3pm"))
        self.assertTrue(text_has_banner("You've hit your session limit"))
        self.assertTrue(text_has_banner("resets Mon"))

    def test_banner_detector_ignores_unrelated_text(self):
        self.assertFalse(text_has_banner("just a normal line of output"))

    # --- build_continue_msg --------------------------------------------------
    def test_build_msg_includes_available_time_parts(self):
        now_epoch = str(int(datetime.datetime.now().timestamp()))
        msg = build_msg(hit_str="2026-07-20 10:00:00", reset_epoch=now_epoch)
        self.assertIn("解除されました", msg)
        self.assertIn("検知 2026-07-20 10:00:00", msg)
        self.assertIn("解除", msg)
        self.assertIn("現在", msg)

    def test_build_msg_omits_missing_parts(self):
        # No HIT_STR and no reset_epoch → only the "現在" clause, no 検知/解除.
        msg = build_msg(hit_str="", reset_epoch="")
        self.assertIn("現在", msg)
        self.assertNotIn("検知", msg)

    def test_build_msg_respects_override(self):
        msg = build_msg(override="CUSTOM RESUME TEXT")
        self.assertEqual(msg, "CUSTOM RESUME TEXT")

    # --- Issue #502: 復帰イベントに相乗りする worktree 掃引 --------------------
    def test_build_msg_appends_the_sweep_note_when_present(self):
        # 掃引結果を復帰メッセージ自体に載せる（主文脈が「解放済みか」を知らずに再投入すると
        # adopt-branch の失敗で初めて気づくことになるため）。
        body = (
            'HIT_STR=""; reset_epoch=""; CONTINUE_MSG_OVERRIDE=""; '
            'SWEEP_MSG="SWEPT-MARKER"; build_continue_msg'
        )
        self.assertIn("SWEPT-MARKER", _run(body).stdout)

    def test_build_msg_is_unchanged_when_no_sweep_happened(self):
        # 掃引が未実施／対象なしのときは1文字も足さない（回帰防止）。
        self.assertNotIn("SWEPT", build_msg())
        self.assertTrue(build_msg().endswith("続けてください。"))

    def test_watcher_sweeps_only_with_the_no_live_dispatch_observation(self):
        """掃引の起動口が「復帰イベント＋アイドル観測」に閉じていることを固定する。

        `running` は入れ子委譲待ちの正当な保留でもある（Issue #423）ため、`gitgate` 側は
        `--no-live-dispatch` の申告が無ければ何もしない。watcher がその申告を渡していること・
        検知経路を別に増やしていないこと（`gitgate` 呼び出しがこの1箇所だけであること）を
        本文の静的検査で確認する。
        """
        source = WATCHER.read_text(encoding="utf-8")
        self.assertIn("worktree-sweep-abandoned", source)
        self.assertIn("--no-live-dispatch", source)
        self.assertEqual(
            source.count("python3 -m gitgate"), 1,
            "掃引の起動口は1箇所だけ（検知経路を二重化しない・Issue #502 オーナー指摘）",
        )
        # 注入ループ（アイドル確認済みの地点）から呼ばれている。
        inject_section = source.split("--- 注入(状態認識", 1)[-1]
        self.assertIn("sweep_abandoned_worktrees", inject_section)

    def test_sweep_can_be_disabled_by_an_environment_variable(self):
        self.assertIn("CLAUDE_RL_SWEEP_WORKTREES", WATCHER.read_text(encoding="utf-8"))

    def test_pane_state_is_re_evaluated_after_the_sweep(self):
        """**F-502-06 回帰**: 掃引で開いた「判定→送出」の間隔を、再評価と上限で塞ぐ。

        掃引はネットワーク I/O（候補ごとの `git fetch`）を含むため、アイドル判定と
        `send-keys` の間隔がミリ秒からネットワーク待ちのオーダーへ広がる。その間に
        セッションが再開していると、大原則「稼働中セッションへは絶対に割り込まない」に
        反して継続メッセージを注入してしまう。掃引の**後**にもう一度 `pane_guard` を
        取り直し、かつ掃引自体を `timeout` で有界にすることを本文で固定する。
        """
        source = WATCHER.read_text(encoding="utf-8")
        after_sweep = source.split("  sweep_abandoned_worktrees\n", 1)[-1]
        before_send = after_sweep.split("send-keys", 1)[0]
        self.assertIn("pane_guard", before_send)
        self.assertIn('log "post-sweep', before_send)
        # 掃引の所要時間そのものにも上限を掛ける（再評価と併用＝多層）。
        self.assertIn("CLAUDE_RL_SWEEP_TIMEOUT", source)
        self.assertIn("timeout -k 5 $SWEEP_TIMEOUT", source)

    def test_every_sweep_outcome_that_needs_attention_gets_a_resume_note(self):
        """**F-502-07 回帰**: `action=release-pending` も継続メッセージの1文に載せる。

        `release-pending`（回収済みで削除だけ遅延）は `action=released` の部分文字列では
        ないため、`*"action=released"*` だけでは拾えず、README が謳う「何か解放/保留した
        ときは1文添える」と挙動がずれていた。
        """
        source = WATCHER.read_text(encoding="utf-8")
        for pattern in (
            '*"action=kept-"*',
            '*"action=release-pending"*',
            '*"action=released"*',
        ):
            self.assertIn(pattern, source)
        # `release-pending` の枝は `released` より**前**に置く（case は先勝ちだが、
        # `action=released` は `action=release-pending` に一致しないので順序自体は
        # 安全側。ここでは「両方の枝が存在し、片方が他方を隠していない」ことを固定する）。
        self.assertLess(
            source.index('*"action=release-pending"*'),
            source.index('*"action=released"*'),
        )

    # --- shared lib helpers --------------------------------------------------
    def test_pane_slug_normalizes_non_alnum(self):
        self.assertEqual(_run('rl_pane_slug "%3"').stdout, "_3")
        self.assertEqual(_run('rl_pane_slug "pane-1.2"').stdout, "pane_1_2")

    def test_hit_file_path_uses_state_dir_and_slug(self):
        out = _run('rl_hit_file "%7"').stdout
        self.assertTrue(out.endswith("/hit-time._7"), out)

    def test_default_pane_cmd_re_includes_bun_and_deno(self):
        # B5: default foreground pattern widened beyond node.
        re_default = extract_var("RL_PANE_CMD_RE")
        for runtime in ("claude", "node", "bun", "deno"):
            self.assertIn(runtime, re_default)

    # --- B1: banner scan window is a single shared constant, default 40 ------
    def test_banner_scan_lines_default_is_40(self):
        self.assertEqual(extract_var("BANNER_SCAN_LINES").strip(), "40")

    # --- D1: hit-file session matching (resolve_hit_str) ---------------------
    def _resolve(self, lines, session_id):
        """Write ``lines`` to a temp hit-file, then run resolve_hit_str(file, sid)."""
        tf = tempfile.NamedTemporaryFile("w", delete=False, suffix=".hit")
        try:
            tf.write(lines)
            tf.close()
            return _run('resolve_hit_str "$1" "$2"', [tf.name, session_id]).stdout
        finally:
            Path(tf.name).unlink(missing_ok=True)

    def test_d1_matching_session_returns_time(self):
        out = self._resolve("sess-AAA\n2026-07-20 10:00:00\n", "sess-AAA")
        self.assertEqual(out, "2026-07-20 10:00:00")

    def test_d1_mismatching_session_discards(self):
        out = self._resolve("sess-AAA\n2026-07-20 10:00:00\n", "sess-BBB")
        self.assertEqual(out, "")

    def test_d1_empty_file_session_is_backward_compat_accepted(self):
        # session_id not extractable at hit time → file line 1 empty → accept.
        out = self._resolve("\n2026-07-20 10:00:00\n", "sess-AAA")
        self.assertEqual(out, "2026-07-20 10:00:00")

    def test_d1_legacy_single_line_format_is_discarded(self):
        # Old 1-line format (time on line 1, no line 2) → time field empty → drop.
        out = self._resolve("2026-07-20 10:00:00\n", "sess-AAA")
        self.assertEqual(out, "")

    def test_d1_missing_file_returns_empty(self):
        out = _run('resolve_hit_str "/no/such/hit/file" "sess-AAA"').stdout
        self.assertEqual(out, "")

    def test_acquire_capture_and_limit_screen_share_scan_window(self):
        # Both the acquire-loop capture and is_limit_screen must read the same
        # BANNER_SCAN_LINES window, or a banner on lines 16-40 is "detected but
        # invisible to the clear check" (B1). Guard structurally via source.
        src = WATCHER.read_text()
        self.assertIn('tail -n "$BANNER_SCAN_LINES"', src)
        self.assertIn('pane_tail "$BANNER_SCAN_LINES"', src)


if __name__ == "__main__":
    unittest.main()
