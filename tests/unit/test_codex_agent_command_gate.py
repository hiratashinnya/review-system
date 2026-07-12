import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".codex" / "hooks" / "agent-command-gate.sh"


def run_gate(payload, *, env=None):
    # AGENT_COMMAND_GATE_TRACE_LOG は既定で常時有効（Issue #192）。テストが明示的に上書きしない
    # 限り空文字にして無効化し、開発者の実ホームディレクトリ（~/.codex/agent-command-gate-trace.log）
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


def payload(agent_type, command, *, tool_name="Bash"):
    # Codex PreToolUse 入力スキーマ準拠：agent_type / tool_name / tool_input.command。
    body = {"tool_name": tool_name, "tool_input": {"command": command}}
    if agent_type is not None:
        body["agent_type"] = agent_type
    return body


class CodexAgentCommandGateTests(unittest.TestCase):
    def assert_denied(self, hook_output):
        self.assertIsNotNone(hook_output)
        self.assertEqual(
            hook_output["hookSpecificOutput"]["hookEventName"],
            "PreToolUse",
        )
        self.assertEqual(
            hook_output["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        # Codex は deny に非空の permissionDecisionReason を要求する
        # （codex-rs/hooks/src/engine/output_parser.rs）。
        self.assertTrue(
            hook_output["hookSpecificOutput"]["permissionDecisionReason"].strip()
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
        # over-deny されていた（実地に PR #191 の作業中で複数回再現。Claude 版と同一設計）。
        # ヒアドキュメント本文はシェル上「直前コマンドへの入力データ」であってトップレベルの
        # コマンド列ではないため、これらは許可されるべき（false positive の解消）。
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
        # 再帰走査するため、これらは引き続き検知されなければならない（Claude 版と同一設計）。
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
        # Issue #189 追加是正（PR #212 レビュー指摘・Claude 版と同一設計）: heredoc_command_word()
        # は `<<` の直前・同一行のコマンド語（例: `cat`）しか見ておらず、その stdout が下流パイプで
        # インタプリタに渡る経路（`cat <<'EOF' | bash` 等）を捕捉できていなかったため、以下がすべて
        # 本来 deny すべきなのに allow されてしまう重大バイパスがあった。パイプ下流にインタプリタが
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
        # Issue #189 追加是正その2（PR #212 再レビュー指摘・Claude 版と同一設計）:
        # HEREDOC_INTERPRETER_COMMANDS に bash 組み込みの `source`/`.`（同義・カレントシェルで
        # スクリプトを読み込み実行する）が含まれておらず、`cat <<'EOF' | source /dev/stdin`
        # （`. /dev/stdin` も同様）でヒアドキュメント本文が再実行されるにもかかわらず allow されて
        # いた（PR #212 の base=main では偶然 deny されていた挙動が本PRの変更で allow に変わる
        # 回帰だった）。source/. を追加したため、引き続き検知されなければならない。
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
        # Issue #213 受け入れ基準1（Claude 版と同一設計）: `bash <<< 'git merge evil'`
        # （here-string）は HEREDOC_RE が `<<` の直後に識別子を要求するため `<<<`（3文字目が `<`）
        # にはマッチせず、検知漏れだった（実際に bash で実行し注入コマンドが走ることを確認済み）。
        issue_implementer_commands = [
            "bash <<< 'git merge feature'",
            'bash <<< "git merge feature"',
            "sh <<< 'gh pr merge 123'",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "bash <<< 'git push origin HEAD'")))
        self.assert_allowed(run_gate(payload("issue-implementer", "bash <<< 'echo hello'")))
        self.assert_allowed(
            run_gate(payload("issue-implementer", "cat <<< 'git merge is mentioned here'"))
        )

    def test_xargs_placeholder_substitution_bypass_is_denied(self):
        # Issue #213 受け入れ基準2（Claude 版と同一設計）: `echo 'git merge evil' |
        # xargs -I{} bash -c '{}'` は quoted_subcommands がリテラル `{}` のみ抽出し、xargs が
        # 実行時に代入する実際の値（パイプ上流の echo リテラル）を静的に追えず検知漏れだった
        # （実行して確認済み）。
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
        self.assert_allowed(
            run_gate(payload("issue-implementer", "find . -name '*.txt' | xargs -I{} wc -l {}"))
        )

    def test_bare_pipe_to_interpreter_bypass_is_denied(self):
        # Issue #213 受け入れ基準6（追記コメントで追加・Claude 版と同一設計）:
        # `printf '%s' 'git merge evil' | bash` のように、ヒアドキュメントを使わない素朴なパイプ
        # 経由でインタプリタへ渡す経路は、PR #212 適用前後を問わず allow のままだった
        # （実行して確認済み）。
        issue_implementer_commands = [
            "printf '%s' 'git merge feature' | bash",
            "echo 'git merge feature' | bash",
            "echo 'gh pr merge 123' | sh",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | bash")))
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash script.sh"))
        )
        self.assert_allowed(run_gate(payload("issue-implementer", "cat notes.txt | bash")))

    def test_operator_chained_pipe_bypass_is_denied(self):
        # 実装中の敵対的自己検証で発見（Issue #213・Claude 版と同一設計）: `true ||
        # echo 'git merge evil' | bash` や `echo 'git merge evil' | bash && true` のように、
        # パイプの前後に `&&`/`||`/`;` で別のサブコマンドを連結すると、producer/consumer 判定が
        # ステージ全体を素朴に見てしまい検知漏れになっていた（`|` は `&&`/`||`/`;` より強く結合
        # するため、実際にパイプに効いてくるのは producer 側は最後のサブコマンド、consumer 側は
        # 最初のサブコマンドのみ）。
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
        self.assert_allowed(run_gate(payload("issue-implementer", "git status && echo done")))

    def test_passthrough_between_literal_producer_and_interpreter_is_denied(self):
        # Issue #215（Claude 版と同一設計）: Issue #213（PR #214）の opus 敵対的レビューで発見。
        # bare_interpreter_reexec_bodies/xargs_reexec_bodies は literal_producer_value を直前
        # ステージ（stages[i-1]）のみに適用していたため、リテラル producer とインタプリタの間に
        # `cat`/`tee` 等のパススルーを1段挟むと検知が外れていた（実行して allow されることを
        # 確認済み）。パススルーを許容して producer を遡れるようにしたため、以下は引き続き
        # （多段パススルーでも）検知されなければならない。
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
        # 敵対的自己検証（Issue #215・Claude 版と同一設計）: パススルー許容ロジック自体が新たな
        # 抜け道を生んでいないか確認。
        # 1. パイプ境界前後の演算子連結（`&&`）でパススルーが挟まると、シェルの結合優先順位
        #    （`|` が `&&` より強い）により実際には2本の独立したパイプラインに分かれ、literal は
        #    bash 側へ渡らない（実際に bash で実行し injected 文字列が「実行されず表示されるだけ」に
        #    留まることを確認済み）。過検知せず allow のままであるべき。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat && true | bash"))
        )
        # 2. `cat` にファイルオペランドがある場合、標準入力ではなくファイルを読むため、上流の
        #    echo リテラルは実際には bash に渡らない。パススルー扱いにしないため過検知しない。
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

    def test_subshell_paren_grouping_bypass_is_denied(self):
        # Issue #218 ギャップ1（PR #216 の opus 敵対的レビューで発見・Claude 版と同一設計）:
        # PIPE_ONLY_RE.split() はトップレベルの `|` を素朴に全分割するため、`( ... | ... )` の
        # ような丸括弧サブシェルを含むパイプラインでは、サブシェル内部の `|` まで分割対象にして
        # しまい `(cat`/`cat)` という不正な字句が生まれ、パススルー追跡が途切れて検知漏れに
        # なっていた（実行して確認済み：`echo 'git merge evil' | (cat | cat) | bash` が allow
        # されていた）。
        issue_implementer_commands = [
            "echo 'git merge feature' | (cat | cat) | bash",
            "echo 'git merge feature' | (cat) | bash",
            "echo 'git merge feature' | ((cat)) | bash",
            "echo 'git merge feature' | (cat | (cat | cat)) | bash",
            "echo 'git merge feature' | (sort | cat) | bash",
            "echo 'git merge feature' | (cat | sort) | bash",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | (cat | cat) | bash"))
        )
        # 比較対象: 括弧なしの同種パイプは #215 で既に対応済み（引き続き deny のまま）。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat | cat | bash"))
        )

    def test_subshell_paren_grouping_does_not_over_deny_unrelated_commands(self):
        # Issue #218 受け入れ基準2: サブシェル括弧を含むが実際には無関係な既存の許可パターンで
        # 新規の誤検知（over-deny）が発生しないことを確認する。
        self.assert_allowed(run_gate(payload("issue-implementer", "(echo hi)")))
        self.assert_allowed(run_gate(payload("issue-implementer", "(echo hi) && git status")))
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | (cat | cat) | bash"))
        )
        # cat がサブシェル内でファイルオペランドを持つ場合は標準入力を読まないため対象外のまま。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | (cat notes.txt) | bash"))
        )
        # 開き括弧のみで閉じ括弧が来ない不正形式は検査不能側に倒して従来どおり過検知しない。
        self.assert_allowed(run_gate(payload("issue-implementer", "echo '(unbalanced'")))

    def test_single_line_filter_passthrough_bypass_is_denied(self):
        # Issue #218 ギャップ2（PR #216 の opus 敵対的レビューで発見・Claude 版と同一設計）:
        # PASSTHROUGH_COMMANDS が cat/tee のみで、sort/head/tail/uniq を挟んだパイプラインが
        # 検知漏れになっていた（実行して確認済み：`echo 'git merge evil' | sort | bash` 等が
        # allow されていた）。sort/head/tail/uniq は「引数なし（sort/uniq）」「正の行数指定のみ、
        # または引数なし（head/tail）」の場合に限り、単一行入力に対する恒等変換として扱う。
        issue_implementer_commands = [
            "echo 'git merge feature' | sort | bash",
            "echo 'git merge feature' | head -n1 | bash",
            "echo 'git merge feature' | uniq | bash",
            "echo 'git merge feature' | tail -n1 | bash",
            "echo 'git merge feature' | head | bash",
            "echo 'git merge feature' | tail | bash",
            "echo 'git merge feature' | head -n 1 | bash",
            "echo 'git merge feature' | head --lines=1 | bash",
            # sort/head/tail/uniq を cat/tee と重ね掛けした多段パススルー。
            "echo 'git merge feature' | cat | sort | bash",
            "echo 'git merge feature' | sort | cat | bash",
            "echo 'git merge feature' | uniq | cat | tail -n1 | bash",
            # xargs プレースホルダ経由でも同様に検知されなければならない。
            "echo 'git merge feature' | sort | xargs -I{} bash -c '{}'",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | sort | bash")))

    def test_single_line_filter_passthrough_does_not_over_deny(self):
        # Issue #218 受け入れ基準3: sort/head/tail/uniq を安易に無条件で追加すると、恒等変換に
        # ならない引数の組み合わせ（`uniq -c`／`head -n0`／ファイルオペランドを伴う `sort file.txt`
        # 等）まで誤ってパススルー扱いしてしまう。これらは恒等性を保証できないため、パススルー
        # チェーンが途切れて allow のまま（＝新規の検知は増えないが、新規の過検知も起きない）で
        # なければならない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | uniq -c | bash"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | head -n0 | bash"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "sort notes.txt | bash"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | sort file.txt | bash"))
        )
        # grep/tr は恒等変換にならないため対象外（Issue #218 スコープ外）。パススルー扱いに
        # ならず allow のまま（過検知しない）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | grep git | bash"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | tr a-z A-Z | bash"))
        )
        # 通常の無関係な用途（安全なコンテンツを sort/head/tail/uniq に通すだけ）を壊さない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | sort | wc -l"))
        )

    def test_subshell_wraps_consumer_or_whole_pipeline_bypass_is_denied(self):
        # PR #219 opus レビューで発見（クラスA・実 bash で実行確認済み・Claude 版と同一設計）:
        # 前回の split_top_level_pipes/strip_matching_parens は「中間パススルー段としての
        # サブシェル」のみに対応しており、consumer 位置・パイプライン全体を囲むサブシェルは
        # 未対応だった。
        issue_implementer_commands = [
            "echo 'git merge feature' | (bash)",
            "(echo 'git merge feature' | bash)",
            "echo 'git merge feature' | (cat | cat) | (bash)",
            "echo 'git merge feature' | (cat && true) | bash",
            "echo 'git merge feature' | (true; cat) | bash",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        pr_reviewer_commands = [
            "echo 'git push origin HEAD' | (bash)",
            "(echo 'git push origin HEAD' | bash)",
        ]
        for command in pr_reviewer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("pr-reviewer", command)))

    def test_subshell_wraps_consumer_or_whole_pipeline_does_not_over_deny(self):
        # クラスA是正の副作用確認: 無関係なサブシェル・sequencing 演算子の組み合わせで
        # 新規の誤検知（over-deny）が発生しないこと。
        self.assert_allowed(run_gate(payload("issue-implementer", "(echo hi)")))
        self.assert_allowed(run_gate(payload("issue-implementer", "echo hi | (cat)")))
        self.assert_allowed(run_gate(payload("issue-implementer", "(echo 'safe text' | bash)")))
        # (a | cat) && (true | b) は実際には別パイプライン（cat の出力は bash に渡らない）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat && true | bash"))
        )
        # サブシェル内の sequencing でも、パススルー候補が2個（cat が2回）ある場合は
        # 静的に恒等性を保証できないため対象外のまま（安全側・過検知にはならない。実際には
        # `(cat; cat)` も恒等になるケースだが、既知の残存ギャップとして許容する＝受け入れ基準5）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | (cat; cat) | bash"))
        )

    def test_single_line_filter_extended_flags_bypass_is_denied(self):
        # PR #219 opus レビューで発見（クラスB・実 bash で実行確認済み・Claude 版と同一設計）:
        # sort -r/-u・uniq -u・head/tail の `-c`/`--bytes`（バイト数指定）・head の `-n +1` は、
        # いずれも実際には恒等変換になるが、当初の実装（フラグなしのみ許可）では未対応で
        # 検知漏れになっていた。
        issue_implementer_commands = [
            "echo 'git merge feature' | sort -r | bash",
            "echo 'git merge feature' | sort -u | bash",
            "echo 'git merge feature' | sort -ru | bash",
            "echo 'git merge feature' | uniq -u | bash",
            "echo 'git merge feature' | head -c100 | bash",
            "echo 'git merge feature' | head -c 100 | bash",
            "echo 'git merge feature' | head --bytes=100 | bash",
            "echo 'git merge feature' | tail -c100 | bash",
            "echo 'git merge feature' | head -n +1 | bash",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | sort -r | bash")))

    def test_single_line_filter_extended_flags_does_not_over_deny(self):
        # クラスB是正の副作用確認: 恒等変換にならない／保証できない引数の組み合わせは
        # 引き続き対象外（過検知しない）。
        # head -c5 は "git merge feature" を5バイトに切り詰めるため恒等でない
        # （実 bash で "git m" になることを確認済み）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | head -c5 | bash"))
        )
        # tail -n +2 は「2行目から末尾まで」で head の `-n +N` とは意味が異なり、
        # 単一行入力では出力が空になる（実 bash で確認済み）ため対象外のまま。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | tail -n +2 | bash"))
        )
        # sort -c（check モード）は標準出力に何も書かない（実 bash で確認済み）ため対象外のまま。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | sort -c | bash"))
        )
        # uniq -d（重複行のみ出力）は単一行入力では出力が空になる（実 bash で確認済み）ため
        # 対象外のまま。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | uniq -d | bash"))
        )
        # 通常の無関係な用途を壊さない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | sort -r | wc -l"))
        )

    def test_operator_sequence_multiple_passthrough_and_stderr_redirect_bypass_is_denied(self):
        # PR #219 opus 再レビューで発見（実 bash で実行確認済み・Claude 版と同一設計）: 前回追加した
        # classify_operator_sequence_stage() 自体の以下2種の分岐を突くバイパスが見つかった。
        #   1. 真の passthrough セグメントが2個以上連なる構成（`cat && cat`/`cat; cat`）。
        #   2. stderr のみのリダイレクト付き passthrough（`cat 2>/dev/null` 等。サブシェル内・
        #      パイプ内・サブシェルすら介さないトップレベル段のいずれでも検知漏れだった）。
        # 根本原因は classify_operator_sequence_stage() が None を返す＝安全側（deny 方向）と
        # 誤ってコメントしていたこと（実際には None は fail-open＝allow 方向）。誤ったコメントを
        # 訂正した上で、cat/tee のみに限定した複数セグメント対応と
        # strip_stderr_only_redirections() を追加して是正した。
        issue_implementer_commands = [
            "echo 'git merge feature' | (cat && cat) | bash",
            "echo 'git merge feature' | (cat; cat) | bash",
            "echo 'git merge feature' | (cat || cat) | bash",
            "echo 'git merge feature' | (cat 2>/dev/null) | bash",
            "echo 'git merge feature' | (cat | cat 2>/dev/null) | bash",
            "echo 'git merge feature' | cat 2>/dev/null | bash",
            "echo 'git merge feature' | cat 2> /dev/null | bash",  # 分離形（"2>" "/dev/null"）
            "echo 'git merge feature' | (cat 2>>/dev/null) | bash",  # 追記形（"2>>"）
            "echo 'git merge feature' | (true && cat 2>/dev/null) | bash",
            "echo 'git merge feature' | (cat 2>/dev/null && cat 2>/dev/null) | bash",
            "echo 'git merge feature' | (sort 2>/dev/null) | bash",
            "echo 'git merge feature' | (head -n1 2>/dev/null) | bash",
            # 3個以上の真の passthrough セグメントが連なる場合も、全て unconditional なら
            # 引き続き検知される（2個限定ではない一般化の確認）。
            "echo 'git merge feature' | (cat && cat && cat) | bash",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | (cat && cat) | bash"))
        )
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | cat 2>/dev/null | bash"))
        )

    def test_operator_sequence_multiple_passthrough_and_stderr_redirect_does_not_over_deny(self):
        # 是正の副作用確認（PR #219 opus 再レビュー指摘の敵対的再検証項目を含む・Claude 版と
        # 同一設計）: 恒等変換を壊す、または保証できないリダイレクト・組み合わせは引き続き対象外
        # （過検知しない）。実 bash で挙動を確認済み。
        # `>`（stdout 自体の向け先変更）は恒等ではない（実際には downstream に届かない）ため
        # 対象外のまま。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | (cat > /tmp/agent-gate-test-x) | bash"))
        )
        # ファイルオペランドを伴う場合は stderr リダイレクトを剥がしても「引数あり」のままなので
        # 対象外のまま（標準入力ではなくファイルを読むため）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat notes.txt 2>/dev/null | bash"))
        )
        # 通常の無関係な用途（無害なコマンドに stderr リダイレクトを付けるだけ）を壊さない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | cat 2>/dev/null | wc -l"))
        )

    def test_fd_duplication_redirect_is_a_known_unresolved_gap(self):
        # 既知の未対応残存ギャップ（PR #219 さらなる opus 再レビューで判明・fail-open・
        # Claude 版と同一設計）。
        #
        # `(cat 2>&1)`/`(cat 2>/dev/null 2>&1)` のように stderr を stdout に合流させる fd
        # 複製構文は、実 bash では恒等変換になる（cat が正常終了する限り stderr には何も
        # 書き込まれないため、2>&1 で合流させても stdout の内容は変わらない）。つまり
        # `echo 'git merge evil' | (cat 2>&1) | bash` 等は実際には deny すべきバイパスで
        # あり、実行して allow されることを確認済み。
        #
        # 以前このテスト（同ファイル内の *_does_not_over_deny）は、これを「恒等性を保証
        # できないため安全に allow されるべき over-deny 防止ケース」として誤って assert
        # していた。実際には false negative（見逃し）であり、「安全」ではない。
        #
        # この fd 複製・クローズ構文（`2>&1`・`>&2`・`{fd}>&-` 等の派生を含む）を個別の
        # point-fix で塞ぎ続ける設計は、新しい亜種が見つかるたびに再発するいたちごっこに
        # なっており（本PRだけで既に複数ラウンド発生）、オーナー判断により本PRではこれ以上
        # 追わず、fail-closed への構造転換（認識できない構文は安全側で拒否するアローリスト
        # 方式へ転換する）を Issue #222 として別途起票し、そちらで根本解消する方針とした。
        #
        # このテストは「現状 allow になってしまう」という既知のギャップを意図的に記録する
        # ものであり、正しい挙動として保証しているわけではない。Issue #222 の対応で deny に
        # 変わったら、このテストは失敗するので、その時点で削除・更新すること
        # （assert_allowed を assert_denied に置き換え、コメントも解消済みに更新する）。
        known_gap_commands = [
            "echo 'git merge feature' | (cat 2>&1) | bash",
            "echo 'git merge feature' | (cat 2>/dev/null 2>&1) | bash",
        ]
        for command in known_gap_commands:
            with self.subTest(command=command):
                self.assert_allowed(run_gate(payload("issue-implementer", command)))

    def test_herestring_and_pipe_detection_does_not_over_deny_heredoc_data(self):
        # 実装中の敵対的自己検証で発見（Issue #213・Claude 版と同一設計）:
        # herestring_reexec_bodies/xargs_reexec_bodies/bare_interpreter_reexec_bodies を
        # command_text（生テキスト）に対して走査すると、`cat > file.py <<'EOF' ... EOF` のように
        # 実行されないヒアドキュメント本文（例: サンプルコードやドキュメントの文字列リテラル）の
        # 中にたまたま `<<<`/パイプ経由でインタプリタに渡っているように見える記法が含まれている
        # だけで over-deny してしまう回帰があった（Issue #189 の false positive 是正方針の再侵犯）。
        # scan_text（ヒアドキュメント本文除去済み）を走査対象にすることで、これらのデータは
        # 実行されないため許可されなければならない。
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
        # Claude 版と同じオーナー判断：agent_type が issue-implementer/pr-reviewer のいずれでも
        # ない場合（欠如を含む・main context 自身がこれに該当）は対象外＝常に許可。
        self.assert_allowed(run_gate(payload(None, "git merge feature")))
        self.assert_allowed(run_gate(payload(None, "git push origin HEAD")))
        self.assert_allowed(run_gate(payload(None, "git status")))
        self.assert_allowed(run_gate(payload("general-purpose", "git merge feature")))
        self.assert_allowed(run_gate(payload("general-purpose", "git push origin HEAD")))

    def test_non_shell_tool_is_out_of_scope(self):
        # git/gh は Bash ツール経由でのみ走る。非シェルツール（apply_patch 等）は対象外。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "git merge feature", tool_name="apply_patch"))
        )
        self.assert_allowed(
            run_gate(payload("pr-reviewer", "git push origin HEAD", tool_name="Write"))
        )

    def test_shell_tool_aliases_are_inspected(self):
        # canonical 名 "Bash" 以外の代表的シェル系エイリアスでも検査する（将来の改名への保険）。
        for tool_name in ("shell", "local_shell", "unified_exec", "exec_command"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    run_gate(payload("issue-implementer", "git merge feature", tool_name=tool_name))
                )

    def test_missing_command_denies_because_command_cannot_be_inspected(self):
        self.assert_denied(
            run_gate({"agent_type": "issue-implementer", "tool_name": "Bash", "tool_input": {}})
        )
        self.assert_denied(run_gate({"agent_type": "issue-implementer", "tool_name": "Bash"}))

    def test_invalid_json_denies(self):
        result = subprocess.run(
            [str(HOOK)],
            input="not-json",
            text=True,
            capture_output=True,
            check=True,
            # 既定パス（~/.codex/agent-command-gate-trace.log）を汚染しないよう無効化する。
            env={**os.environ, "AGENT_COMMAND_GATE_TRACE_LOG": ""},
        )
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_subagent_type_fallback_is_supported(self):
        self.assert_denied(
            run_gate(
                {
                    "subagent_type": "issue-implementer",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git merge feature"},
                }
            )
        )

    def test_debug_payload_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "payload.log"
            output = run_gate(
                {
                    "agent_type": "issue-implementer",
                    "tool_name": "Bash",
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
            self.assertEqual(deny_record["tool_name"], "Bash")
            self.assertIn("ts", deny_record)
            self.assertEqual(set(deny_record.keys()), {"ts", "agent_type", "tool_name", "decision"})
            self.assertEqual(allow_record["decision"], "allow")
            self.assertEqual(allow_record["agent_type"], "issue-implementer")
            # command 本文・その他 payload フィールドが漏れていないことを確認する。
            raw_text = log_path.read_text()
            self.assertNotIn("git merge feature", raw_text)
            self.assertNotIn("git push origin HEAD", raw_text)

    def test_trace_log_records_invalid_json_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "trace.log"
            result = subprocess.run(
                [str(HOOK)],
                input="not-json",
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "AGENT_COMMAND_GATE_TRACE_LOG": str(log_path)},
            )
            self.assertTrue(result.stdout)
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["decision"], "deny")
            self.assertIsNone(record["agent_type"])

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
