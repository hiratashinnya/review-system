import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "agent-command-gate.sh"


def run_gate(payload, *, env=None):
    # AGENT_COMMAND_GATE_TRACE_LOG は既定で常時有効（Issue #192）。テストが明示的に上書きしない
    # 限り空文字にして無効化し、開発者の実ホームディレクトリ（~/.claude/agent-command-gate-trace.log）
    # を汚染しないようにする。
    merged_env = {**os.environ, "AGENT_COMMAND_GATE_TRACE_LOG": "", **(env or {})}
    result = subprocess.run(
        [str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env=merged_env,
    )
    if not result.stdout:
        return None
    return json.loads(result.stdout)


def payload(agent_type, command):
    return {"agent_type": agent_type, "tool_input": {"command": command}}


class AgentCommandGateTests(unittest.TestCase):
    def assert_denied(self, hook_output):
        self.assertIsNotNone(hook_output)
        self.assertEqual(
            hook_output["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

    def assert_allowed(self, hook_output):
        self.assertIsNone(hook_output)

    def test_issue_implementer_denies_direct_merge_forms(self):
        commands = [
            "git merge feature",
            "rtk git merge feature",
            "GIT_PAGER=cat git merge feature",
            "echo hi\ngit merge feature",
            "(git merge feature)",
            "echo $(git merge feature)",
            "echo `git merge feature`",
            "eval 'git merge feature'",
            "bash -c 'git merge feature'",
            "python3 -c \"import os; os.system('git merge feature')\"",
            "gh pr merge 123",
            "gh --repo hiratashinnya/review-system pr merge 123",
            "gh -R hiratashinnya/review-system pr merge 123",
            "rtk gh --repo hiratashinnya/review-system pr merge 123",
            "rtk gh pr merge 123",
            "git -c alias.m=merge m feature",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

    def test_issue_implementer_allows_non_merge_git_commands(self):
        commands = [
            "git merge-base main HEAD",
            "git merge-tree HEAD main feature",
            "git merge --abort",
            "git merge --quit",
            "git push origin HEAD",
            "gh pr create --fill",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed(run_gate(payload("issue-implementer", command)))

    def test_pr_reviewer_denies_push_but_allows_merge(self):
        self.assert_denied(run_gate(payload("pr-reviewer", "git push origin HEAD")))
        self.assert_denied(run_gate(payload("pr-reviewer", "rtk git push origin HEAD")))
        self.assert_allowed(run_gate(payload("pr-reviewer", "gh pr merge 123")))

    def test_heredoc_prose_quoting_is_not_over_denied(self):
        # Issue #189: quoted_subcommands/quoted_literals の副作用で、`gh pr create`/`git commit` を
        # 本リポジトリの規約どおりヒアドキュメント（<<'EOF' ... EOF）で渡すと、本文中の説明的な
        # 引用テキスト（Markdown インラインコード等）に「git merge」「gh pr merge」が含まれるだけで
        # over-deny されていた（実地に PR #191 の作業中で複数回再現）。ヒアドキュメント本文は
        # シェル上「直前コマンドへの入力データ」であってトップレベルのコマンド列ではないため、
        # これらは許可されるべき（false positive の解消）。
        commands = [
            "gh pr create --title \"t\" --body \"$(cat <<'EOF'\n"
            "See `git merge` example in docs.\n"
            "EOF\n"
            ")\"",
            "git commit -m \"$(cat <<'EOF'\n"
            "fix: note that `gh pr merge` is reviewer-only\n"
            "EOF\n"
            ")\"",
            "gh pr comment 123 --body \"$(cat <<'EOF'\n"
            "Please do not run `git merge` manually; only pr-reviewer may `gh pr merge`.\n"
            "EOF\n"
            ")\"",
            # ダブルクォート版デリミタ・非引用デリミタでも本文がデータとして扱われる限りは許可。
            "git commit -m \"$(cat <<\"EOF\"\n"
            "note about git merge in prose\n"
            "EOF\n"
            ")\"",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed(run_gate(payload("issue-implementer", command)))

    def test_heredoc_smuggled_reexecution_is_still_denied(self):
        # Issue #189 是正の trade-off 確認: ヒアドキュメント本文を「常にデータ扱い」で無条件に
        # スキップすると、`bash -c "$(cat <<'EOF' ... EOF)"` や `bash <<'EOF' ... EOF` のように
        # ヒアドキュメント経由で実際にコマンド文字列が再実行される難読化を見逃してしまう。
        # インタプリタ（bash/sh/python 等）へ直接・間接に渡る本文は、除去した上で別途生テキストとして
        # 再帰走査するため、これらは引き続き検知されなければならない。
        commands = [
            "bash -c \"$(cat <<'EOF'\n"
            "git merge evil\n"
            "EOF\n"
            ")\"",
            "bash <<'EOF'\ngit merge evil\nEOF",
            "sh <<'EOF'\ngh pr merge 123\nEOF",
            "eval \"$(cat <<'EOF'\n"
            "git merge evil\n"
            "EOF\n"
            ")\"",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

    def test_heredoc_piped_to_interpreter_is_still_denied(self):
        # Issue #189 追加是正（PR #212 レビュー指摘）: heredoc_command_word() は `<<` の直前・
        # 同一行のコマンド語（例: `cat`）しか見ておらず、その stdout が下流パイプでインタプリタに
        # 渡る経路（`cat <<'EOF' | bash` 等）を捕捉できていなかったため、以下がすべて本来 deny
        # すべきなのに allow されてしまう重大バイパスがあった。パイプ下流にインタプリタが
        # あれば本文を再帰走査するよう是正したため、引き続き検知されなければならない。
        issue_implementer_commands = [
            "cat <<'EOF' | bash\ngit merge evil\nEOF",
            "cat <<EOF | bash\ngit merge evil\nEOF",  # 非引用デリミタ
            "cat <<EOF | sh\ngh pr merge 123\nEOF",
            "cat <<-'EOF' | bash\ngit merge evil\nEOF",  # `<<-` ダッシュ版
            "cat <<'EOF' | tee /tmp/x | bash\ngit merge evil\nEOF",  # 多段パイプ
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        # git push は pr-reviewer 側の禁止事項（issue-implementer には push は許可されている）ため、
        # 同じパイプ経由バイパスを pr-reviewer ロールで確認する。
        pr_reviewer_commands = [
            "cat <<'EOF' | bash\ngit push origin HEAD\nEOF",
            "cat <<'EOF' | tee /tmp/x | bash\ngit push origin HEAD\nEOF",
        ]
        for command in pr_reviewer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("pr-reviewer", command)))

    def test_heredoc_piped_to_source_is_still_denied(self):
        # Issue #189 追加是正その2（PR #212 再レビュー指摘）: HEREDOC_INTERPRETER_COMMANDS に
        # bash 組み込みの `source`/`.`（同義・カレントシェルでスクリプトを読み込み実行する）が
        # 含まれておらず、`cat <<'EOF' | source /dev/stdin`（`. /dev/stdin` も同様）でヒアドキュメント
        # 本文が再実行されるにもかかわらず allow されていた（PR #212 の base=main では偶然 deny
        # されていた挙動が本PRの変更で allow に変わる回帰だった）。source/. を追加したため、
        # 引き続き検知されなければならない。
        issue_implementer_commands = [
            "cat <<'EOF' | source /dev/stdin\ngit merge evil\nEOF",
            "cat <<'EOF' | . /dev/stdin\ngit merge evil\nEOF",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        pr_reviewer_commands = [
            "cat <<'EOF' | source /dev/stdin\ngit push origin HEAD\nEOF",
            "cat <<'EOF' | . /dev/stdin\ngit push origin HEAD\nEOF",
        ]
        for command in pr_reviewer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("pr-reviewer", command)))

    def test_herestring_bypass_is_denied(self):
        # Issue #213 受け入れ基準1: `bash <<< 'git merge evil'`（here-string）は HEREDOC_RE が
        # `<<` の直後に識別子を要求するため `<<<`（3文字目が `<`）にはマッチせず、検知漏れだった
        # （実際に bash で実行し注入コマンドが走ることを確認済み）。
        issue_implementer_commands = [
            "bash <<< 'git merge feature'",
            'bash <<< "git merge feature"',
            "sh <<< 'gh pr merge 123'",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "bash <<< 'git push origin HEAD'")))
        # 対象コマンドが git/gh に無関係な場合は over-deny しない（herestring 値が単に
        # インタプリタに渡っても、走査結果が違反でなければ許可のまま）。
        self.assert_allowed(run_gate(payload("issue-implementer", "bash <<< 'echo hello'")))
        # herestring を受け取るコマンドがインタプリタでない場合（`cat` はデータとして読むだけ）は
        # 誤検知しない。
        self.assert_allowed(run_gate(payload("issue-implementer", "cat <<< 'git merge is mentioned here'")))

    def test_xargs_placeholder_substitution_bypass_is_denied(self):
        # Issue #213 受け入れ基準2: `echo 'git merge evil' | xargs -I{} bash -c '{}'` は
        # quoted_subcommands がリテラル `{}` のみ抽出し、xargs が実行時に代入する実際の値
        # （パイプ上流の echo リテラル）を静的に追えず検知漏れだった（実行して確認済み）。
        issue_implementer_commands = [
            "echo 'git merge feature' | xargs -I{} bash -c '{}'",
            "echo 'git merge feature' | xargs -I {} bash -c '{}'",
            "printf '%s' 'gh pr merge 123' | xargs -I{} sh -c '{}'",
            "echo 'merge' | xargs -I{} git {}",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | xargs -I{} bash -c '{}'"))
        )
        # xargs の上流がリテラルでない場合（`find` の結果など）は静的に値を確定できないため
        # 対象外＝過検知しない（既存の一般的な xargs 利用イディオムを壊さない）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "find . -name '*.txt' | xargs -I{} wc -l {}"))
        )

    def test_bare_pipe_to_interpreter_bypass_is_denied(self):
        # Issue #213 受け入れ基準6（追記コメントで追加）: `printf '%s' 'git merge evil' | bash` の
        # ように、ヒアドキュメントを使わない素朴なパイプ経由でインタプリタへ渡す経路は、
        # PR #212 適用前後を問わず allow のままだった（実行して確認済み）。
        issue_implementer_commands = [
            "printf '%s' 'git merge feature' | bash",
            "echo 'git merge feature' | bash",
            "echo 'gh pr merge 123' | sh",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | bash")))
        # bash がスクリプトファイル引数を伴う場合（標準入力をスクリプトとして読まない）は
        # 過検知しない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash script.sh"))
        )
        # 上流が非リテラル（コマンド置換等）の場合は静的に値を確定できないため対象外。
        self.assert_allowed(run_gate(payload("issue-implementer", "cat notes.txt | bash")))

    def test_operator_chained_pipe_bypass_is_denied(self):
        # 実装中の敵対的自己検証で発見（Issue #213）: `true || echo 'git merge evil' | bash` や
        # `echo 'git merge evil' | bash && true` のように、パイプの前後に `&&`/`||`/`;` で別の
        # サブコマンドを連結すると、producer/consumer 判定がステージ全体を素朴に見てしまい
        # 検知漏れになっていた（`|` は `&&`/`||`/`;` より強く結合するため、実際にパイプに
        # 効いてくるのは producer 側は最後のサブコマンド、consumer 側は最初のサブコマンドのみ）。
        commands = [
            "echo 'git merge feature' | bash && true",
            "echo 'git merge feature' | bash; true",
            "true; echo 'git merge feature' | bash",
            "false || echo 'git merge feature' | bash",
            "true || echo 'git merge feature' | bash",
            "echo 'git merge feature' | xargs -I{} bash -c '{}' && true",
            "true; echo 'git merge feature' | xargs -I{} bash -c '{}'",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        # 演算子連結があっても無関係のコマンドは過検知しない。
        self.assert_allowed(run_gate(payload("issue-implementer", "git status && echo done")))

    def test_passthrough_between_literal_producer_and_interpreter_is_denied(self):
        # Issue #215: Issue #213（PR #214）の opus 敵対的レビューで発見。bare_interpreter_reexec_bodies/
        # xargs_reexec_bodies は literal_producer_value を直前ステージ（stages[i-1]）のみに適用して
        # いたため、リテラル producer とインタプリタの間に `cat`/`tee` 等のパススルーを1段挟むと
        # 検知が外れていた（実行して allow されることを確認済み）。パススルーを許容して producer を
        # 遡れるようにしたため、以下は引き続き（多段パススルーでも）検知されなければならない。
        issue_implementer_commands = [
            "echo 'git merge feature' | cat | bash",
            "printf '%s' 'git merge feature' | tee /tmp/x | bash",
            "echo 'git merge feature' | cat | xargs -I{} bash -c '{}'",
            # 多段パススルー（cat/tee の重ね掛け）。
            "echo 'git merge feature' | cat | cat | bash",
            "echo 'git merge feature' | cat | tee /tmp/x | cat | bash",
            "printf '%s' 'gh pr merge 123' | cat | sh",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        pr_reviewer_commands = [
            "echo 'git push origin HEAD' | cat | bash",
            "echo 'git push origin HEAD' | cat | xargs -I{} bash -c '{}'",
        ]
        for command in pr_reviewer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("pr-reviewer", command)))

    def test_passthrough_producer_traversal_does_not_introduce_new_bypass(self):
        # 敵対的自己検証（Issue #215）: パススルー許容ロジック自体が新たな抜け道を生んでいないか確認。
        # 1. パイプ境界前後の演算子連結（`&&`）でパスルーが挟まると、シェルの結合優先順位
        #    （`|` が `&&` より強い）により実際には2本の独立したパイプラインに分かれ、literal は
        #    bash 側へ渡らない（実際に bash で実行し injected 文字列が「実行されず表示されるだけ」に
        #    留まることを確認済み）。過検知せず allow のままであるべき。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat && true | bash"))
        )
        # 2. `cat` にファイルオペランドがある場合、標準入力ではなくファイルを読むため、上流の
        #    echo リテラルは実際には bash に渡らない。パススルー扱いにしないため过検知しない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat notes.txt | bash"))
        )
        # 3. 既存の false positive 対策（無関係の xargs/パイプイディオム）は壊れていない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "find . -name '*.txt' | xargs -I{} wc -l {}"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash script.sh"))
        )

    def test_herestring_and_pipe_detection_does_not_over_deny_heredoc_data(self):
        # 実装中の敵対的自己検証で発見（Issue #213）: herestring_reexec_bodies/xargs_reexec_bodies/
        # bare_interpreter_reexec_bodies を command_text（生テキスト）に対して走査すると、
        # `cat > file.py <<'EOF' ... EOF` のように実行されないヒアドキュメント本文（例: サンプル
        # コードやドキュメントの文字列リテラル）の中にたまたま `<<<`/パイプ経由でインタプリタに
        # 渡っているように見える記法が含まれているだけで over-deny してしまう回帰があった
        # （Issue #189 の false positive 是正方針の再侵犯）。scan_text（ヒアドキュメント本文除去済み）
        # を走査対象にすることで、これらのデータは実行されないため許可されなければならない。
        commands = [
            "cat > /tmp/example.py <<'EOF'\n"
            "cases = [\n"
            "    (\"issue-implementer\", \"/bin/bash <<< 'git merge feature'\"),\n"
            "]\n"
            "EOF",
            "cat > /tmp/example.md <<'EOF'\n"
            "Example: `echo 'git merge evil' | xargs -I{} bash -c '{}'` is a known bypass.\n"
            "EOF",
            "cat > /tmp/example.md <<'EOF'\n"
            "Example: `printf '%s' 'git merge evil' | bash` is a known bypass.\n"
            "EOF",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed(run_gate(payload("issue-implementer", command)))

    def test_missing_or_unrecognized_agent_is_out_of_scope(self):
        # 2026-07-11 オーナー判断：agent_type が issue-implementer/pr-reviewer のいずれでもない
        # 場合（欠如を含む・main context 自身がこれに該当）は、このゲートの対象外として常に許可する。
        # main context を積極識別するハーネス側の機能が無く、かつ push/merge を専用エージェント
        # 以外全面禁止にすると main context 自身の直接 push まで塞がれてしまうため、この設計に確定。
        self.assert_allowed(run_gate({"tool_input": {"command": "git merge feature"}}))
        self.assert_allowed(run_gate({"tool_input": {"command": "git push origin HEAD"}}))
        self.assert_allowed(run_gate({"tool_input": {"command": "git status"}}))
        self.assert_allowed(run_gate(payload("general-purpose", "git merge feature")))
        self.assert_allowed(run_gate(payload("general-purpose", "git push origin HEAD")))

    def test_missing_command_denies_because_command_cannot_be_inspected(self):
        self.assert_denied(run_gate({"agent_type": "issue-implementer", "tool_input": {}}))
        self.assert_denied(run_gate({"agent_type": "issue-implementer"}))

    def test_subagent_type_fallback_is_supported(self):
        self.assert_denied(
            run_gate({"subagent_type": "issue-implementer", "tool_input": {"command": "git merge feature"}})
        )

    def test_debug_payload_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "payload.log"
            output = run_gate(
                {
                    "agent_type": "issue-implementer",
                    "tool_input": {"command": "git merge feature"},
                    "api_token": "secret-value",
                },
                env={"AGENT_COMMAND_GATE_DEBUG_PAYLOAD": str(log_path)},
            )
            self.assert_denied(output)
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["payload"]["api_token"], "<redacted>")
            self.assertEqual(record["decision"], "deny")

    def test_trace_log_records_minimal_fields_on_deny_and_allow(self):
        # Issue #192: 常時有効の最小トレース。command 本文や生 payload は含まず、
        # 時刻・agent_type・tool_name・判定のみを1行JSONとして追記する。
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "trace.log"
            self.assert_denied(
                run_gate(
                    payload("issue-implementer", "git merge feature"),
                    env={"AGENT_COMMAND_GATE_TRACE_LOG": str(log_path)},
                )
            )
            self.assert_allowed(
                run_gate(
                    payload("issue-implementer", "git push origin HEAD"),
                    env={"AGENT_COMMAND_GATE_TRACE_LOG": str(log_path)},
                )
            )
            lines = log_path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)
            deny_record = json.loads(lines[0])
            allow_record = json.loads(lines[1])
            self.assertEqual(deny_record["decision"], "deny")
            self.assertEqual(deny_record["agent_type"], "issue-implementer")
            self.assertIn("ts", deny_record)
            self.assertEqual(set(deny_record.keys()), {"ts", "agent_type", "tool_name", "decision"})
            self.assertEqual(allow_record["decision"], "allow")
            self.assertEqual(allow_record["agent_type"], "issue-implementer")
            # command 本文・その他 payload フィールドが漏れていないことを確認する。
            raw_text = log_path.read_text()
            self.assertNotIn("git merge feature", raw_text)
            self.assertNotIn("git push origin HEAD", raw_text)

    def test_trace_log_can_be_disabled_with_empty_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "trace.log"
            run_gate(
                payload("issue-implementer", "git merge feature"),
                env={"AGENT_COMMAND_GATE_TRACE_LOG": ""},
            )
            self.assertFalse(log_path.exists())

    def test_trace_log_rotates_when_it_grows_past_the_size_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "trace.log"
            log_path.write_text("x" * 1_000_001)
            run_gate(
                payload("issue-implementer", "git status"),
                env={"AGENT_COMMAND_GATE_TRACE_LOG": str(log_path)},
            )
            backup_path = Path(str(log_path) + ".1")
            self.assertTrue(backup_path.exists())
            self.assertEqual(len(log_path.read_text().strip().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
