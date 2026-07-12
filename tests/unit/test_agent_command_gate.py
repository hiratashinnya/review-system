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
        # 過検知しない。これは sink 自体が interpreter-reading-stdin と確定できない（位置引数が
        # ある）ケースであり、fail-closed の対象にはならない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash script.sh"))
        )
        # Issue #222 fail-closed 設計転換: 上流が非リテラル（`cat notes.txt` のようにファイル
        # オペランドを読む等）の場合、以前は「静的に値を確定できないため対象外＝allow」だったが、
        # sink（bash）は確定しているのに内容を安全と確認できない以上、fail-closed で deny に
        # 転じる（over-deny 増加を許容する Issue #222 の決定事項。issue-implementer/pr-reviewer が
        # 任意のファイル内容を interpreter へパイプする正当な必要性は通常ない）。
        self.assert_denied(run_gate(payload("issue-implementer", "cat notes.txt | bash")))

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
        #    echo リテラルは実際には bash に渡らない（パイプの意味論としては真に無関係）。ただし
        #    Issue #222 fail-closed 設計転換により、「echo の値が渡らないこと」自体は事実でも
        #    「notes.txt の中身が bash に渡ること」は排除できず、classify_passthrough_stage は
        #    これを（disconnected ではなく）unverifiable として扱う。sink（bash）が確定している
        #    以上、内容を安全と確認できない限り deny する（over-deny 増加を許容する Issue #222 の
        #    決定事項として意図的に受け入れる）。
        self.assert_denied(
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
        # Issue #218 ギャップ1（PR #216 の opus 敵対的レビューで発見）: PIPE_ONLY_RE.split() は
        # トップレベルの `|` を素朴に全分割するため、`( ... | ... )` のような丸括弧サブシェルを
        # 含むパイプラインでは、サブシェル内部の `|` まで分割対象にしてしまい `(cat`/`cat)` という
        # 不正な字句が生まれ、パススルー追跡が途切れて検知漏れになっていた（実行して確認済み：
        # `echo 'git merge evil' | (cat | cat) | bash` が allow されていた）。
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
        # cat がサブシェル内でファイルオペランドを持つ場合、標準入力ではなく notes.txt を読む
        # ため producer の echo リテラルは渡らないが、Issue #222 fail-closed 設計転換により
        # notes.txt の中身自体を安全と確認できない以上 deny する（over-deny 増加を許容する
        # Issue #222 の決定事項として意図的に受け入れる。上の関連テストと同じ理由づけ）。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | (cat notes.txt) | bash"))
        )
        # 開き括弧のみで閉じ括弧が来ない不正形式は検査不能側に倒して従来どおり過検知しない
        # （パイプの継続性が追えないだけで、既存の direct_violation 走査には影響しない）。
        self.assert_allowed(run_gate(payload("issue-implementer", "echo '(unbalanced'")))

    def test_single_line_filter_passthrough_bypass_is_denied(self):
        # Issue #218 ギャップ2（PR #216 の opus 敵対的レビューで発見）: PASSTHROUGH_COMMANDS が
        # cat/tee のみで、sort/head/tail/uniq を挟んだパイプラインが検知漏れになっていた
        # （実行して確認済み：`echo 'git merge evil' | sort | bash` 等が allow されていた）。
        # sort/head/tail/uniq は「引数なし（sort/uniq）」「正の行数指定のみ、または引数なし
        # （head/tail）」の場合に限り、単一行入力に対する恒等変換として扱う。
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
        # Issue #218 時点（fail-open 設計）では、sort/head/tail/uniq の恒等変換にならない引数の
        # 組み合わせ（`uniq -c`／`head -n0`／ファイルオペランドを伴う `sort file.txt` 等）は
        # 「恒等性を保証できないためパススルー扱いにしない＝allow のまま」だった。
        #
        # Issue #222（fail-closed 設計転換）でこの前提が変わった: sink（bash）は確定しているのに
        # 内容を安全と確認できない以上、"確定できない" は "deny" 側に倒れる。以下は全て
        # 意図的な over-deny の新規発生であり、Issue #222 の決定事項として受け入れる
        # （issue-implementer/pr-reviewer が任意のファイル内容や、恒等性を保証できない変換結果を
        # interpreter へパイプする正当な必要性は通常ない）。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | uniq -c | bash"))
        )
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | head -n0 | bash"))
        )
        self.assert_denied(
            run_gate(payload("issue-implementer", "sort notes.txt | bash"))
        )
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | sort file.txt | bash"))
        )
        # grep/tr は UNCONDITIONAL/SINGLE_LINE のいずれの列挙にも含まれず classify_simple_command_stage
        # が (None, None) を返すため、これも fail-closed の対象になり deny する。これは Issue #220
        # （cut/awk/sed/tr 等の恒等変換フィルタ列挙方式の限界）が、個別列挙の拡張ではなく本設計転換
        # そのものによって根本的に解消されることを示す（受け入れ基準1・Issue #222 スコープに明記）。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | grep git | bash"))
        )
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | tr a-z A-Z | bash"))
        )
        # 通常の無関係な用途（sink が bash 等の interpreter ではない）は引き続き壊さない。
        # `wc` は HEREDOC_INTERPRETER_COMMANDS に含まれないため、そもそも fail-closed のトリガー
        # 対象にならない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | sort | wc -l"))
        )

    def test_subshell_wraps_consumer_or_whole_pipeline_bypass_is_denied(self):
        # PR #219 opus レビューで発見（クラスA・実 bash で実行確認済み）: 前回の
        # split_top_level_pipes/strip_matching_parens は「中間パススルー段としてのサブシェル」
        # のみに対応しており、consumer 位置・パイプライン全体を囲むサブシェルは未対応だった。
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
        # PR #219 opus レビューで発見（クラスB・実 bash で実行確認済み）: sort -r/-u・uniq -u・
        # head/tail の `-c`/`--bytes`（バイト数指定）・head の `-n +1` は、いずれも実際には
        # 恒等変換になるが、当初の実装（フラグなしのみ許可）では未対応で検知漏れになっていた。
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
        # クラスB是正時点（fail-open 設計）では、恒等変換にならない／保証できない引数の組み合わせは
        # 対象外（allow）だった。Issue #222（fail-closed 設計転換）でこの前提が変わり、以下は全て
        # 意図的な over-deny の新規発生として受け入れる（sink が確定している以上、恒等でないと
        # 判明している＝安全と確認できないので deny する）。
        # head -c5 は "git merge feature" を5バイトに切り詰めるため恒等でない
        # （実 bash で "git m" になることを確認済み）→ byte_cap 超過で deny。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | head -c5 | bash"))
        )
        # tail -n +2 は「2行目から末尾まで」で head の `-n +N` とは意味が異なり、
        # 単一行入力では出力が空になる（実 bash で確認済み）→ 未対応フラグとして deny。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | tail -n +2 | bash"))
        )
        # sort -c（check モード）は標準出力に何も書かない（実 bash で確認済み）→ 未対応フラグ
        # として deny。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | sort -c | bash"))
        )
        # uniq -d（重複行のみ出力）は単一行入力では出力が空になる（実 bash で確認済み）→
        # 未対応フラグとして deny。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | uniq -d | bash"))
        )
        # 通常の無関係な用途（sink が interpreter ではない）は引き続き壊さない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | sort -r | wc -l"))
        )

    def test_operator_sequence_multiple_passthrough_and_stderr_redirect_bypass_is_denied(self):
        # PR #219 opus 再レビューで発見（実 bash で実行確認済み）: 前回追加した
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
        # PR #219 時点（fail-open 設計）では、恒等変換を壊す／保証できないリダイレクト・組み合わせは
        # 対象外（allow）だった。Issue #222（fail-closed 設計転換）でこの前提が変わった。
        # `>`（stdout 自体の向け先変更）は producer の echo リテラルが実際には bash に届かないが
        # （実 bash で確認済み・真に無関係）、classify_passthrough_stage は「file への出力」を
        # disconnected とは判定せず unverifiable として扱う（`>`/`>>` 等の stdout リダイレクトは
        # strip_stderr_only_redirections の対象外＝非フラグの位置引数として cat の file-operand
        # チェックに引っかかる）ため、sink（bash）が確定している以上 deny する。issue-implementer/
        # pr-reviewer がこのようなリダイレクトを伴うパイプを interpreter へ渡す正当な必要性は
        # 通常なく、意図的な over-deny として受け入れる（Issue #222 決定事項）。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | (cat > /tmp/agent-gate-test-x) | bash"))
        )
        # ファイルオペランドを伴う場合は stderr リダイレクトを剥がしても「引数あり」のままであり
        # （標準入力ではなくファイルを読むため producer の echo リテラルは届かない）、上と同じ
        # 理由づけで fail-closed の対象になり deny する。
        self.assert_denied(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | cat notes.txt 2>/dev/null | bash"))
        )
        # 通常の無関係な用途（sink が interpreter ではない）は引き続き壊さない。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | cat 2>/dev/null | wc -l"))
        )

    def test_fd_duplication_redirect_bypass_is_denied(self):
        # Issue #222（fail-closed 設計転換）でこのギャップは解消された。以前は
        # test_fd_duplication_redirect_is_a_known_unresolved_gap という名前で、以下2件が
        # 「既知の未対応残存ギャップ（fail-open のため allow になってしまう）」として意図的に
        # 記録されていた（PR #219 さらなる opus 再レビューで発見。fd 複製・クローズ構文
        # `2>&1`・`>&2`・`{fd}>&-` 等は個別の point-fix を重ねるたびに新しい亜種が見つかる
        # いたちごっこだった）。
        #
        # `(cat 2>&1)`/`(cat 2>/dev/null 2>&1)` は実 bash では恒等変換になる（cat が正常終了
        # する限り stderr には何も書き込まれないため、2>&1 で合流させても stdout の内容は
        # 変わらない）ため、実際には deny すべきバイパスだった。
        #
        # classify_simple_command_stage は `2>&1`（_STDERR_DISCARD_TOKEN_RE が `(?!&)` で
        # 除外するため strip_stderr_only_redirections で剥がされない）を非フラグの位置引数と
        # 扱い、cat の file-operand チェックに引っかけて (None, None) を返す。以前はこれが
        # 「確定できない＝ALLOW」だったが、Issue #222 の設計転換により
        # literal_producer_value_through_passthrough はこれを _UNVERIFIABLE_PRODUCER として
        # 扱い、sink（bash）が確定している以上 deny する。個別の `2>&1` 対応を追加したのでは
        # なく、"分類できないものは全て deny" という単一の原理で自動的に閉じたことを確認する
        # テスト（受け入れ基準1・2）。
        bypass_commands = [
            "echo 'git merge feature' | (cat 2>&1) | bash",
            "echo 'git merge feature' | (cat 2>/dev/null 2>&1) | bash",
        ]
        for command in bypass_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

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

    def test_issue_220_enumeration_gap_is_resolved_by_fail_closed_design(self):
        # Issue #220: PASSTHROUGH_COMMANDS/SINGLE_LINE_PASSTHROUGH_COMMANDS の列挙方式は、
        # cut/awk/sed/rev 等 cat/tee/sort/head/tail/uniq 以外の恒等変換フィルタに対応しておらず、
        # 無限に列挙が必要になるという設計限界が指摘されていた（Issue #218 の PR #219 レビューで
        # 判明・実行して恒等変換になることを確認済みの Issue #220 記載の PoC）。Issue #222 の
        # fail-closed 設計転換は、恒等性を証明できないコマンドは全て deny するため、これらは
        # 個別列挙の追加なしに自動的に閉じる（受け入れ基準1）。
        commands = [
            "echo 'git merge feature' | cut -c1-1000 | bash",
            "echo 'git merge feature' | rev | rev | bash",
            "echo 'git merge feature' | awk '{print}' | bash",
            "echo 'git merge feature' | sed 's/x/x/' | bash",
            "echo 'git merge feature' | tac | bash",
            "echo 'git merge feature' | base64 | base64 -d | bash",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

    def test_pr219_round3_fd_and_novel_syntax_bypasses_are_denied_structurally(self):
        # Issue #222 実装時の敵対的自己検証で発見。個別の point-fix ではなく fail-closed の
        # 設計原理そのものによって塞がれることを確認する（列挙ベースの対応を一切追加していない）。
        commands = [
            # fd 複製/クローズ構文（PR #219 3ラウンド目のバイパス群）。
            "echo 'git merge feature' | cat 0<&0 | bash",
            "echo 'git merge feature' | cat 2>&- | bash",
            # `|&`（stdout+stderr をまとめてパイプする省略記法）。split_top_level_pipes が
            # `|` の直後の `&` を消費し損ね、`& bash` という不正な字句が生まれて producer 追跡が
            # 打ち切られ、fail-closed 判定にすら至らず ALLOW していた新規発見バグ。
            "echo 'git merge feature' | cat |& bash",
            # ブレースグルーピング `{ ... }`（Issue #218 では丸括弧サブシェルのみスコープだった）。
            # `{ cat; }` 内の `;` が、丸括弧非対応のまま新設の
            # _DISCONNECTED_OPERATOR_SEQUENCE 判定に誤って合致し、「確定的に無関係」と誤認して
            # 見逃す新規発見バグ。
            "echo 'git merge feature' | { cat; } | bash",
            "echo 'git merge feature' | { { cat; }; } | bash",
            # xargs -I{} のプレースホルダそのものがコマンド全体になる形。
            "echo 'git merge feature' | xargs -I{} {}",
            # プロセス置換をインタプリタの位置引数として渡す形（`bash <(CMD)`）。既存の
            # 「位置引数があれば標準入力を読まないため対象外」ロジックが `<(...)` を実ファイル
            # パスと誤同一視していた新規発見バグ。
            "bash <(echo 'git merge feature')",
            "sh <(echo 'git merge feature')",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | cat |& bash")))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | { cat; } | bash"))
        )
        self.assert_denied(run_gate(payload("pr-reviewer", "bash <(echo 'git push origin HEAD')")))

    def test_unenumerated_novel_construct_denies_by_default_not_by_listing(self):
        # 受け入れ基準2: 「今回のレビューで能動的に試されていない亜種」でも、列挙されていない
        # 限り deny 側に倒れることを実演する。以下のコマンドは、このコミット時点で
        # PASSTHROUGH_COMMANDS/SINGLE_LINE_PASSTHROUGH_COMMANDS/HEREDOC_INTERPRETER_COMMANDS の
        # いずれにも個別列挙されていない全く新規のコマンド名・構文であり、fail-closed の設計
        # 原理（classify_passthrough_stage が確定できないものは全て _UNVERIFIABLE_PRODUCER）に
        # よってのみ deny される。将来 bash に新しいビルトインや外部コマンドが追加されても、
        # 明示的な追加対応なしに安全側に倒れることの実証。
        commands = [
            # このリポジトリのどの列挙にも含まれない、架空の外部フィルタコマンド名。
            "echo 'git merge feature' | totally-made-up-filter-xyz | bash",
            # dd（同じく未列挙）を経由。
            "echo 'git merge feature' | dd 2>/dev/null | bash",
            # 複数の未列挙コマンドを重ねる。
            "echo 'git merge feature' | nl | column | bash",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

    def test_stdin_alias_positional_arg_bypass_is_denied(self):
        # PR #223 opus 再レビュー指摘A（2026-07-13・最重要）: `/dev/stdin`・`/dev/fd/N`・
        # `/proc/self/fd/N` は OS が提供する「自プロセスの標準入力」を指す疑似ファイルパスで
        # あり、`bash /dev/stdin` はファイルではなく実質的に標準入力をスクリプトとして読む。
        # bare_interpreter_reexec_bodies の「位置引数があれば標準入力を読まないため対象外」
        # という前提がこれらの疑似パスに対して事実誤認であり、本PRが `<(...)` プロセス置換で
        # 修正したのと全く同じバグクラス（実 bash で実際に実行されることを確認済み）。
        issue_implementer_commands = [
            "echo 'git merge feature' | bash /dev/stdin",
            "echo 'git merge feature' | sh /dev/stdin",
            "echo 'git merge feature' | source /dev/stdin",
            "echo 'git merge feature' | . /dev/stdin",
            "echo 'git merge feature' | bash /dev/fd/0",
            "echo 'git merge feature' | bash /proc/self/fd/0",
            "echo 'git merge feature' | bash /proc/12345/fd/3",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | bash /dev/stdin")))
        # 実在のスクリプトファイルパス（stdin エイリアスに一致しない）は引き続き対象外のまま
        # （新規の過検知を避ける・既存の over-deny 防止テストと同じ理由づけ）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash script.sh"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'git merge feature' | bash /home/user/repo/script.sh"))
        )

    def test_xargs_without_placeholder_bypass_is_denied(self):
        # PR #223 opus 再レビュー指摘B（2026-07-13）: `-I` を使わない xargs は、stdin から
        # 読んだトークンをコマンドの末尾に追記して実行する。xargs_reexec_bodies は `-I` の
        # 有無で判定しており、この形式は一切見ていなかったため素通りしていた（実 bash で
        # 実際に実行されることを確認済み）。オーナー方針転換により、xargs が実行しようと
        # しているコマンドの先頭が git/gh/interpreter である場合、producer 値の確定可否に
        # よらず一律 deny する。
        issue_implementer_commands = [
            "echo 'git merge feature' | xargs -0 bash -c",
            "echo 'git merge feature' | grep . | xargs -0 bash -c",
            "echo 'git merge feature' | xargs bash -c",
            "echo 'git merge feature' | xargs git",
            "echo 'git merge feature' | xargs -n1 gh",
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | grep . | xargs -0 bash -c"))
        )
        # 既存の一般的な xargs イディオムは引き続き壊さない（コマンドの先頭が git/gh/interpreter
        # 以外の場合は対象化しない・受け入れ基準4）。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "find . -name '*.txt' | xargs -I{} wc -l {}"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "find . -name '*.pyc' | xargs rm -f"))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", "echo 'safe text' | xargs -n1 echo"))
        )

    def test_dynamic_sink_and_stdin_loop_bypass_is_denied(self):
        # PR #223 opus 再レビュー指摘C（2026-07-13・オーナー方針転換「過剰denyを許容する。
        # 危険コマンドや疑わしいコマンドが含まれていれば、実行されるか気にせずブロックしていい」）:
        # パイプ consumer の先頭コマンド語が `$(...)`／バッククォート／`${...}` で動的に構成
        # されている場合、それが interpreter か無害なコマンドかを静的に判定できない。また
        # `while`/`until` から始まり `read` を含む stdin 読み取りループは、中身を精査せず
        # 一律 deny する（実 bash でいずれも実際にペイロードが実行されることを確認済み）。
        issue_implementer_commands = [
            "echo 'git merge feature' | grep . | $(echo bash)",
            "echo 'git merge feature' | grep . | ${SHELL##*/}",
            "echo 'git merge feature' | grep . | `echo bash`",
            'echo \'git merge feature\' | while read l; do eval "$l"; done',
            'echo \'git merge feature\' | until read l; do eval "$l"; done',
        ]
        for command in issue_implementer_commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))
        self.assert_denied(
            run_gate(payload("pr-reviewer", "echo 'git push origin HEAD' | grep . | $(echo bash)"))
        )
        self.assert_denied(
            run_gate(
                payload("pr-reviewer", 'echo \'git push origin HEAD\' | while read l; do eval "$l"; done')
            )
        )
        # 通常の変数展開・コマンド置換の「引数としての」利用（コマンド名自体ではない）は
        # 引き続き壊さない。
        self.assert_allowed(run_gate(payload("issue-implementer", "echo $(git rev-parse HEAD)")))
        self.assert_allowed(
            run_gate(payload("issue-implementer", 'git commit -m "deploy ${VERSION}"'))
        )
        self.assert_allowed(
            run_gate(payload("issue-implementer", 'echo "current branch: $(git branch --show-current)"'))
        )
        # 無害な for ループは壊さない（while/until 以外のループ構文・read を含まない構文は対象外）。
        self.assert_allowed(run_gate(payload("issue-implementer", "for f in *.py; do echo $f; done")))


if __name__ == "__main__":
    unittest.main()
