#!/usr/bin/env bash
# Codex CLI PreToolUse フックハンドラ（.claude/hooks/agent-command-gate.sh の Codex 版）。
#
# 役割:
#   "issue-implementer" / "pr-reviewer" subagent（Codex custom subagent の role 名）に対して、
#   push と merge の非対称な権限境界を機械的に強制する。Claude Code 版と同じく、プロンプト指示
#   ではなくハーネス（Codex CLI の PreToolUse フック）で拒否する。ただしシェル文字列の静的検査
#   には限界があるため、本フックは多層防御の一枚として扱う。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - pr-reviewer:        merge は可、push は不可（レビュー中に無レビューの変更を紛れ込ませられない）。
#   それ以外の agent_type（main／各 *-author 等・agent_type 欠如を含む）はこのゲートの対象外＝許可。
#
# Codex CLI 対応の一次資料（codex-cli 0.142.5 / openai/codex main で確認）:
#   - 入力スキーマ codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json:
#       agent_type（任意・subagent の role 名が入る）／tool_name（必須）／tool_input（必須・任意型）等。
#   - 出力スキーマ codex-rs/hooks/schema/generated/pre-tool-use.command.output.schema.json:
#       hookSpecificOutput.{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason}
#       で拒否する。permissionDecision:"deny" は非空の permissionDecisionReason を要求する
#       （codex-rs/hooks/src/engine/output_parser.rs）。この deny ワイヤ形式は Claude Code と同一。
#   - シェルコマンドの tool_name は "Bash"、tool_input.command は文字列
#       （codex-rs/core/src/tools/hook_names.rs の HookToolName::bash()、
#        codex-rs/core/src/hook_runtime.rs で tool_input.command を string として参照）。
#   - agent_type は spawn された subagent の role 名（= .codex/agents/*.toml の name）
#       （codex-rs/core/src/hook_runtime.rs subagent_hook_context / SubagentHookContext.agent_type）。
#   - 登録形式は .codex/hooks.json の "PreToolUse": [{ "matcher": "Bash", "hooks": [...] }]
#       （codex-rs/config/src/hook_config.rs の HookEventsToml.pre_tool_use / MatcherGroup）。
#     プロジェクトローカルフックは初回に `/hooks` で trust する必要がある（trusted_hash）。
#
# 既知の限界（Issue #129 / #181・多層防御の一枚に過ぎない）:
#   このフックは Bash command 文字列を静的に検査する。直接呼び出し、複数行、環境変数プレフィックス、
#   rtk ラッパー、代表的な bash -c/eval/コマンド置換は検知対象に含めるが、任意のラッパースクリプト、
#   難読化、別インタプリタ内の任意コード、動的に組み立てられるコマンドまでは閉じきれない。
#   加えて Codex 側特有の限界として、(a) フックは `/hooks` で trust されて初めて発火する、
#   (b) requirements.toml/config.toml でフックが無効化され得る、(c) agent_type に実際どの文字列が
#   入るかは dogfooding で最終確認すべき（Claude issue #129 項目1 と同じ fail-open リスク・
#   AGENT_COMMAND_GATE_DEBUG_PAYLOAD で受信 payload を確認できる）。pr-reviewer.toml / issue-implementer.toml
#   側のプロンプトレベルの規範と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type と tool_name と tool_input.command を想定）。
#   agent_type が issue-implementer/pr-reviewer のいずれでもない場合（欠如を含む）はこのゲートの
#   対象外＝常に許可する。tool_name がシェル系（Bash 等）でない場合も許可する（git/gh は Bash 経由の
#   ため）。シェル系ロールでコマンド文字列が読めない場合は検査不能として deny する（fail-closed）。
#
#   Claude 版と同じオーナー判断を踏襲：agent_type 欠如時（main context 自身）に危険コマンドを
#   fail-closed で deny すると main context の直接 push まで塞ぐ回帰が出るため、「対象外ロールは常に許可」
#   とする（agent_type 詐称防御は失うが、二者択一の上でのオーナー明示判断・Claude issue #129）。
# デバッグ: AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log を設定すると、受信 payload の redacted JSON と
#   判定を追記する（オプトイン・機微値はキー名ベースで伏せる）。
# トレース（Issue #192・常時有効）: 呼ばれるたびに時刻・agent_type・tool_name・判定(allow/deny)のみを
#   既定で ~/.codex/agent-command-gate-trace.log に1行追記する（command 本文・生 payload は含まない）。
#   パスは AGENT_COMMAND_GATE_TRACE_LOG で上書き、空文字で無効化できる。詳細は README.md 参照。
#
#   2026-07-11 是正の経緯（Issue #189）：quoted_subcommands/quoted_literals による難読化対策の
#   副作用で、`gh pr create --body "$(cat <<'EOF' ... EOF)"` のようにヒアドキュメントで PR 本文・
#   コミットメッセージを渡す（本フック自身の運用規約が推奨する書き方）際、本文中の散文的な引用
#   （例: Markdown インラインコード `git merge`）を独立したトップレベルコマンドと誤認して
#   over-deny していた。ヒアドキュメント本文はシェル上「直前コマンドへの入力データ」であって
#   コマンド列ではないため、direct_violation の素朴な走査対象から除外し、実際にインタプリタへの
#   入力として再実行される場合（`bash <<'EOF' ... EOF` 等）だけ本文を素のテキストとして再帰走査する
#   よう是正した（詳細は find_violation/extract_heredocs のコメント参照。Claude 版と同一設計）。
#   既存の eval/bash -c/python -c 経由の難読化検知（quoted_subcommands）は無変更。
#
#   2026-07-12 追加是正（Issue #189・pr-reviewer レビュー指摘・PR #212・Claude 版と同一設計）：
#   上記の是正が heredoc_command_word() で「`<<` の直前・同一行のコマンド語」しか見ておらず、その
#   stdout が下流パイプでインタプリタに渡る経路（`cat <<'EOF' | bash` / `cat <<EOF | bash`
#   （非引用デリミタ）/ `cat <<-'EOF' | bash`（`<<-` ダッシュ版）/
#   `cat <<'EOF' | tee /tmp/x | bash`（多段パイプ）等）を捕捉できておらず、本来 deny すべきものが
#   軒並み allow される重大バイパスがあった。「本文を除外する前に、そのヒアドキュメントが最終的に
#   インタプリタへ渡る経路（直接 `bash <<EOF` でも、パイプ経由でも）が無いことを確認できた場合のみ
#   除外する」という、より保守的な（除外条件を厳しくする）方向で
#   heredoc_pipeline_has_downstream_interpreter() を追加し、マーカー行内のパイプ下流ステージに
#   インタプリタが見つかれば reexec_bodies に含めて depth+1 で再帰走査するよう拡張した
#   （詳細は heredoc_pipeline_has_downstream_interpreter/extract_heredocs のコメント参照）。
#
#   2026-07-12 追加是正その2（Issue #189・PR #212 再レビュー指摘・Claude 版と同一設計）：
#   HEREDOC_INTERPRETER_COMMANDS に bash 組み込みの `source`/`.`（同義・カレントシェルでスクリプトを
#   再実行するコマンド）が含まれておらず、`cat <<'EOF' | source /dev/stdin`（`. /dev/stdin` も同様）
#   でヒアドキュメント本文が再実行されるにもかかわらず allow されていた（PR #212 の base=main では
#   偶然 deny されていた挙動が本PRの変更で allow に変わる回帰だった）。source/. を
#   HEREDOC_INTERPRETER_COMMANDS に追加して是正。
#
#   2026-07-12 追加是正その3（Issue #213・PR #212 sonnet 再レビューで発見・既存ギャップ・
#   Claude 版と同一設計）：以下3経路が実際にコマンドを実行するにもかかわらず allow されていた。
#     1. here-string 経由：`bash <<< 'git merge evil'`。HEREDOC_RE は `<<` の直後に識別子を
#        要求するため `<<<`（3文字目が `<`）にはそもそもマッチせず、検知対象外だった。
#     2. xargs プレースホルダ置換経由：`echo 'git merge evil' | xargs -I{} bash -c '{}'`。
#        quoted_subcommands はリテラル文字列 `{}` をそのまま抽出するだけで、実行時に xargs が
#        代入する実際の値（パイプ上流のリテラル）を追えていなかった。
#     3. 一般パイプ経由（ヒアドキュメントを使わない素朴なパイプ）：`printf '%s' 'git merge evil' | bash`。
#   herestring_reexec_bodies/xargs_reexec_bodies/bare_interpreter_reexec_bodies を追加し、
#   いずれも「パイプ上流が echo/printf のみで構成される静的リテラルの場合に限り」実行時に渡る値を
#   静的に確定して reexec 対象に含める設計とした（上流が `find` の結果や変数展開等の非リテラルの
#   場合は静的に決定できないため対象外＝新規の過検知を出さない）。完全な網羅は目指さない（受け入れ
#   基準5）。詳細は各関数のコメント参照（詳細設計は Claude/Codex 両版で同一）。
#
#   2026-07-12 追加是正その4（Issue #215・Issue #213/PR #214 の opus 敵対的レビューで発見・
#   Claude 版と同一設計）：bare_interpreter_reexec_bodies/xargs_reexec_bodies は
#   literal_producer_value を「直前ステージ（stages[i-1]）のみ」に適用していたため、リテラル
#   producer とインタプリタの間に `cat`/`tee` 等のパススルーを1段挟むと検知が外れていた
#   （`echo 'git merge evil' | cat | bash` 等を実行して allow されることを確認済み）。同PR自身の
#   ヒアドキュメント経路（heredoc_pipeline_has_downstream_interpreter）は既に多段パススルーに
#   対応済みで、bare-pipe/xargs 経路だけが非対称だった。is_pure_passthrough_stage/
#   literal_producer_value_through_passthrough を追加し、直前ステージが純粋なパススルー
#   （演算子を含まず、cat はファイルオペランドを持たない）である限りさらに前段へ literal
#   producer の確定を遡るよう対称化した。過度なパススルーコマンドの網羅は目指さない（受け入れ
#   基準6・cat/tee の代表例に限定）。詳細は各関数のコメント参照。
#
#   2026-07-12 追加是正その5（Issue #218・PR #216 の opus 敵対的レビューで発見・既存ギャップ2件・
#   Claude 版と同一設計）：
#     1. サブシェル括弧グルーピング未対応：PIPE_ONLY_RE.split() はトップレベルの `|` を素朴に
#        全分割し、丸括弧サブシェル `( ... | ... )` を認識しなかったため、
#        `echo 'git merge evil' | (cat | cat) | bash` のようなパイプラインで `(cat`/`cat)` という
#        不正な字句が生まれ、literal_producer_value_through_passthrough の遡及がそこで打ち切られ
#        検知漏れになっていた（実行して確認済み）。split_top_level_pipes()/strip_matching_parens() を
#        追加し、丸括弧の深さを追跡しながら分割・剥離することで、サブシェル全体を1段のパススルー
#        として扱えるようにした（波括弧 `{ ... ; }` 等サブシェル以外のグルーピング構文への一般化は
#        対象外＝スコープ外・Issue #218 受け入れ基準）。
#     2. cat/tee 以外の単一行保存フィルタ未対応：`echo 'git merge evil' | sort | bash` /
#        `... | head -n1 | bash` / `... | uniq | bash` 等、sort/head/tail/uniq を挟んだパイプラインが
#        検知漏れになっていた。cat/tee は入力の行数や内容に関わらず常に恒等変換（UNCONDITIONAL）だが、
#        sort/head/tail/uniq は複数行入力や一部フラグでは恒等変換にならないため、
#        「引数なし（sort/uniq）」「正の行数指定のみ、または引数なし（head/tail）」の場合に限り、かつ
#        最終的に確定する producer 値が実際に改行を含まない単一行であることを別途確認した場合のみ
#        （SINGLE_LINE）恒等とみなす2区分の設計にした（classify_passthrough_stage/
#        is_single_line_identity_args）。`grep`/`tr` は恒等変換にならないため対象外（受け入れ基準3・
#        スコープ外として明記）。詳細は各関数のコメント参照。
#
#   2026-07-12 追加是正その6（PR #219 の opus 敵対的レビューで発見・同PR内で追加是正・
#   オーナー承認「実装者に差し戻して同PR内でA+Bも修正」・Claude 版と同一設計）：その5の実装に
#   対し、実 bash で実行確認された残存バイパス2クラスが見つかった。
#     クラスA（サブシェル・consumer/パイプライン全体のラップ）: split_top_level_pipes/
#       strip_matching_parens は「中間パススルー段としてのサブシェル」のみに対応しており、
#       `echo 'git merge evil' | (bash)`（consumer 位置を丸括弧で包む）・
#       `(echo 'git merge evil' | bash)`（パイプライン全体を丸括弧で包む）・
#       `echo 'git merge evil' | (cat | cat) | (bash)`（両方の組み合わせ）・
#       `echo 'git merge evil' | (cat && true) | bash`・`echo 'git merge evil' | (true; cat) | bash`
#       （サブシェル内の sequencing 演算子）が未対応で、いずれも実行して allow されることを
#       確認した。unwrap_redundant_parens()/top_level_pipeline_stages() で consumer 側・
#       パイプライン全体のラップを剥がし、classify_subshell_body()/classify_operator_sequence_stage()
#       でサブシェル内の sequencing 演算子（&&/;）を、true/:/false のような「標準出力を一切
#       生成しないことが既知のコマンド」と組み合わさる場合に限り安全側で解決するようにした
#       （トップレベル＝丸括弧の外側での &&/; は既存どおり対象外のまま。シェルの結合優先順位
#       `|` > `&&`/`;` により実際に別パイプラインへ分かれてしまうため。詳細は
#       classify_operator_sequence_stage のコメント参照）。
#     クラスB（sort/head/tail の恒等フラグの過小評価）: その5の実装は sort/uniq をフラグなしのみ
#       許可していたが、`sort -r`/`sort -u`/`uniq -u` は単一行入力に対しては実際には恒等変換
#       であり、deny すべきなのに allow されていたバイパスだった。同様に head/tail の
#       `-c`/`--bytes`（バイト数指定）・head の `-n +1` も未対応だった。
#       is_single_line_identity_args を (is_safe, byte_cap) を返す設計に拡張し、sort/uniq は
#       検証済みの安全なフラグ集合（SORT_SAFE_FLAG_CHARS={"r","u"}/UNIQ_SAFE_FLAG_CHARS={"u"}）
#       のみ許可、head/tail のバイト数指定は producer 値の実際のバイト長が指定値以下の場合に
#       限り恒等とみなす byte_cap 判定を追加した（`head -c5` で "git merge evil" が "git m" に
#       切り詰められ恒等でなくなることを実行して確認済みのため、バイト数の妥当性は動的に
#       検証する）。
#   受け入れ基準の scope は変わらず：`grep`/`tr` の対応、cut/awk/sed 等の他フィルタコマンドへの
#   一般化は Issue #220 として別起票済み・本是正では対象外。詳細は各関数のコメント参照。
#
#   2026-07-12 追加是正その7（PR #219 の opus 再レビューで発見・同PR内で追加是正・オーナー承認
#   「実装者に差し戻して同PR内で修正」・Claude 版と同一設計）：その6で追加した
#   classify_operator_sequence_stage() 自体の分岐を突く新規バイパス5件が実 bash で見つかった：
#     `echo 'git merge evil' | (cat && cat) | bash` / `... | (cat; cat) | bash`（真の
#     passthrough セグメントが2個以上連なる構成）・`... | (cat 2>/dev/null) | bash` /
#     `... | (cat | cat 2>/dev/null) | bash` / `... | cat 2>/dev/null | bash`（stderr
#     リダイレクト付き passthrough。最後の1件はサブシェルすら介さないトップレベル段）。
#   根本原因はレビュアー指摘のとおり、classify_operator_sequence_stage() が「None を返す＝
#   安全側（deny 方向）」と誤ってコメントしていたことにあった：実際には None を返すと
#   呼び出し元 literal_producer_value_through_passthrough の遡及チェーンが打ち切られ reexec
#   対象に載らなくなる＝fail-open（allow・見逃し）だった。誤ったコメントを訂正した上で、
#   (1) 真の passthrough セグメントが2個以上連なる構成（`cat && cat`/`cat; cat`）を、
#   全セグメントが "unconditional"（cat/tee・byte_cap なし）の場合に限り追加対応し（cat/tee は
#   必ず標準入力を最後まで読み切るため、複数個連なっても2個目以降は EOF で何も出力しないことが
#   read() のバッファリング実装に関わらず保証できる。実 bash で確認済み）、
#   (2) strip_stderr_only_redirections() を新設し、stderr のみを破棄/追記するリダイレクト
#   （`2>TARGET`/`2>>TARGET`）を安全に読み飛ばして cat 等のファイルオペランド判定に混入
#   しないようにした（stdout/stdin 自体に触れるリダイレクト・`2>&1` は対象外のまま維持）。
#   head/tail の `-c` を含む複数セグメント構成等、対応が複雑になりすぎる／安全性を保証しきれない
#   と判断した拡張はオーナー承認のもと見送り、既知の残存ギャップとして
#   classify_operator_sequence_stage() のコメントに明記した（受け入れ基準5）。クラスC
#   （cut/awk/sed/tr 等）は引き続き Issue #220 として別起票済み・対象外。詳細は各関数の
#   コメント参照。
#
#   2026-07-13 設計転換（Issue #222・PR #219 3ラウンド連続の whack-a-mole を受けたオーナー承認
#   「B: fail-closedへの設計転換」・Claude 版と同一設計）：上記までの是正は全て「producer/
#   passthrough 追跡ロジックが安全なパイプ段だと静的に確定できない場合、追跡を諦めて ALLOW する」
#   という fail-open の初期値の上に、新しい未知のシェル構文（サブシェル→sequencing演算子→
#   stderrリダイレクト→fd複製/クローズ→…）が見つかるたびに個別の point-fix（列挙の拡張）を
#   重ねる構造だった。この構造そのものが whack-a-mole の根本原因（シェル構文の亜種は原理的に
#   列挙で塞ぎきれない）と判断し、初期値を反転した：**「パイプの中間段が、literal producer
#   から interpreter/git/gh までの間で安全な passthrough だと積極的に確定できない限り、そのまま
#   到達しうるとみなし deny する」**。
#
#   具体的には literal_producer_value_through_passthrough() が producer 遡及の途中で
#   classify_passthrough_stage() から「確定できない」（None, None）を受け取った場合、従来は
#   None を返して追跡を諦め ALLOW していたが、以後は `_UNVERIFIABLE_PRODUCER` という別センチネルを
#   返し、bare_interpreter_reexec_bodies()/xargs_reexec_bodies()/process_substitution_reexec_bodies()
#   の呼び出し元が「sink（interpreter や git/gh）は確定しているが、そこに至る内容を静的に安全と
#   確認できなかった」ことを検知して fail_closed フラグを立て、最終的に find_violation() が独立した
#   deny 理由として返す（既存の「git merge」等の具体的な違反メッセージとは別立てのメッセージに
#   した。役割非対称メッセージ（"is reserved for pr-reviewer" 等）は「もう一方のロールなら許可
#   される」という誤った含意を持つため、fail-closed の理由には使わない）。
#
#   唯一の例外（真に安全と証明できる場合のみ ALLOW 側に倒す）: 丸括弧・ブレースで囲まれていない
#   ステージが `&&`/`||`/`;`/改行 演算子を含む場合（`classify_passthrough_stage` が
#   `_DISCONNECTED_OPERATOR_SEQUENCE` を返す）。これはシェルの結合優先順位（`|` が `&&`/`||`/`;`
#   より強く結合する）により、その時点で実際には別々の独立したパイプラインに分かれていることが
#   構造的に証明できるケースであり、「確定できない」のではなく「確定的に無関係」なので
#   fail-closed の対象にしない（`echo x | cat && true | bash` 等・既存の安全側設計を維持）。
#
#   この設計転換により、これまで3ラウンドで個別に列挙して塞いできたバイパス（サブシェル括弧・
#   sequencing 演算子・stderr リダイレクト・fd 複製/クローズ構文の全て）は、個別の point-fix
#   ではなく「classify_passthrough_stage が確定できないものは全て deny」という単一の原理で
#   自動的に閉じる。既存の PASSTHROUGH_COMMANDS 列挙（UNCONDITIONAL/SINGLE_LINE 区分）は削除せず、
#   fail-closed の枠組みの中の「高速パス最適化」（安全と確定済みの代表的な cat/tee/sort/head/
#   tail/uniq を早期にパススルー確定させ、無用な過検知を避ける）として維持する（Issue #222
#   スコープに明記のとおり）。
#
#   over-deny の増加を許容する（Issue #222 決定事項）: 従来「ファイルオペランド付き cat/sort」
#   「uniq -c／head -n0 等の未対応フラグ」「grep/tr 等の未列挙フィルタ」「サブシェル内の
#   2個以上の passthrough セグメント」等は、内容が実際には無害だったため allow のまま許容して
#   いたが、これらは全て「安全と確定できない」に該当するため fail-closed で deny に転じる
#   （実装後の敵対的検証・over-deny 実害の洗い出しは本コミットの PR 説明を参照）。同時に
#   Issue #220（grep/cut/awk/sed 等の恒等変換フィルタ列挙方式の限界）は、個別コマンドの
#   恒等性を証明できない限り deny する本設計により根本的に解消される（列挙が不要になる）。
#
#   xargs -I{} のテンプレート代入は、producer 値が確定できない場合でも「代入先が git/gh の
#   サブコマンド位置、interpreter の -c/スクリプト位置、またはプレースホルダそのものが
#   コマンド全体」という危険な形をしている場合に限り fail-closed 対象とする
#   （xargs_template_is_dangerous_shape()）。`xargs -I{} wc -l {}` のような一般的な非危険形は
#   対象化しない（既存の一般的な xargs イディオムを壊さない・受け入れ基準4）。
#
#   プロセス置換 `<(CMD)`/`>(CMD)`（bash がその場でパイプ/名前付きパイプを生成し中のコマンドを
#   別プロセスとして実行して consumer に渡す構文）をインタプリタの位置引数として渡す形
#   （`bash <(echo 'git merge evil')`）は、実装時の敵対的自己検証で新規発見した重大バイパス
#   （既存の「位置引数があれば標準入力を読まないため対象外」という判定が `<(...)` を実在の
#   ファイルパスと誤って同一視していた）。process_substitution_reexec_bodies() で、CMD 自身を
#   1本のミニパイプラインとみなし literal_producer_value_through_passthrough を再利用して
#   対応した。また `|&`（stdout+stderr をまとめてパイプ）と `{ ... }`（ブレースグルーピング。
#   丸括弧サブシェルと同じ「接続を切らない」性質を持つがサブシェル以外のグルーピング構文として
#   Issue #218 では意図的にスコープ外だった）も、既存の split_top_level_pipes/
#   strip_matching_parens が非対応だったために classify_passthrough_stage の
#   _DISCONNECTED_OPERATOR_SEQUENCE 判定を誤って通過してしまう新規バイパスとして同じ実装時の
#   敵対的自己検証で発見し、split_top_level_pipes（`|&` の2文字消費・`{`/`}` の深さ追跡）と
#   strip_matching_parens（`{ ... }` も1グループとして剥がす）を拡張して是正した。
#
#   ヒアドキュメント／here-string のパイプ下流インタプリタ判定（heredoc_pipeline_has_downstream_
#   interpreter）は、この設計転換の対象に含めていない（本文は常に静的に既知であり
#   「確定できない producer」という問題がそもそも存在しないため）。ただし判定自体の頑健性は
#   split_top_level_pipes/unwrap_redundant_parens ベースに統一し、`cat <<EOF | (bash)` のような
#   丸括弧で consumer を包む構文（敵対的自己検証で新規発見・列挙不要の構造的対応）も検知できる
#   よう是正した。詳細は各関数のコメント参照（Claude/Codex 両版で同一設計）。
# 標準ライブラリのみで JSON をパースする（jq 非依存・AGENTS.md の "python3 標準ライブラリのみ" 方針に合わせる）。
# 実装注意: `python3 - <<EOF ... EOF` は heredoc がそのまま python の stdin になり、外側で
# パイプされた本来の stdin（フック入力 JSON）が読めなくなる。よって stdin を一旦ファイルに
# 落としてから python にファイル引数として渡す。
set -u

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

python3 - "$tmpfile" <<'PYEOF'
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone

SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|passwd|authorization|credential|key)", re.I)
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|\n()]|\$\(|`")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
WRAPPER_COMMANDS = {"rtk", "command", "builtin", "exec"}
GH_GLOBAL_OPTIONS_WITH_VALUE = {"--repo", "-R", "--hostname"}
GH_GLOBAL_OPTION_VALUE_PREFIXES = ("--repo=", "-R", "--hostname=")
GH_GLOBAL_FLAG_OPTIONS = {"--help", "-h", "--paginate", "--verbose", "--version", "--debug"}
# Codex がシェルコマンドの hook tool_name として使う canonical 名は "Bash"
# （codex-rs/core/src/tools/hook_names.rs HookToolName::bash()）。git/gh はこの Bash ツール経由で走る。
# 将来 canonical 名が変わっても取りこぼさないよう、代表的なシェル系エイリアスも許容集合に入れる。
# 空文字（tool_name 欠如）は検査不能側に倒して inspect する（fail-closed 寄り）。
SHELL_TOOL_NAMES = {"", "Bash", "shell", "local_shell", "unified_exec", "exec_command"}


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def redact(value):
    if isinstance(value, dict):
        return {
            key: ("<redacted>" if SENSITIVE_KEY_RE.search(str(key)) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def debug_payload(payload, decision, reason):
    path = os.environ.get("AGENT_COMMAND_GATE_DEBUG_PAYLOAD")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "payload": redact(payload),
                "decision": decision,
                "reason": reason,
            }, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


# 常時有効の最小トレース（Issue #192）：AGENT_COMMAND_GATE_DEBUG_PAYLOAD（オプトイン・フルペイロード・
# デフォルト無効）とは別に、"フックが実際に呼ばれたか" だけを常時1行追記で残す。command 本文や生 payload
# は含めない（機微情報を持たない設計）。既定パスは AGENT_COMMAND_GATE_TRACE_LOG で上書きでき、空文字を
# 設定すると無効化できる（テストや no-op 運用向け）。既定でオンにしたのは、オプトイン方式だと
# "trust 付与後に本当に発火したか" を確認したいまさにその時に、事前に環境変数を仕込み忘れて再現できない
# という Issue #192 の根本課題を再発させるため（1行判断根拠）。
TRACE_DEFAULT_PATH = os.path.expanduser("~/.codex/agent-command-gate-trace.log")
TRACE_MAX_BYTES = 1_000_000  # 超過したら1世代だけ .1 にローテートする（際限ない肥大化を防ぐ）。


def trace_event(agent_type, tool_name, decision):
    path = os.environ.get("AGENT_COMMAND_GATE_TRACE_LOG", TRACE_DEFAULT_PATH)
    if not path:
        return
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        try:
            if os.path.getsize(path) > TRACE_MAX_BYTES:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "agent_type": agent_type or None,
                "tool_name": tool_name or None,
                "decision": decision,
            }, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


try:
    with open(sys.argv[1]) as f:
        payload = json.load(f)
except Exception:
    deny("agent-command-gate: PreToolUse payload is not valid JSON; refusing because the Bash command cannot be inspected.")
    trace_event(None, None, "deny")
    sys.exit(0)

def first_string(*values):
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""

agent_type = first_string(
    payload.get("agent_type"),
    payload.get("subagent_type"),
    (payload.get("agent") or {}).get("type") if isinstance(payload.get("agent"), dict) else None,
)
tool_name = first_string(payload.get("tool_name"))
tool_input = payload.get("tool_input")
command = tool_input.get("command") if isinstance(tool_input, dict) else None


def strip_leading_wrappers(tokens):
    tokens = list(tokens)
    while tokens:
        while tokens and ASSIGNMENT_RE.match(tokens[0]):
            tokens.pop(0)
        if not tokens:
            break
        head = tokens[0]
        if head == "env":
            tokens.pop(0)
            while tokens and (tokens[0].startswith("-") or ASSIGNMENT_RE.match(tokens[0])):
                option = tokens.pop(0)
                if option in {"-u", "-S"} and tokens:
                    tokens.pop(0)
            continue
        if head in WRAPPER_COMMANDS:
            tokens.pop(0)
            continue
        break
    return tokens


def shell_words(segment):
    segment = segment.strip()
    if not segment:
        return []
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        tokens = segment.split()
    return [token.rstrip(")") for token in tokens if token.rstrip(")")]


def git_subcommand(tokens):
    configs = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token == "-c" and index + 1 < len(tokens):
            configs.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("-c") and len(token) > 2:
            configs.append(token[2:])
            index += 1
            continue
        if token in {"-C", "--git-dir", "--work-tree", "--namespace"} and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    subcommand = tokens[index] if index < len(tokens) else ""
    args = tokens[index + 1:] if index < len(tokens) else []
    return subcommand, args, configs


def gh_command(tokens):
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token in GH_GLOBAL_OPTIONS_WITH_VALUE and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith(GH_GLOBAL_OPTION_VALUE_PREFIXES) and token not in {"-R"}:
            index += 1
            continue
        if token in GH_GLOBAL_FLAG_OPTIONS:
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    return tokens[index:]


def is_allowed_merge_maintenance(args):
    return len(args) == 1 and args[0] in {"--abort", "--quit"}


def direct_violation(tokens, role):
    tokens = strip_leading_wrappers(tokens)
    if not tokens:
        return None
    if tokens[0] == "git":
        subcommand, args, configs = git_subcommand(tokens)
        if role in {"issue-implementer", "unknown"}:
            if subcommand == "merge" and not is_allowed_merge_maintenance(args):
                return "git merge"
            for config in configs:
                match = re.fullmatch(r"alias\.([A-Za-z0-9_.-]+)=merge", config)
                if match and subcommand == match.group(1):
                    return "git alias for merge"
        if role in {"pr-reviewer", "unknown"} and subcommand == "push":
            return "git push"
    if tokens[0] == "gh" and role in {"issue-implementer", "unknown"}:
        command_tokens = gh_command(tokens)
        if command_tokens[:2] == ["pr", "merge"]:
            return "gh pr merge"
    return None


def quoted_subcommands(command_text):
    patterns = [
        r"\beval\s+(['\"])(.*?)\1",
        r"\b(?:bash|sh|zsh|dash)\s+-c\s+(['\"])(.*?)\1",
        r"\b(?:python3?|perl|ruby|node)\s+-c\s+(['\"])(.*?)\1",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command_text, re.S):
            yield match.group(2)


def quoted_literals(command_text):
    for match in re.finditer(r"(['\"])(.*?)\1", command_text, re.S):
        yield match.group(2)


# ヒアドキュメント対応（Issue #189・Claude 版 .claude/hooks/agent-command-gate.sh と同一設計）:
# ヒアドキュメント本文（<<WORD / <<'WORD' / <<"WORD" ... WORD）はシェル上「直前のコマンドへの
# 入力データ」であり、トップレベルのコマンド列ではない。しかし SEGMENT_SPLIT_RE ベースの素朴な
# 分割は改行・丸括弧・バッククォートを無条件にコマンド境界とみなすため、ヒアドキュメント経由で
# 渡す PR 本文・コミットメッセージの散文（Markdown のインラインコード `git merge` 等）を独立した
# トップレベルコマンドと誤認し、over-deny していた（Issue #189 で実地に複数回誤検知された）。
# 対策: ヒアドキュメント本文を direct_violation のトップレベル走査から除外する。ただし
# `bash <<'EOF' ... EOF` のように本文が実際にインタプリタへのスクリプト入力として再実行される
# 場合は、除外した上で別途 depth+1 として本文の素のテキストを再帰走査し、既存の false negative
# 対策と同じ安全側バイアスを維持する。
# 適用は depth==0（エージェントが実際に発行したコマンド全体）のみに限定する。depth>0
# （quoted_subcommands が eval/bash -c/python -c の引数として抽出した文字列）は、その時点で
# 既に「再実行される」と判定済みのテキストなので、ヒアドキュメント除去はせず素の最大感度スキャンを
# 維持する（`bash -c "$(cat <<'EOF'\ngit merge evil\nEOF\n)"` のような二重の難読化を見逃さないため）。
HEREDOC_RE = re.compile(
    r"<<-?[ \t]*(?:'([A-Za-z_][A-Za-z0-9_]*)'|\"([A-Za-z_][A-Za-z0-9_]*)\"|([A-Za-z_][A-Za-z0-9_]*))"
)
# quoted_subcommands() が "-c" 経由の再実行として扱っているコマンド集合と揃える
# （bash/sh/zsh/dash と python3?/perl/ruby/node）。ヒアドキュメントを直接標準入力として
# 食わせるコマンド（`bash <<EOF` 等）も同じ意味で「本文が実行される」ため同じ集合を使う。
# `source`/`.`（bash 組み込みの同義コマンド。カレントシェルでスクリプトを読み込み実行する）も
# 同様に本文が実行されるため含める（2026-07-12 追加是正・Issue #189・PR #212 再レビュー指摘）。
HEREDOC_INTERPRETER_COMMANDS = {
    "bash", "sh", "zsh", "dash", "python", "python3", "perl", "ruby", "node", "source", ".",
}


def heredoc_command_word(command_text, marker_start):
    """`<<` の直前（同じ行内）にあるコマンド語を返す（先頭が '-' のフラグ語はスキップする）。
    見つからなければ空文字列を返す（= 非インタプリタ扱い・安全側でスキップのみに倒す）。"""
    line_start = command_text.rfind("\n", 0, marker_start) + 1
    prefix = command_text[line_start:marker_start]
    words = prefix.split()
    for word in reversed(words):
        if word.startswith("-"):
            continue
        return os.path.basename(word.rstrip("|;&"))
    return ""


def heredoc_pipeline_has_downstream_interpreter(line_after_marker):
    """ヒアドキュメントのマーカー以降・同じ行の末尾までのテキストを走査し、パイプ（`|`）で
    区切られた下流ステージの先頭コマンドがインタプリタかどうかを判定する（Issue #189 追加是正・
    PR #212 レビュー指摘・Claude 版と同一設計）。

    是正の経緯: heredoc_command_word() は `<<` の直前・同一行のコマンド語（例: `cat`）しか
    見ておらず、その stdout がパイプ下流のインタプリタへ渡る経路（`cat <<'EOF' | bash` /
    `cat <<EOF | bash`（非引用デリミタ）/ `cat <<-'EOF' | bash`（`<<-` ダッシュ版）/
    `cat <<'EOF' | tee /tmp/x | bash`（多段パイプ）等）を捕捉できておらず、本来 deny すべきものが
    軒並み allow される重大バイパスがあった。
    設計方針: 「本文を除外する前に、そのヒアドキュメントが最終的にインタプリタへ渡る経路
    （直接 `bash <<EOF` でも、パイプ経由でも）が無いことを確認できた場合のみ除外する」という、
    より保守的な（除外条件を厳しくする）方向に倒す。マーカー行内の各パイプステージについて
    strip_leading_wrappers で env/rtk 等のラッパーとフラグ・代入を剥がした先頭コマンド語を見て、
    どこかにインタプリタがあれば「最終的に再実行される」と判定する。

    2026-07-13 頑健化（Issue #222 敵対的自己検証で新規発見・Claude 版と同一設計）: 素朴な
    `line_after_marker.split("|")` は丸括弧で consumer を包む構文（`cat <<EOF | (bash)`）を
    認識できず、`(bash)` という1トークンが HEREDOC_INTERPRETER_COMMANDS と一致せず見逃していた
    （実行して確認済み・実際にペイロードが走る）。split_top_level_pipes/unwrap_redundant_parens
    （丸括弧・引用符を構造的に扱う既存のパイプ分割器）に置き換えることで、個別列挙ではなく
    構造的にこの種の亜種を塞ぐ。"""
    for stage in split_top_level_pipes(line_after_marker)[1:]:
        stage = unwrap_redundant_parens(first_operator_segment(stage))
        tokens = strip_leading_wrappers(stage.split())
        if not tokens:
            continue
        name = os.path.basename(tokens[0].rstrip("|;&"))
        if name in HEREDOC_INTERPRETER_COMMANDS:
            return True
    return False


def extract_heredocs(command_text):
    """ヒアドキュメント本文をトップレベル走査用テキストから取り除き、
    (取り除いた後のテキスト, インタプリタへ直接渡される本文のリスト) を返す。
    本文は常に direct_violation の素朴な分割対象から除外する一方、本文がインタプリタコマンドへの
    標準入力として渡される場合（`bash <<'EOF' ... EOF` の直接形、または `cat <<'EOF' | bash` の
    ようにパイプ下流でインタプリタに渡る形のいずれか。Issue #189 追加是正）は、その本文を
    呼び出し側（find_violation）で depth+1 として再帰走査させる。終端デリミタが見つからない
    不正な形式のヒアドキュメントはテキストを変更せず残す（検査不能側＝安全側に倒す）。"""
    stripped = []
    reexec_bodies = []
    pos = 0
    for m in HEREDOC_RE.finditer(command_text):
        if m.start() < pos:
            continue  # 既に取り除いた本文の内側にある偽陽性マッチ
        word = m.group(1) or m.group(2) or m.group(3)
        line_end = command_text.find("\n", m.end())
        if line_end == -1:
            continue  # 本文を持たない（改行がない）= 不正形式、そのまま残す
        body_start = line_end + 1
        delim_re = re.compile(r"(?m)^[ \t]*" + re.escape(word) + r"[ \t]*$")
        dm = delim_re.search(command_text, body_start)
        if not dm:
            continue  # 終端デリミタが見つからない = 不正形式、そのまま残す
        stripped.append(command_text[pos:body_start])
        reaches_interpreter = (
            heredoc_command_word(command_text, m.start()) in HEREDOC_INTERPRETER_COMMANDS
            or heredoc_pipeline_has_downstream_interpreter(command_text[m.end():line_end])
        )
        if reaches_interpreter:
            reexec_bodies.append(command_text[body_start:dm.start()])
        pos = dm.start()
    stripped.append(command_text[pos:])
    return "".join(stripped), reexec_bodies


# here-string 対応（Issue #213 受け入れ基準1・Claude 版と同一設計）: `<<<`（here-string）は
# `<<`（ヒアドキュメント）と記法が似ているが意味論が異なる。`<<WORD ... WORD` は終端デリミタまでの
# 複数行を読むのに対し、`<<<VALUE` は同じ行の一語（クォート文字列 or 空白なしの単語）をそのまま
# コマンドの標準入力として渡す。HEREDOC_RE は `<<` の直後に識別子（クォート付き/なし）を要求するため、
# 3文字目が `<` である `<<<` にはそもそもマッチせず、`bash <<< 'git merge evil'` が検知漏れになって
# いた（実証済み）。本関数は `<<<` の後続値を抽出し、直前のコマンド語（またはパイプ下流）が
# インタプリタの場合のみ reexec 対象として返す（heredoc_command_word/
# heredoc_pipeline_has_downstream_interpreter を再利用）。ヒアドキュメントと異なり単一行の値であり、
# 除去しなくても direct_violation の素朴な走査に新規の誤検知は生じないため、scan_text からの除去
# （ストリップ）は行わない。
HERESTRING_RE = re.compile(r"<<<[ \t]*(?:(['\"])(.*?)\1|(\S+))", re.S)


def herestring_reexec_bodies(command_text):
    bodies = []
    for m in HERESTRING_RE.finditer(command_text):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        if not value:
            continue
        line_end = command_text.find("\n", m.end())
        rest_of_line = command_text[m.end():line_end] if line_end != -1 else command_text[m.end():]
        reaches_interpreter = (
            heredoc_command_word(command_text, m.start()) in HEREDOC_INTERPRETER_COMMANDS
            or heredoc_pipeline_has_downstream_interpreter(rest_of_line)
        )
        if reaches_interpreter:
            bodies.append(value)
    return bodies


# `|`（`||` を除く）でトップレベルのパイプ境界を分割する。SEGMENT_SPLIT_RE 同様、クォート/
# ヒアドキュメント境界を認識しない素朴な分割であり、既存の制約の延長線上にある（安全側＝
# 誤検知が起きても deny 方向にしか倒れない設計であり、完全な網羅は目指さない・受け入れ基準5）。
PIPE_ONLY_RE = re.compile(r"(?<!\|)\|(?!\|)")


# サブシェル括弧グルーピング対応（Issue #218 ギャップ1・Claude 版と同一設計）: PIPE_ONLY_RE.split()
# はトップレベルの `|` を素朴に全分割するため、`echo x | (cat | cat) | bash` のような丸括弧
# サブシェルを含むパイプラインでは、サブシェル内部の `|` まで分割対象にしてしまい `(cat` / `cat)`
# という不正な字句が生まれ、classify_passthrough_stage 判定がそこで偽になって
# producer→パススルー→consumer の追跡が途切れる（実行して確認済み：
# `echo 'git merge evil' | (cat | cat) | bash` が allow されていた）。split_top_level_pipes() は
# 丸括弧の深さを数えながら分割することで、サブシェル内部の `|` を分割対象から除外する
# （波括弧 `{ ... ; }` 等サブシェル以外のグルーピング構文への一般化は対象外＝スコープ外・
# Issue #218 受け入れ基準）。
def split_top_level_pipes(text):
    """PIPE_ONLY_RE と同じ「`|`（`||` を除く）」の意味論で分割するが、丸括弧 `( ... )` の
    内側にある `|` はトップレベルとみなさず分割しない。括弧の対応が取れないまま文字列が終端した
    場合（閉じ括弧が来ない）、それ以降は深さが0に戻らないため以降の `|` も分割対象外になる
    （安全側：新規の誤検知にはならず、単に一部のステージ境界を見失うだけに留まる）。

    2026-07-13 是正（Issue #222 敵対的自己検証で新規発見・Claude 版と同一設計）: `|&`（bash の
    `cmd1 |& cmd2` ＝ `cmd1 2>&1 | cmd2` の省略記法。stdout と stderr をまとめて次段へパイプ
    する）が未対応だった。旧実装は `|` の直後の文字が `&` の場合を全く考慮しておらず、`|` 自体は
    素朴にパイプ境界として分割する一方、直後の `&` はどちらのステージにも属さず次ステージの
    バッファの先頭に紛れ込み（例: `cat |& bash` → ["cat ", "& bash"]）、`& bash` という不正な
    字句になって consumer 側の interpreter 認識が壊れ、結果的に producer→passthrough→consumer
    の追跡が打ち切られて fail-closed 判定（_UNVERIFIABLE_PRODUCER）にすら至らずそのまま ALLOW
    してしまっていた（実行して確認済み・実際にペイロードが走る重大バイパス）。`|` の直後が `&`
    の場合は両方の文字を消費してパイプ境界とすることで是正する。

    追加是正（同時発見・Claude 版と同一設計）: 丸括弧 `(` `)` の深さしか追跡していなかったため、
    ブレースグループ `{ ... }` の内側にある `|` をトップレベルとして誤って分割していた。`{`/`}`
    も同じ深さカウンタで追跡する（strip_matching_parens が `{ ... }` も1グループとして剥がせる
    ようになったことと対称化）。"""
    stages = []
    depth = 0
    current = []
    length = len(text)
    i = 0
    while i < length:
        ch = text[i]
        if ch == "(" or ch == "{":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch == ")" or ch == "}":
            if depth > 0:
                depth -= 1
            current.append(ch)
            i += 1
            continue
        if ch == "|" and depth == 0:
            prev_ch = text[i - 1] if i > 0 else ""
            next_ch = text[i + 1] if i + 1 < length else ""
            if prev_ch == "|":
                current.append(ch)  # 直前が `|` の `||` は PIPE_ONLY_RE 同様パイプ境界としない
                i += 1
                continue
            if next_ch == "|":
                current.append(ch)  # 直後が `|` の `||` も同様（この文字だけ積んで次周で判定）
                i += 1
                continue
            stages.append("".join(current))
            current = []
            if next_ch == "&":
                i += 2  # `|&` は `|` と `&` の2文字をまとめてパイプ境界として消費する
            else:
                i += 1
            continue
        current.append(ch)
        i += 1
    stages.append("".join(current))
    return stages


_GROUP_OPENERS = "({"
_GROUP_CLOSERS = {"(": ")", "{": "}"}


def strip_matching_parens(stripped):
    """stripped 全体がちょうど1組の対応する丸括弧 `( ... )` またはブレースグループ `{ ... }`
    （bash のコマンドグルーピング構文。サブシェルと違い現在のシェルで実行されるが、中身の
    複数コマンドの標準出力が1本に連結されて外側へ渡る点はサブシェルと同じ「接続を切らない」
    性質を持つ）で囲まれている場合、内側のテキストを返す（例: "(cat | cat)" → "cat | cat"、
    "{ cat; }" → " cat; "）。外側の括弧が末尾より前で閉じてしまう場合（例: "(cat) (cat)" の
    ように2つの独立したグループが並んでいる場合）、開き括弧と閉じ括弧の種類が対応しない場合
    （例: "(foo}"）、先頭/末尾が括弧でない場合、括弧の対応が取れない場合は None を返す
    （安全側：全体を1つのグループとして扱えると確信できる場合のみ剥がす）。

    2026-07-13 拡張（Issue #222 敵対的自己検証で新規発見・Claude 版と同一設計）: ブレースグループ
    `{ ... }` は Issue #218 時点では意図的にスコープ外（丸括弧のみ対応）だったが、丸括弧非対応の
    ままだと `{ cmd; }` の中の `;` が「サブシェル外側の &&/;/|| は別パイプラインに分かれる」と
    いう無関係な判定（classify_passthrough_stage の _DISCONNECTED_OPERATOR_SEQUENCE）に誤って
    合致し、実際には接続されている producer→{ cmd; }→consumer の経路を「確定的に無関係」と
    誤認して見逃す新規バイパスがあった（`echo 'git merge evil' | { cat; } | bash` を実 bash で
    実行しペイロードが走ることを確認済み）。ブレースグループも classify_subshell_body に
    委譲できるよう本関数で認識する。"""
    if len(stripped) < 2 or stripped[0] not in _GROUP_OPENERS:
        return None
    opener = stripped[0]
    closer = _GROUP_CLOSERS[opener]
    if stripped[-1] != closer:
        return None
    stack = []
    for idx, ch in enumerate(stripped):
        if ch in _GROUP_OPENERS:
            stack.append(ch)
        elif ch in (")", "}"):
            if not stack:
                return None  # 対応する開き括弧がない
            top = stack.pop()
            if _GROUP_CLOSERS[top] != ch:
                return None  # 開き括弧の種類と閉じ括弧の種類が対応しない（例: "(foo}"）
            if not stack and idx != len(stripped) - 1:
                return None  # 最外のグループが末尾より前で閉じている = 全体を囲んでいない
    if stack:
        return None  # 閉じきれていない（不正形式）
    return stripped[1:-1]


# サブシェルによる consumer/パイプライン全体のラップ対応（PR #219 opus レビューで発見・クラスA・
# Claude 版と同一設計）: `echo 'git merge evil' | (bash)`（consumer 位置を丸括弧で包む）や
# `(echo 'git merge evil' | bash)`（パイプライン全体を丸括弧で包む）は、いずれも実 bash で
# 実際にペイロードが実行されるにもかかわらず、split_top_level_pipes だけでは検知できない
# （前者は consumer 側トークンが `(bash)` という1語になり HEREDOC_INTERPRETER_COMMANDS と
# 一致しない。後者はパイプ全体が depth>=1 の内側に収まり、そもそもトップレベルの `|` が
# 見つからず stages が1要素のまま split されない）。実行して確認済み。
def unwrap_redundant_parens(text):
    """text をトリムした結果がちょうど1組の対応する丸括弧で全体を囲んでいる場合、内側を返し、
    それがさらに丸括弧で囲まれていれば繰り返し剥がす（`((cmd))` 等の多重サブシェルにも対応）。
    剥がせなくなった時点のテキスト（トリム済み）を返す。"""
    stripped = text.strip()
    while True:
        inner = strip_matching_parens(stripped)
        if inner is None:
            return stripped
        stripped = inner.strip()


def top_level_pipeline_stages(command_text):
    """command_text 全体のトップレベルのパイプ段リストを返す。split_top_level_pipes が1要素
    しか返さず、かつその唯一の要素がちょうど1組の丸括弧で command_text 全体を囲んでいるだけ
    （＝パイプライン全体が丸ごとサブシェルに包まれているだけで、実質的な段構成は中身と同じ）の
    場合は、中身を展開してから改めて分割する（再帰的に多重サブシェルにも対応）。"""
    stages = split_top_level_pipes(command_text)
    if len(stages) == 1:
        unwrapped = unwrap_redundant_parens(stages[0])
        if unwrapped != stages[0].strip():
            return top_level_pipeline_stages(unwrapped)
    return stages


# 敵対的自己検証で発見（Issue #213・実装中の追加是正・Claude 版と同一設計）: `true ||
# echo 'git merge evil' | bash` や `echo 'git merge evil' | bash && true` のように、パイプ境界の
# 前後に `&&`/`||`/`;`/改行で別のサブコマンドが連結されていると、ステージ全体をそのまま shlex
# 解析するだけでは producer 側の先頭トークンが `true`（echo ではない）になったり、consumer 側の
# 残余引数に `&&`/`true` 等の非フラグ語が混入して「位置引数あり」判定に誤って倒れたりして検知漏れに
# なる。シェルの優先順位は `|` が `&&`/`||`/`;` より強く結合するため、producer に実際に効いて
# くるのはその中の最後のサブコマンド、consumer に効いてくるのは最初のサブコマンドのみ。
STAGE_OPERATOR_SPLIT_RE = re.compile(r"&&|\|\||;|\n")


def last_operator_segment(text):
    parts = STAGE_OPERATOR_SPLIT_RE.split(text)
    return parts[-1] if parts else text


def first_operator_segment(text):
    parts = STAGE_OPERATOR_SPLIT_RE.split(text)
    return parts[0] if parts else text


def literal_producer_value(stage_text):
    """パイプの直前ステージのうち実際にパイプへ出力を渡す最後のサブコマンド
    （last_operator_segment）が echo/printf のみで構成され、渡す引数が全てリテラル
    （フラグを含まない単語・クォート文字列）である場合に、標準出力へ書き出される文字列を返す。
    変数展開・コマンド置換・非対応コマンド（`find` 等）が混在する場合は None を返す
    （静的に確定できないため対象外＝新規の過検知を出さない安全側の設計）。"""
    stripped = last_operator_segment(stage_text).strip()
    if "$" in stripped or "`" in stripped:
        return None
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return None
    tokens = strip_leading_wrappers(tokens)
    if len(tokens) < 2:
        return None
    head, args = tokens[0], tokens[1:]
    if any(arg.startswith("-") for arg in args):
        return None
    if head == "echo":
        return " ".join(args)
    if head == "printf":
        if len(args) == 1:
            return args[0]
        if len(args) == 2 and args[0] in {"%s", "%s\\n"}:
            return args[1]
        return None
    return None


# パススルー経由の producer 遡及対応（Issue #215・Claude 版と同一設計）: bare_interpreter_reexec_bodies/
# xargs_reexec_bodies は下で literal_producer_value を直前ステージ（stages[i-1]）のみに適用して
# いたため、リテラル producer とインタプリタの間に `cat`/`tee` 等のパススルーを1段挟むと
# （`echo 'git merge evil' | cat | bash` 等）検知が外れていた（実行して確認済み）。本節は
# 「直前ステージが純粋なパススルーなら、さらにその前段へ literal_producer_value の確定を
# 遡って試みる」設計で、既存の heredoc_pipeline_has_downstream_interpreter（多段パススルー対応済み）
# と対称化する。過度なパススルーコマンドの網羅は目指さない（受け入れ基準6・代表例の cat/tee に限定）。
UNCONDITIONAL_PASSTHROUGH_COMMANDS = {"cat", "tee"}

# 単一行保存フィルタの追加対応（Issue #218 ギャップ2・Claude 版と同一設計）: cat/tee は入力の
# 行数や内容に関わらず常に恒等変換（入力どおりに出力する）だが、sort/head/tail/uniq は
# 「複数行入力」や「一部のフラグ」では恒等変換にならない（例: sort は複数行なら並べ替える、
# `uniq -c` は件数を先頭に付与する、`head -n0` は0行しか出力しない）。一方でこのフックが遡及に
# 使う literal_producer_value は echo/printf の静的リテラル引数から確定した値であり、通常は
# 改行を含まない単一行になる。「単一行入力であれば恒等になることが構造的に保証できる引数の
# 組み合わせ」に限り UNCONDITIONAL（cat/tee・無条件）とは区別して SINGLE_LINE（producer 値に
# 改行が含まれないことを別途確認した場合のみ有効）という2区分でパススルーを扱う。`grep`/`tr` は
# 恒等変換にならない（grep はパターン一致が前提、tr は文字変換が前提）ため対象外（Issue #218
# 受け入れ基準3・スコープ外として明記）。
SINGLE_LINE_PASSTHROUGH_COMMANDS = {"sort", "head", "tail", "uniq"}

_POSITIVE_INT_RE = re.compile(r"^\d+$")

# PR #219 opus レビュー・クラスB追随是正（Claude 版と同一設計）: sort -r/-u・uniq -u・head/tail
# -c（バイト数指定）・head -n +1 は、実 bash で実行確認したところいずれも恒等変換だったが、
# 当初の実装（フラグなしのみ許可）では未対応で検知漏れになっていた。以下、各コマンドごとに
# 検証済みの安全な引数の組み合わせのみを追加する（無条件の全フラグ許可はしない）。
#
# sort -r/--reverse・-u/--unique（単独・バンドル `-ru`/`-ur` を含む）は、1行しかない入力では
# 並べ替え・重複排除ともに対象が1個しかなく効果がないため恒等（実 bash で確認済み）。
# `-c`/`-C`（check モード。並べ替え結果を標準出力に書かない）・`-o FILE`（ファイル出力）・
# `-m`（複数ソート済み入力のマージ前提）等、恒等が崩れる／保証できないフラグは許可しない。
SORT_SAFE_FLAG_CHARS = {"r", "u"}
SORT_SAFE_LONG_FLAGS = {"--reverse", "--unique"}
# uniq -u/--unique（隣接する重複を除いた行のみ出力）は、1行しかない入力では比較対象がなく
# 常に「重複していない行」として出力されるため恒等（実 bash で確認済み）。`-d`/`--repeated`
# （重複行のみ出力。1行入力では出力が空になり恒等でない）・`-c`（件数付与）は許可しない。
UNIQ_SAFE_FLAG_CHARS = {"u"}
UNIQ_SAFE_LONG_FLAGS = {"--unique"}


def _is_safe_flag_only_args(args, safe_chars, safe_long_flags):
    """args の全トークンが「安全な短縮フラグ文字だけで構成された `-` 始まりのバンドル」
    （例: safe_chars={"r","u"} なら `-r`/`-u`/`-ru`/`-ur`）または「安全なロングフラグ」の
    いずれかである場合のみ True を返す。ファイルオペランド・その他の非安全フラグが1つでも
    混じっていれば False（安全側）。"""
    for arg in args:
        if arg in safe_long_flags:
            continue
        if arg.startswith("--"):
            return False
        if arg.startswith("-") and len(arg) > 1 and all(ch in safe_chars for ch in arg[1:]):
            continue
        return False
    return True


def _head_tail_count_spec(args):
    """head/tail の引数（先頭コマンド語を除いた残り）を解析し、`-n`/`-c`（または `--lines=`/
    `--bytes=`）1個だけで構成される場合に ("lines" | "bytes", カウント文字列) を返す。
    複数フラグの混在・カウント指定なしなど、静的に安全性を判定できない形は None を返す。"""
    kind = None
    count_text = None
    if len(args) == 1:
        token = args[0]
        if token.startswith("-n") and token != "-n":
            kind, count_text = "lines", token[2:]
        elif token.startswith("-c") and token != "-c":
            kind, count_text = "bytes", token[2:]
        elif token.startswith("--lines="):
            kind, count_text = "lines", token[len("--lines="):]
        elif token.startswith("--bytes="):
            kind, count_text = "bytes", token[len("--bytes="):]
        elif token.startswith("-") and len(token) > 1 and token[1:].isdigit():
            kind, count_text = "lines", token[1:]  # head -5 / tail -5 の旧記法
    elif len(args) == 2 and args[0] in {"-n", "--lines"}:
        kind, count_text = "lines", args[1]
    elif len(args) == 2 and args[0] in {"-c", "--bytes"}:
        kind, count_text = "bytes", args[1]
    if kind is None or count_text is None:
        return None
    return kind, count_text


def is_single_line_identity_args(name, args):
    """SINGLE_LINE_PASSTHROUGH_COMMANDS の各コマンドについて、与えられた引数の組み合わせが
    「単一行入力に対して」恒等変換になることを保証できるかどうかを判定する。

    戻り値は (is_safe, byte_cap) のタプル。is_safe=False の場合 byte_cap は常に None。
    is_safe=True かつ byte_cap=None は「単一行入力であれば無条件に恒等」（行数指定・フラグなし
    等）。is_safe=True かつ byte_cap=N（正の整数）は「単一行入力であり、かつ最終的に確定する
    producer 値の UTF-8 バイト長が N 以下の場合に限り恒等」（head/tail の `-c`/`--bytes`
    バイト数指定・PR #219 opus レビュー クラスB追随。`head -c5` で "git merge evil" が
    "git m" に切り詰められ恒等でなくなることを実 bash で確認済みのため、無条件許可はしない）。

    - sort: 引数なし、または SORT_SAFE_FLAG_CHARS/SORT_SAFE_LONG_FLAGS のみで構成される場合。
    - uniq: 引数なし、または UNIQ_SAFE_FLAG_CHARS/UNIQ_SAFE_LONG_FLAGS のみで構成される場合。
    - head/tail: 引数なし、正の行数指定（`-n`/`--lines`。head は `-n +N` の `+` も許容——GNU
      head の `-n +N` は tail と異なり単に "先頭 N 行"（`-n N` と同義）であることを実 bash で
      確認済み。tail の `-n +N` は「N 行目から末尾まで」で意味が異なるため対象外）、または
      正のバイト数指定（`-c`/`--bytes`。byte_cap 付きで返す）。
    - それ以外の組み合わせ（ファイルオペランド混在・非対応フラグ等）は (False, None)。
    """
    if not args:
        return True, None
    if name == "sort":
        return _is_safe_flag_only_args(args, SORT_SAFE_FLAG_CHARS, SORT_SAFE_LONG_FLAGS), None
    if name == "uniq":
        return _is_safe_flag_only_args(args, UNIQ_SAFE_FLAG_CHARS, UNIQ_SAFE_LONG_FLAGS), None
    if name in {"head", "tail"}:
        spec = _head_tail_count_spec(args)
        if spec is None:
            return False, None
        kind, count_text = spec
        if kind == "lines":
            if count_text.startswith("+"):
                if name != "head":
                    return False, None  # tail の `-n +N` は開始行指定で意味が異なるため対象外
                count_text = count_text[1:]
            if not _POSITIVE_INT_RE.match(count_text) or int(count_text) < 1:
                return False, None
            return True, None
        if kind == "bytes":
            if not _POSITIVE_INT_RE.match(count_text):
                return False, None
            n = int(count_text)
            if n < 1:
                return False, None
            return True, n
        return False, None
    return False, None


# サブシェル内 sequencing 演算子対応（PR #219 opus レビューで発見・クラスA・Claude 版と同一設計）:
# `(cat && true)`/`(true; cat)` は、実 bash では実際に恒等変換になる（cat が stdin を読み切って
# 書き出した後、true が続けて走っても標準出力には何も追加されない／true が先に走っても stdin を
# 消費せず何も出力しないため後続の cat がそのまま元の stdin を書き出す。いずれも実 bash で
# 確認済み）にもかかわらず、当初の実装は STAGE_OPERATOR_SPLIT_RE（&&/||/;/改行）を含む時点で
# 無条件に非パススルー扱いにしていたため検知漏れだった。
#
# ただし、この「演算子を挟んでも恒等になりうる」という性質は、あくまで丸括弧で囲まれた
# **サブシェルの中身**でのみ成り立つ（1つの実行コンテキストで標準出力が連結されるため）。
# 丸括弧に包まれていない、トップレベルのパイプ段テキストに現れる `&&`/`;` は、シェルの結合
# 優先順位が `|` > `&&`/`||`/`;` であるため実際には別々のパイプラインに分かれてしまう
# （`a | cat && true | b` は `(a | cat) && (true | b)` で cat の出力は b に渡らない・既存の
# 安全側の理由づけ）。この区別を保つため、classify_passthrough_stage（トップレベル段専用）と
# classify_subshell_body（丸括弧の中身専用）を分離し、sequencing 演算子の処理は後者からのみ
# 呼び出す classify_operator_sequence_stage に閉じ込める。
NOOP_STDOUT_FREE_COMMANDS = {"true", ":", "false"}

# stderr のみのリダイレクト対応（PR #219 opus 再レビューで発見・実 bash で実行確認済み・
# Claude 版と同一設計）: shlex は shell のリダイレクト構文を理解せず、`cat 2>/dev/null` の
# "2>/dev/null" を単なる1トークン（`cat 2> /dev/null` なら "2>" と "/dev/null" の2トークン）と
# してそのまま返すため、cat のファイルオペランドチェックや sort/uniq/head/tail の引数安全性
# チェックが、実際には stdin→stdout の恒等性を一切壊さない stderr 単独のリダイレクトを
# 「非フラグの位置引数（＝ファイルオペランドあり）」と誤判定して拒否していた。
# `(cat 2>/dev/null)`・パイプ内の `cat | cat 2>/dev/null`・サブシェルすら介さないトップレベル段
# `cat 2>/dev/null` のいずれも実行して allow される（本来 deny すべきバイパス）ことを確認済み。
#
# 安全に取り除けるのは「stderr を破棄/追記するだけ」（`2>TARGET`/`2>>TARGET`）に限る。
# `2>&1`（stderr を stdout に合流）・`>`/`>>`/`1>`/`&>`（stdout 自体の向け先変更）・
# `<`/`<<`/`<<<`（標準入力の向け先変更）はこの関数では除去しない。
#
# **重要な訂正（PR #219 さらなる再レビューで指摘・fail-open の再発・Claude 版と同一設計）**:
# 以前このコメントは「除去しない＝以降の判定でそのまま非フラグの位置引数として扱われ、
# 従来どおり拒否される（安全側）」と記述していたが、これは「拒否される」の主語を取り違えた
# 誤りだった。実際に「拒否される」のは classify_simple_command_stage 内の passthrough
# 認識判定（(None, None) を返す）に過ぎず、PreToolUse の最終判定が deny になるという意味
# ではない。(None, None) が返ると literal_producer_value_through_passthrough の遡及チェーン
# が打ち切られ reexec 対象に載らなくなる＝**ALLOW（見逃し）** になる（このPRで
# classify_operator_sequence_stage について訂正したのと全く同じ fail-open 構造）。実際に
# `(cat 2>&1)`／`(cat 2>/dev/null 2>&1)` は実 bash で恒等変換になり（cat が正常終了する限り
# stderr には何も書き込まれないため、2>&1 で合流させても stdout の内容は変わらない）、
# 実行して allow される（本来 deny すべき）ことを確認済み＝**既知の未対応の残存ギャップ
# （fail-open のまま）** であり、「安全」ではない。
#
# この fd 複製・クローズ構文（`2>&1`・`>&2`・`{fd}>&-` 等の派生を含む）は、個別の
# point-fix を重ねるたびに新しい亜種が見つかる展開になっており（本PRだけで既に複数
# ラウンド発生）、いたちごっこである。オーナー判断により、本PRではこれ以上の point-fix
# は追わず、fail-closed への構造転換（認識できない構文は安全側で拒否するアローリスト方式へ
# 転換する）を Issue #222 として別途起票し、そちらで根本解消する方針とした。本関数
# （strip_stderr_only_redirections）が `2>&1` 等を対象外のままにしているのは意図的な
# スコープ限定であり、その残存ギャップは Issue #222 で解消される前提で維持している。
_STDERR_DISCARD_TOKEN_RE = re.compile(r"^2>{1,2}(?!&)")


def strip_stderr_only_redirections(tokens):
    """tokens（コマンド名を除いた残り引数）から stderr のみを破棄/追記するリダイレクト
    （結合形 `2>TARGET`/`2>>TARGET` の1トークン、または分離形 `2>`/`2>>` + 次トークンの2トークン）
    を取り除いた残りのトークン列を返す。"""
    result = []
    i = 0
    n = len(tokens)
    while i < n:
        token = tokens[i]
        if token in ("2>", "2>>"):
            if i + 1 < n:
                i += 2
                continue
            result.append(token)  # リダイレクト先を伴わない不正形式は素通しし以降の判定に委ねる
            i += 1
            continue
        if _STDERR_DISCARD_TOKEN_RE.match(token):
            i += 1
            continue
        result.append(token)
        i += 1
    return result


def classify_simple_command_stage(stripped):
    """stripped（パイプ/丸括弧/sequencing 演算子を含まない単一のコマンドテキスト）を解析し、
    ("unconditional" | "single_line", byte_cap) または (None, None) を返す（末端の判定ロジック。
    従来 classify_passthrough_stage 内にあった単純コマンド解析部分を独立させたもの）。
    引数は strip_stderr_only_redirections で stderr のみのリダイレクトを取り除いた後に判定する
    （PR #219 opus 再レビュー対応）。"""
    if "$" in stripped or "`" in stripped:
        return None, None
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return None, None
    tokens = strip_leading_wrappers(tokens)
    if not tokens:
        return None, None
    name = os.path.basename(tokens[0])
    args = strip_stderr_only_redirections(tokens[1:])
    if name in UNCONDITIONAL_PASSTHROUGH_COMMANDS:
        if name == "cat":
            for arg in args:
                if arg == "-" or arg.startswith("-"):
                    continue
                return None, None  # 非フラグのファイルオペランドがある = 標準入力を読まない
        return "unconditional", None
    if name in SINGLE_LINE_PASSTHROUGH_COMMANDS:
        is_safe, byte_cap = is_single_line_identity_args(name, args)
        if not is_safe:
            return None, None
        return "single_line", byte_cap
    return None, None


def classify_operator_sequence_stage(stripped):
    """stripped が `&&`/`||`/`;`/改行で連結された1個以上のサブコマンド列で構成される場合に、
    サブシェル全体を1段のパススルーとして扱えるかどうかを判定し、(kind, byte_cap) または
    (None, None) を返す。

    **(None, None) を返すことは「安全」ではない（PR #219 opus 再レビューで指摘・重要な訂正）**:
    ここで None を返すと呼び出し元 literal_producer_value_through_passthrough の遡及チェーンが
    そこで打ち切られ、そのパイプライン全体が「静的に確定できないパススルー」として扱われて
    reexec 対象に載らなくなる＝**ALLOW（見逃し）** になる。以前のコメントは「見逃し方向には
    ならない」と誤って記述していたが、実際にはこの関数が実際には恒等変換であるパターンを
    未対応のまま None を返すたびに fail-open（バイパス見逃し）が起こり得る。実際に
    `(cat && cat)`/`(cat; cat)`（真の passthrough セグメントが2個以上）や
    `(cat 2>/dev/null)`（stderr リダイレクト付き passthrough。こちらは
    strip_stderr_only_redirections で別途対応）が実 bash で allow されるバイパスとして
    見つかった。None は「恒等性を静的に確認できなかった」という**未対応の残存ギャップ**
    （受け入れ基準5・完全網羅は目指さない）を意味するのであって、「見逃しが起きない」ことを
    意味しない。

    対応済みの範囲: 1個以上のセグメントが classify_subshell_body で識別可能なパススルーで、
    残り全てが標準出力に何も書かないことが既知のコマンド（NOOP_STDOUT_FREE_COMMANDS＝
    true/:/false、引数なし。stderr リダイレクト付きの `true 2>/dev/null` 等も同様に無害として
    扱う）である場合、パススルーが1個だけなら判定結果をそのまま返す。パススルーが2個以上
    連なる場合（`(cat && cat)`/`(cat; cat)` 等）は、**全セグメントが "unconditional"
    （cat/tee・byte_cap なし）の場合に限り**まとめて "unconditional" として扱う。cat/tee は
    必ず標準入力を最後まで読み切ってから書き出すため、複数個連なっても「1個目が全部読み切り、
    2個目以降は EOF で何も出力しない」ことが read() のバッファリング実装に関わらず保証できる
    （実 bash で確認済み）。一方 sort/uniq/head/tail（"single_line" 種別）、特に head/tail の
    `-c`（バイト数指定）は「指定バイト数だけ読んで残りが未読のまま後続セグメントに漏れ出す」
    可能性を静的に排除しきれないため、複数セグメント構成での組み合わせは対象外のまま維持する
    （安全性を保証しきれない組み合わせを拡張しないという限定であり、これも受け入れ基準5の
    残存ギャップとして許容する）。

    既知の未対応の残存ギャップ（このラウンドでは対応しない・fail-open のまま）:
    - `false && cat` のように、真に決定的な短絡評価（false は必ず失敗する）によって
      passthrough セグメントが実際には一度も実行されない構成は、この関数の短絡評価
      シミュレーションでは検出できない。ただしこの方向の誤りは「実際には空出力になるのに
      恒等変換だと誤認する」（過検知＝deny 方向）であり、見逃し（allow 方向）の新規リスクには
      ならない。
    - head/tail の `-c` を含む複数セグメント構成、3種類以上のコマンドが混在する構成等は
      未対応のまま（対応が複雑になりすぎる／安全性を保証しきれないと判断したため、無理に
      実装しない。オーナー承認済み）。

    呼び出しはこの関数専用（classify_passthrough_stage のトップレベル段では sequencing 演算子は
    元の挙動＝None のまま。これは丸括弧の外側での `&&`/`;` がシェルの結合優先順位により実際に
    別パイプラインに分かれる＝真の非該当であって、こちらは「安全」の表現が引き続き正しい）。"""
    segments = [seg for seg in re.split(r"&&|\|\||;|\n", stripped) if seg.strip()]
    if not segments:
        return None, None
    passthrough_results = []
    for seg in segments:
        seg_stripped = seg.strip()
        try:
            seg_tokens = strip_leading_wrappers(shlex.split(seg_stripped, posix=True))
        except ValueError:
            seg_tokens = None
        if (
            seg_tokens
            and seg_tokens[0] in NOOP_STDOUT_FREE_COMMANDS
            and not strip_stderr_only_redirections(seg_tokens[1:])
        ):
            continue  # 標準出力を生成しないことが既知のコマンド（stderr リダイレクトのみは無害）
        kind, byte_cap = classify_subshell_body(seg)
        if kind is None:
            return None, None
        passthrough_results.append((kind, byte_cap))
    if not passthrough_results:
        return None, None  # 全セグメントが noop（true/:/false のみ）＝標準入力を一切読まないため
                            # 出力は常に空になり、パイプ上流の内容とは一致しない（恒等ではない）
    if len(passthrough_results) == 1:
        return passthrough_results[0]
    if all(kind == "unconditional" and byte_cap is None for kind, byte_cap in passthrough_results):
        return "unconditional", None
    return None, None


def classify_subshell_body(text):
    """丸括弧で1回以上囲まれたサブシェルの中身を解析し、("unconditional" | "single_line",
    byte_cap) または (None, None) を返す（PR #219 opus レビュー・クラスA対応）。

    - 中身がさらに丸括弧で囲まれていれば多重サブシェルとして再帰的に剥がす。
    - トップレベルの `|` を含めば、split_top_level_pipes で分割した各段が全て
      classify_subshell_body で passthrough と判定される場合に限り、サブシェル全体を1段の
      パススルーとして扱う（従来の Issue #218 ギャップ1 対応を踏襲。いずれかの段が
      single_line なら全体も single_line、byte_cap は各段の cap の最小値を採用）。
    - パイプを含まず `&&`/`||`/`;`/改行のみで連結されたコマンド列は
      classify_operator_sequence_stage に委ねる（サブシェル内の sequencing 演算子対応）。
    - それ以外（単一の単純コマンド）は classify_simple_command_stage に委ねる。
    """
    stripped = text.strip()
    if not stripped:
        return None, None
    nested = strip_matching_parens(stripped)
    if nested is not None:
        return classify_subshell_body(nested)
    sub_stages = split_top_level_pipes(stripped)
    if len(sub_stages) > 1:
        if any(not sub.strip() for sub in sub_stages):
            return None, None
        results = [classify_subshell_body(sub) for sub in sub_stages]
        if any(kind is None for kind, _cap in results):
            return None, None
        kinds = [kind for kind, _cap in results]
        caps = [cap for _kind, cap in results if cap is not None]
        combined_kind = "single_line" if "single_line" in kinds else "unconditional"
        combined_cap = min(caps) if caps else None
        return combined_kind, combined_cap
    if STAGE_OPERATOR_SPLIT_RE.search(stripped):
        return classify_operator_sequence_stage(stripped)
    return classify_simple_command_stage(stripped)


# fail-closed センチネル（Issue #222・Claude 版と同一設計）: classify_passthrough_stage の
# (None, None) には意味が2種類混在している——(a) トップレベル（丸括弧の外側）の
# `&&`/`||`/`;`/改行演算子を含む段は、シェルの結合優先順位（`|` が `&&`/`||`/`;` より強く
# 結合する）により実際には別々の独立したパイプラインに分かれることが構造的に証明できる＝
# 「確定的に無関係」であって fail-closed の対象ではない。(b) それ以外の全て（未知のコマンド・
# ファイルオペランド・引数の組み合わせ・構文エラー等）は「安全と確定できない」であって
# fail-closed の対象。呼び出し元 literal_producer_value_through_passthrough がこの2つを
# 区別できるよう、(a) には専用のセンチネル値を返す。
_DISCONNECTED_OPERATOR_SEQUENCE = "disconnected-operator-sequence"
# producer 値が静的に確定できず、かつ「確定的に無関係」とも証明できなかったことを表す
# センチネル。None（Python の通常の欠損値）や実際の producer 文字列と衝突しない専用オブジェクト
# にすることで、呼び出し元が「値なし（disconnected・安全）」と「値不明（fail-closed・危険側）」を
# 確実に区別できるようにする。
_UNVERIFIABLE_PRODUCER = object()


def classify_passthrough_stage(stage_text):
    """stage_text（split_top_level_pipes/top_level_pipeline_stages で得られた、トップレベルの
    パイプ段テキスト）が、標準入力をそのまま標準出力へ転送するだけのパススルーかどうかを判定し、
    ("unconditional" | "single_line", byte_cap) を返す。

    それ以外の場合は (None, None) または (_DISCONNECTED_OPERATOR_SEQUENCE, None) を返す
    （Issue #222・fail-closed 設計転換。呼び出し元 literal_producer_value_through_passthrough が
    両者を区別する）。

    - "unconditional": cat/tee のように、入力の行数や内容に関わらず常に恒等変換になる。
    - "single_line": sort/head/tail/uniq のように、入力が改行を含まない単一行であり、かつ
      is_single_line_identity_args が真を返す引数の組み合わせの場合に限り恒等になる。呼び出し側
      literal_producer_value_through_passthrough が、最終的に確定した producer 値が実際に単一行
      （"\\n" を含まない）であることを別途確認する（Issue #218 ギャップ2）。
    - byte_cap: None なら無条件、正の整数 N なら producer 値のバイト長が N 以下の場合に限り
      恒等（head/tail の `-c`/`--bytes` 対応・PR #219 opus レビュー クラスB追随）。

    丸括弧 `( ... )` で stage_text 全体が囲まれている場合は classify_subshell_body に委譲し、
    サブシェルの中身（ネストしたパイプ・sequencing 演算子を含む）を解析する（Issue #218 ギャップ1
    ／PR #219 opus レビュー クラスA。サブシェル内では &&/;/|| は接続を切らないため、その中の
    「確定できない」は全て _UNVERIFIABLE_PRODUCER 側になる——classify_subshell_body/
    classify_operator_sequence_stage は独自に (None, None) を返すのみで、この関数のような
    disconnected センチネルは持たない）。

    丸括弧で囲まれていない場合、`&&`/`||`/`;`/改行を含む段は _DISCONNECTED_OPERATOR_SEQUENCE を
    返す（トップレベルではシェルの結合優先順位により実際には別々のパイプラインに分かれることが
    構造的に証明できるため、fail-closed の対象にしない＝既存の安全側設計を維持。サブシェル内でのみ
    意味が異なる点は classify_operator_sequence_stage のコメント参照）。
    """
    stripped = stage_text.strip()
    if not stripped:
        return None, None
    inner = strip_matching_parens(stripped)
    if inner is not None:
        return classify_subshell_body(inner)
    if STAGE_OPERATOR_SPLIT_RE.search(stripped):
        return _DISCONNECTED_OPERATOR_SEQUENCE, None
    return classify_simple_command_stage(stripped)


def literal_producer_value_through_passthrough(stages, index):
    """stages[index] から後方（producer 方向）へ、パススルー段（classify_passthrough_stage）を
    許容しながら literal_producer_value が確定できる最初の段まで遡る。index は毎回1段ずつ減る
    ため、有限のステージ数で必ず終了する（無限ループにはならない）。

    戻り値は3通り（Issue #222・fail-closed 設計転換）:
    - 文字列: producer 値を静的に確定できた（既存の高速パス。find_violation がこの値を
      再帰的に scan し、実際に git merge/gh pr merge/git push が含まれるかを厳密に判定する）。
    - None: 途中で classify_passthrough_stage が _DISCONNECTED_OPERATOR_SEQUENCE を返した
      （丸括弧の外側の &&/||/;/改行によりシェルの結合優先順位で実際には別パイプラインに
      分かれることが構造的に証明できた＝**真に安全と確認済み**。fail-closed の対象にしない）。
    - _UNVERIFIABLE_PRODUCER: それ以外の理由で確定できなかった（未知のコマンド・ファイル
      オペランド・構文エラー・sort/head/tail/uniq の未対応フラグ・sequencing 演算子内の
      解決不能な組み合わせ等）。呼び出し元（bare_interpreter_reexec_bodies/xargs_reexec_bodies）
      はこれを「sink（interpreter や git/gh）に到達しうる内容を安全と確認できなかった」と
      みなし、fail-closed で deny 側に倒す（PR #219 3ラウンドで判明した通り、ここを
      「確定できない＝ALLOW」にすると新しい未知のシェル構文のたびに個別対応が必要になる
      whack-a-mole になるため、初期値を反転した）。

    途中で "single_line" 種別のパススルー段（sort/head/tail/uniq）を1つでも経由した場合は、
    最終的に確定した producer 値が改行を含む場合（＝実際には単一行ではなかった場合）、
    single_line 種別のコマンドについて確認済みの「単一行入力に対してのみ恒等」という前提が
    成立しなくなるため _UNVERIFIABLE_PRODUCER を返す（Issue #218 ギャップ2 の判定自体は
    「真に恒等でない」ことを検出できているが、fail-closed 転換によりその場合は deny 側に
    倒す——これは既存の安全側判定を「確定的に無関係」からさらに一段厳しくした変更ではなく、
    「恒等の前提が崩れた＝もはや安全と確認できない」という当然の帰結）。byte_cap 付きの段
    （head/tail の `-c`/`--bytes`）を経由し、producer 値の UTF-8 バイト長が経由した全 byte_cap
    の最小値を超える場合も同様に _UNVERIFIABLE_PRODUCER を返す。"""
    requires_single_line = False
    max_bytes = None
    while index >= 0:
        value = literal_producer_value(stages[index])
        if value is not None:
            if requires_single_line and "\n" in value:
                return _UNVERIFIABLE_PRODUCER
            if max_bytes is not None and len(value.encode("utf-8")) > max_bytes:
                return _UNVERIFIABLE_PRODUCER
            return value
        kind, byte_cap = classify_passthrough_stage(stages[index])
        if kind == _DISCONNECTED_OPERATOR_SEQUENCE:
            return None  # 構造的に無関係と証明済み＝真に安全。fail-closed 対象にしない。
        if kind is None:
            return _UNVERIFIABLE_PRODUCER
        if kind == "single_line":
            requires_single_line = True
        if byte_cap is not None and (max_bytes is None or byte_cap < max_bytes):
            max_bytes = byte_cap
        index -= 1
    return _UNVERIFIABLE_PRODUCER


# xargs プレースホルダ置換対応（Issue #213 受け入れ基準2・Claude 版と同一設計）: `echo 'git merge
# evil' | xargs -I{} bash -c '{}'` のように、`-I` で指定したプレースホルダ（既定 `{}`）が xargs
# 経由で実行時に置換されるパターンは、quoted_subcommands が `bash -c '{}'` を抽出してもプレース
# ホルダのリテラル文字列のままで、実際に代入される値（パイプ上流からの入力）を静的に追えず検知漏れに
# なっていた。本関数は、xargs の直前のパイプステージ（またはそこから純粋なパススルー＝cat/tee を
# 許容して遡った先のステージ。Issue #215）が echo/printf のみの静的リテラル引数で構成されている
# 場合に限り（literal_producer_value_through_passthrough が値を確定できる場合のみ）、その値を
# プレースホルダに埋め込んだ上で xargs のコマンド部分を reexec 対象として返す。上流が非リテラル
# の場合は対象外（安全側）。長形式 `--replace` 等の非 `-I` 記法は未対応（既知の残存ギャップ・
# 完全網羅は目指さない設計方針＝受け入れ基準5）。
XARGS_PLACEHOLDER_RE = re.compile(r"(?<!\S)-I[ \t]*(\S+)")


def xargs_template_is_dangerous_shape(remainder, placeholder):
    """xargs -I{} のテンプレート（`-I` フラグ以降のテキスト）が、代入値を静的に確定できなくても
    危険とみなすべき「形」をしているかどうかを判定する（Issue #222・fail-closed 設計転換・
    Claude 版と同一設計）。

    危険な形と判定する3パターン:
    1. テンプレートの先頭コマンドがプレースホルダそのもの（`xargs -I{} {}`）＝代入値が
       コマンド全体になる。
    2. テンプレートの先頭コマンドが git/gh（`xargs -I{} git {}` 等）＝代入値が git/gh の
       サブコマンド位置に来る可能性を排除できない。
    3. テンプレートの先頭コマンドが HEREDOC_INTERPRETER_COMMANDS（bash/sh/python/eval 相当）＝
       代入値がインタプリタへの入力になる可能性を排除できない。

    それ以外（`wc -l {}`/`rm {}` のように、プレースホルダが git/gh/interpreter 以外の通常の
    コマンドの引数位置に来るだけの形）は対象化しない。これは「代入値が具体的に何であっても
    git merge/gh pr merge/git push の形にはなり得ない」ことが構造的に保証できるためであり、
    既存の一般的な xargs イディオム（`find . | xargs -I{} wc -l {}` 等）を壊さないための
    意図的なスコープ限定（受け入れ基準4・over-deny 実害の抑制）。"""
    try:
        rem_tokens = strip_leading_wrappers(shlex.split(remainder.strip(), posix=True))
    except ValueError:
        return True  # テンプレート自体を解析できない = 安全と確認できないため危険側に倒す
    if not rem_tokens:
        return True
    if rem_tokens[0] == placeholder:
        return True
    head = os.path.basename(rem_tokens[0])
    if head in {"git", "gh"}:
        return True
    if head in HEREDOC_INTERPRETER_COMMANDS:
        return True
    return False


def xargs_reexec_bodies(command_text):
    """戻り値は (bodies, fail_closed) のタプル（Issue #222・fail-closed 設計転換・Claude 版と
    同一設計）。bodies: 従来どおり、producer 値を静的に確定できた場合の reexec 候補テキストの
    リスト（find_violation が再帰的に scan して実際に git/gh 違反かを厳密判定する・既存の
    高速パス）。fail_closed: True の場合、xargs -I{} の代入先が危険な形
    （xargs_template_is_dangerous_shape）をしているにもかかわらず、上流 producer の値を静的に
    確定できなかった（literal_producer_value_through_passthrough が _UNVERIFIABLE_PRODUCER を
    返した）ことを示す。このとき find_violation は安全側で deny する（内容を具体的に特定
    できなくても、xargs の代入先の形自体が git/gh/interpreter に直結しているため）。"""
    bodies = []
    fail_closed = False
    # top_level_pipeline_stages: 丸括弧サブシェル対応（Issue #218 ギャップ1／PR #219 opus レビュー
    # クラスA：パイプライン全体が丸ごとサブシェルに包まれる `(... | xargs ...)` 形も展開する）。
    stages = top_level_pipeline_stages(command_text)
    for i in range(1, len(stages)):
        # unwrap_redundant_parens: consumer 位置が丸括弧で包まれる `(xargs ...)` 形にも対応
        # （PR #219 opus レビュー クラスA。bash 側と同じ理由づけ）。
        stage_text = unwrap_redundant_parens(stages[i])
        try:
            stage_tokens = strip_leading_wrappers(shlex.split(stage_text.strip(), posix=True))
        except ValueError:
            continue
        if not stage_tokens or stage_tokens[0] != "xargs":
            continue
        m = XARGS_PLACEHOLDER_RE.search(stage_text)
        if not m:
            continue
        placeholder = m.group(1)
        remainder = stage_text[m.end():]
        if placeholder not in remainder:
            continue
        literal_value = literal_producer_value_through_passthrough(stages, i - 1)
        if literal_value is _UNVERIFIABLE_PRODUCER:
            if xargs_template_is_dangerous_shape(remainder, placeholder):
                fail_closed = True
            continue
        if literal_value is None:
            continue
        bodies.append(remainder.replace(placeholder, literal_value))
    return bodies, fail_closed


# 非 `-I` 形式の xargs 対応（PR #223 opus 再レビュー指摘B・2026-07-13 オーナー方針転換・Claude 版と
# 同一設計）: `echo 'git push' | xargs -0 bash -c` のように `-I` を使わない xargs は、stdin から
# 読んだトークンを COMMAND の末尾に追記して実行する（`-0` は NUL 区切り指定に過ぎず、追記される
# という基本動作は変わらない）。xargs_reexec_bodies は `-I` の有無で判定しており、この形式は
# 一切見ていなかったため素通りしていた（実 bash で実際に実行されることを確認済み）。
# オーナー方針転換により、代入値の正確な追記位置・区切り方（-0/-n/-L 等の組み合わせ）を
# 精密に静的解決することは狙わず、「xargs が実行しようとしているコマンドの先頭が
# git/gh/interpreter である」という危険な形をしている場合、producer 値の確定可否によらず
# 一律 fail-closed とする（過検知は許容し見逃さないことを優先する・#222 オーナー方針）。
XARGS_BOOL_FLAGS = {
    "-0", "--null", "-t", "--verbose", "-p", "--interactive", "-x", "--exit",
    "-r", "--no-run-if-empty", "-o", "--open-tty",
}
XARGS_VALUE_FLAGS = {
    "-I", "-i", "--replace", "-L", "-l", "--max-lines", "-n", "--max-args",
    "-P", "--max-procs", "-d", "--delimiter", "-a", "--arg-file", "-s",
    "--max-chars", "-E", "--eof",
}
_XARGS_COMBINED_SHORT_FLAG_RE = re.compile(r"^-[IiLlnPdsE].+")


def xargs_command_head(stage_tokens):
    """stage_tokens[0]=='xargs' として、xargs 自身のオプション（値を伴うもの・伴わないもの・
    結合形の両方）を読み飛ばし、xargs が実行するコマンドの先頭トークンを返す（見つからなければ
    None）。未知のトークンに遭遇した場合はそこまでで打ち切りコマンドの先頭とみなす（安全側＝
    見逃さない方向。過検知は許容する）。"""
    i = 1
    n = len(stage_tokens)
    while i < n:
        tok = stage_tokens[i]
        if tok == "--":
            i += 1
            break
        if tok in XARGS_VALUE_FLAGS:
            i += 2
            continue
        if tok in XARGS_BOOL_FLAGS:
            i += 1
            continue
        if _XARGS_COMBINED_SHORT_FLAG_RE.match(tok):
            i += 1
            continue
        if tok.startswith("--") and "=" in tok:
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    return stage_tokens[i] if i < n else None


def xargs_without_placeholder_fail_closed(command_text):
    """xargs が `-I` プレースホルダを使わない形式（`xargs -0 bash -c` 等）で、実行しようとする
    コマンドの先頭が git/gh/interpreter である場合、producer 値の確定可否によらず True を返す
    （PR #223 opus 再レビュー指摘B）。`-I` 形式は xargs_reexec_bodies が別途厳密に処理するため
    ここでは対象外にする（二重処理を避ける）。"""
    stages = top_level_pipeline_stages(command_text)
    for i in range(1, len(stages)):
        stage_text = unwrap_redundant_parens(stages[i])
        if XARGS_PLACEHOLDER_RE.search(stage_text):
            continue  # -I 形式は xargs_reexec_bodies が担当
        try:
            stage_tokens = strip_leading_wrappers(shlex.split(stage_text.strip(), posix=True))
        except ValueError:
            continue
        if not stage_tokens or stage_tokens[0] != "xargs":
            continue
        head = xargs_command_head(stage_tokens)
        if head is None:
            continue
        name = os.path.basename(head)
        if name in {"git", "gh"} or name in HEREDOC_INTERPRETER_COMMANDS:
            return True
    return False


# stdin エイリアスの疑似ファイルパス対応（PR #223 opus 再レビュー指摘A・2026-07-13 オーナー方針
# 転換：過剰denyを許容し「確証が持てない＝deny」をデフォルトにする・Claude 版と同一設計）:
# `/dev/stdin`・`/dev/fd/N`・`/proc/self/fd/N`・`/proc/PID/fd/N` は、OS が提供する「自プロセスの
# 標準入力」を指す疑似ファイルパスであり、`bash /dev/stdin` はファイルではなく実質的に標準入力を
# スクリプトとして読む（`bash` 単体・`bash <(CMD)` と全く同じ危険性）。従来の
# bare_interpreter_reexec_bodies は「位置引数があれば標準入力を読まないため対象外」という
# 前提を無条件に適用しており、これらの疑似パスも「実在のスクリプトファイル」と誤って
# 同一視して素通りしていた（`echo 'git push' | bash /dev/stdin` 等が実 bash で実際に実行される
# ことを確認済み・本PR自身が `<(...)` プロセス置換で是正したのと全く同一のバグクラス）。
_STDIN_ALIAS_PATH_RE = re.compile(r"^/(dev/stdin|dev/fd/\d+|proc/self/fd/\d+|proc/\d+/fd/\d+)$")


def bare_interpreter_reexec_bodies(command_text):
    """一般パイプ経由対応（Issue #213 受け入れ基準6・Claude 版と同一設計）: `printf '%s' 'git merge
    evil' | bash` のように、ヒアドキュメントを使わない素朴なパイプでインタプリタへ渡す経路を検知する。
    パイプ下流ステージの「最初のサブコマンド」（first_operator_segment。`bash && true` のように
    後続に `&&`/`;` 等で別コマンドが連結されていても、実際にパイプへ繋がるのは最初の一つだけの
    ため）の先頭コマンドがインタプリタ（HEREDOC_INTERPRETER_COMMANDS を流用）で、かつ
    `-c`/`--command` を伴わず、最初の位置引数（スクリプトファイル等）が無いか、または stdin
    エイリアス（_STDIN_ALIAS_PATH_RE。`/dev/stdin`/`/dev/fd/N`/`/proc/self/fd/N` 等・PR #223
    opus 再レビュー指摘A）の場合のみ、上流ステージ（またはそこから純粋なパススルー＝cat/tee を
    許容して遡った先のステージ。Issue #215）の literal_producer_value_through_passthrough を
    reexec 対象として返す。最初の位置引数が stdin エイリアスに一致しない実在のファイルパス
    （`bash script.sh`／`source FILE` 等）の場合は標準入力ではなくそのファイルを読むため対象外と
    する（新規の過検知を避けるため。2個目以降の位置引数はスクリプトへの `$1`/`$2` 等の引数に
    過ぎず、標準入力を読むかどうかの判定には関与しないため無視する）。

    PR #219 opus レビュー クラスA追随（Claude 版と同一設計）: `echo x | (bash)`（consumer 位置を
    丸括弧で包む）や `(echo x | bash)`（パイプライン全体を丸括弧で包む）は実 bash で実際に
    ペイロードが実行されるにもかかわらず、当初の実装では検知できなかった（前者は shlex トークンが
    `(bash)` という1語になり HEREDOC_INTERPRETER_COMMANDS と一致しない、後者はトップレベルの
    `|` が見つからず stages が1要素のまま split されない）。top_level_pipeline_stages/
    unwrap_redundant_parens で対応する。

    戻り値は (bodies, fail_closed) のタプル（Issue #222・fail-closed 設計転換・Claude 版と同一
    設計）。interpreter シンクが確定しているにもかかわらず
    literal_producer_value_through_passthrough が _UNVERIFIABLE_PRODUCER を返した場合
    （サブシェル・sequencing 演算子・stderr リダイレクト・fd 複製/クローズ構文等、未知・未対応の
    シェル構文を含む場合すべて）、fail_closed=True を返し find_violation が安全側で deny する。
    これにより、これまで3ラウンドで個別に列挙して塞いできたバイパスの全クラスが、個別の
    point-fix ではなく本関数のこの1箇所の設計原理で自動的に閉じる。"""
    bodies = []
    fail_closed = False
    # top_level_pipeline_stages: 丸括弧サブシェル対応（Issue #218 ギャップ1／PR #219 クラスA）。
    stages = top_level_pipeline_stages(command_text)
    for i in range(1, len(stages)):
        # unwrap_redundant_parens: consumer 位置が丸括弧で包まれる `(bash)` 形にも対応
        # （PR #219 opus レビュー クラスA）。
        stage_text = unwrap_redundant_parens(first_operator_segment(stages[i]))
        try:
            stage_tokens = strip_leading_wrappers(shlex.split(stage_text.strip(), posix=True))
        except ValueError:
            continue
        if not stage_tokens:
            continue
        name = os.path.basename(stage_tokens[0])
        if name not in HEREDOC_INTERPRETER_COMMANDS:
            continue
        rest_args = stage_tokens[1:]
        if any(arg in {"-c", "--command"} for arg in rest_args):
            continue  # スクリプトが引数そのもの＝quoted_subcommands が別途担当
        first_positional = None
        for arg in rest_args:
            if not arg.startswith("-"):
                first_positional = arg
                break
        if first_positional is not None and not _STDIN_ALIAS_PATH_RE.match(first_positional):
            continue  # 実在のスクリプトファイルパス（stdin エイリアスでない）＝標準入力を読まない
        literal_value = literal_producer_value_through_passthrough(stages, i - 1)
        if literal_value is _UNVERIFIABLE_PRODUCER:
            fail_closed = True
            continue
        if literal_value is None:
            continue
        bodies.append(literal_value)
    return bodies, fail_closed


# プロセス置換対応（Issue #222 実装時の敵対的自己検証で新規発見・Claude 版と同一設計）: `<(CMD)`/
# `>(CMD)`（bash のプロセス置換。`<(CMD)` は CMD の標準出力を読める名前付きパイプ／fd のパスに
# 展開され、consumer からはファイルパスを渡されたように見える）は、
# `bash <(echo 'git merge evil')` を実 bash で実行すると実際にペイロードが走ることを確認済みの
# 重大バイパスだった。bare_interpreter_reexec_bodies の「位置引数（スクリプトファイル等）がある
# 場合は標準入力を読まないため対象外」という既存の安全側ロジック（Issue #213 由来）が、`<(...)`
# を「普通の位置引数＝実在のファイルパス」と誤って同一視してしまうため素通りしていた。実際には
# `<(...)` の中身は command_text 自身に literal に書かれているコマンドであり（パイプ上流のように
# 実行時にしか定まらない値ではない）、producer 遡及は不要でヒアドキュメント本文と全く同じ扱いで
# 無条件に再帰走査すればよい。shlex は `<(`/`>(` を理解できず誤トークン化するため、shlex 経由
# ではなく専用の丸括弧深さ追跡で抽出する。
def process_substitution_bodies(command_text):
    """command_text 中の `<(...)`/`>(...)`（プロセス置換）の内側のコマンドテキストを全て
    抽出して返す。丸括弧のネストを深さで追跡し、対応が取れないものは無視する（安全側：
    見逃しても新規の過検知にはならず、単に検知対象が1件減るだけに留まる）。"""
    bodies = []
    for m in re.finditer(r"[<>]\(", command_text):
        start = m.end()
        depth = 1
        i = start
        n = len(command_text)
        while i < n and depth > 0:
            if command_text[i] == "(":
                depth += 1
            elif command_text[i] == ")":
                depth -= 1
            i += 1
        if depth == 0:
            bodies.append(command_text[start:i - 1])
    return bodies


# プロセス置換をインタプリタの位置引数として渡す形（`bash <(echo 'git merge evil')`）専用の
# fail-closed 対応（Claude 版と同一設計）。process_substitution_bodies（上）は `<(...)` の中身を
# 常に raw テキストとして再帰走査するため、中身が直接 `git ...`/`gh ...` で始まる場合は
# direct_violation が拾えるが、`echo 'git merge evil'` のように「実行した"結果"が git merge に
# なる」間接形は raw テキストの先頭トークンが "echo" のままなので捕まらない（実 bash で確認済み・
# 真のバイパス）。bare_interpreter_reexec_bodies は「位置引数（スクリプトファイル等）がある場合は
# 標準入力を読まないため対象外」という Issue #213 由来の安全側ロジックを持つが、`<(...)` を通常の
# 位置引数（実ファイルパス）と同一視してしまい、これも素通りしていた。`<(CMD)` は bash が CMD を
# サブプロセスとして起動しその stdout を fd 経由でインタプリタに渡す仕組みであり、パイプ経由で
# stdin を渡すのと安全性の観点では等価（インタプリタは結局 CMD の出力をスクリプトとして読む）。
# よって CMD 自身を1本のミニパイプラインとみなし、既存の
# literal_producer_value_through_passthrough を再利用して producer 値を解決する（確定できれば
# scan、できなければ fail_closed）。
def process_substitution_reexec_bodies(command_text):
    """戻り値は (bodies, fail_closed) のタプル（他の *_reexec_bodies 系と統一）。

    xargs/bare-interpreter 系の `for i in range(1, len(stages))`（i=0 は producer 側なので除外）
    と異なり、本関数は `range(0, len(stages))` で全ステージを見る。`bash <(CMD)` はパイプの
    consumer 位置である必要が一切なく、パイプを介さない単独のコマンド（stages が1要素）でも
    バイパスが成立する（`bash <(echo 'git merge evil')` は実 bash で確認済み・パイプ不使用）
    ため、i=0（唯一のステージ含む）も対象にする必要がある。"""
    bodies = []
    fail_closed = False
    stages = top_level_pipeline_stages(command_text)
    for i in range(0, len(stages)):
        stage_text = unwrap_redundant_parens(first_operator_segment(stages[i]))
        if "<(" not in stage_text:
            continue
        head_match = re.match(r"\s*(\S+)", stage_text)
        if not head_match:
            continue
        wrapped = strip_leading_wrappers([head_match.group(1)])
        if not wrapped:
            continue
        name = os.path.basename(wrapped[0])
        if name not in HEREDOC_INTERPRETER_COMMANDS:
            continue
        for m in re.finditer(r"<\(", stage_text):
            start = m.end()
            inner_depth = 1
            j = start
            n = len(stage_text)
            while j < n and inner_depth > 0:
                if stage_text[j] == "(":
                    inner_depth += 1
                elif stage_text[j] == ")":
                    inner_depth -= 1
                j += 1
            if inner_depth != 0:
                continue
            inner_cmd = stage_text[start:j - 1]
            inner_stages = top_level_pipeline_stages(inner_cmd)
            value = literal_producer_value_through_passthrough(inner_stages, len(inner_stages) - 1)
            if value is _UNVERIFIABLE_PRODUCER:
                fail_closed = True
                continue
            if value is None:
                continue
            bodies.append(value)
    return bodies, fail_closed


# 動的に構成される sink コマンド名／stdin 読み取りループ対応（PR #223 opus 再レビュー指摘C・
# 2026-07-13 オーナー方針転換「過剰denyを許容する。危険コマンドや疑わしいコマンドが含まれて
# いれば、実行されるか気にせずブロックしていい」・Claude 版と同一設計）: これまでの fail-closed
# 対応は「sink が interpreter/git/gh だと確定している場合に、そこに至る内容を確認できなければ
# deny」だったが、以下は sink コマンド自体が何であるか静的に確定できない、または stdin の内容を
# コマンドとして解釈しうるループ構文であり、内容確認を待たずに deny すべきとオーナーが判断した:
#   1. `echo 'git push' | grep . | $(echo bash)` / `... | ${SHELL##*/}`: パイプ consumer の
#      先頭コマンド語が `$(...)`／バッククォート／`${...}` で動的に構成されており、それが
#      interpreter か無害なコマンドかを静的に判定できない。
#   2. `echo 'git push' | while read l; do eval "$l"; done`: `while`/`until` ループが `read`
#      で1行ずつ読み取りながら任意のコマンドとして実行しうる（`eval` の有無を問わず、ループの
#      中身を精査せず一律 deny する——オーナー方針「内容を精査せずdeny側に倒して構わない」）。
# 実 bash でいずれも実際にペイロードが実行されることを確認済み。
_DYNAMIC_COMMAND_NAME_RE = re.compile(r"\$\(|`|\$\{")
_STDIN_CONSUMING_LOOP_HEAD_WORDS = {"while", "until"}


def unverifiable_pipe_consumer_sink(command_text):
    """command_text のトップレベルのパイプ consumer（stages[1:]。producer 側の stages[0] は
    対象外）を走査し、(a) 先頭コマンド語が動的に構成されている（_DYNAMIC_COMMAND_NAME_RE に
    一致）、または (b) `while`/`until` から始まり `read` を含む stdin 読み取りループである
    場合に True を返す。内容の精査は行わず、形だけで判定する（過検知許容・見逃さない方針。
    PR #223 opus 再レビュー指摘C）。"""
    stages = top_level_pipeline_stages(command_text)
    for i in range(1, len(stages)):
        stage_text = unwrap_redundant_parens(first_operator_segment(stages[i]))
        stripped = stage_text.strip()
        if not stripped:
            continue
        try:
            tokens = shlex.split(stripped, posix=True)
        except ValueError:
            tokens = stripped.split()
        tokens = strip_leading_wrappers(tokens)
        if not tokens:
            continue
        head = tokens[0]
        if _DYNAMIC_COMMAND_NAME_RE.search(head):
            return True
        if head in _STDIN_CONSUMING_LOOP_HEAD_WORDS and "read" in tokens:
            return True
    return False


def find_violation(command_text, role, depth=0):
    """戻り値は (violation, fail_closed) のタプル（Issue #222・fail-closed 設計転換・Claude 版と
    同一設計）。violation: 従来どおり、"git merge"/"git push"/"gh pr merge"/"git alias for merge"
    のいずれか（具体的に何が検出されたかを表す既存の高精度パス）または None。
    fail_closed: True の場合、xargs_reexec_bodies/bare_interpreter_reexec_bodies/
    process_substitution_reexec_bodies のいずれかが「sink（interpreter や git/gh）は確定して
    いるが、そこに至る内容を静的に安全と確認できなかった」ことを検知したことを示す（violation が
    None でも fail_closed=True ならこの呼び出しの親は deny すべき）。再帰呼び出し
    （reexec_bodies/quoted_subcommands 経由）のいずれかで fail_closed が立った場合も上位へ
    伝播する。"""
    if depth > 3:
        return None, False
    if depth == 0:
        scan_text, reexec_bodies = extract_heredocs(command_text)
    else:
        # depth>0 は quoted_subcommands が eval/bash -c/python -c の引数として抽出した、
        # 既に「再実行される」と判定済みのテキスト。ヒアドキュメント除去はせず素のスキャンを維持する。
        scan_text, reexec_bodies = command_text, []
    # here-string/xargs プレースホルダ/一般パイプ経由の reexec 対象は、ヒアドキュメントと異なり
    # 単一行の判定であるため depth を問わず毎回抽出する（Issue #213）。ただし command_text ではなく
    # scan_text（ヒアドキュメント本文を除去済みのテキスト）を走査対象にする。ヒアドキュメント本文
    # （例: `cat > file.py <<'EOF' ... EOF` で書き出す Python ソース中の文字列リテラル）に
    # 偶然 `<<<`/パイプ/xargs に見える記法が含まれていても、それは実行されないデータであり
    # over-deny してはならない（Issue #189 の false positive 是正方針を踏襲。command_text で
    # 走査すると reaches_interpreter 判定がヒアドキュメント本文内の直前の語だけを見て誤って
    # 「再実行される」と判定してしまう回帰があったため、実装中の敵対的自己検証で発見し是正）。
    reexec_bodies = list(reexec_bodies) + herestring_reexec_bodies(scan_text)
    reexec_bodies += process_substitution_bodies(scan_text)
    xargs_bodies, xargs_fail_closed = xargs_reexec_bodies(scan_text)
    bare_bodies, bare_fail_closed = bare_interpreter_reexec_bodies(scan_text)
    procsub_bodies, procsub_fail_closed = process_substitution_reexec_bodies(scan_text)
    reexec_bodies += xargs_bodies + bare_bodies + procsub_bodies
    fail_closed = (
        xargs_fail_closed
        or bare_fail_closed
        or procsub_fail_closed
        or xargs_without_placeholder_fail_closed(scan_text)
        or unverifiable_pipe_consumer_sink(scan_text)
    )
    for segment in SEGMENT_SPLIT_RE.split(scan_text):
        violation = direct_violation(shell_words(segment), role)
        if violation:
            return violation, fail_closed
    for body in reexec_bodies:
        violation, nested_fail_closed = find_violation(body, role, depth + 1)
        fail_closed = fail_closed or nested_fail_closed
        if violation:
            return violation, fail_closed
    for nested in quoted_subcommands(command_text):
        violation, nested_fail_closed = find_violation(nested, role, depth + 1)
        fail_closed = fail_closed or nested_fail_closed
        if violation:
            return violation, fail_closed
        for literal in quoted_literals(nested):
            violation, literal_fail_closed = find_violation(literal, role, depth + 1)
            fail_closed = fail_closed or literal_fail_closed
            if violation:
                return violation, fail_closed
    return None, fail_closed

reason = None
role = agent_type if agent_type in {"issue-implementer", "pr-reviewer"} else "unknown"
if role == "unknown":
    # 対象外ロール（main context 自身・欠如を含む）は常に許可。上記オーナー判断の通り。
    pass
elif tool_name not in SHELL_TOOL_NAMES:
    # git/gh はシェル(Bash)ツール経由でのみ走る。非シェルツール（apply_patch 等）は対象外。
    pass
elif not isinstance(command, str) or not command:
    reason = "agent-command-gate: PreToolUse payload does not contain tool_input.command; refusing because the Bash command cannot be inspected."
else:
    violation, fail_closed = find_violation(command, role)
    if agent_type == "issue-implementer" and violation:
        reason = f"issue-implementer role: {violation} is reserved for pr-reviewer. Push + open a PR, then stop and report."
    elif agent_type == "pr-reviewer" and violation:
        reason = f"pr-reviewer role: {violation} is reserved for issue-implementer. Reviewers may inspect/comment/merge only, never push code."
    elif fail_closed:
        # Issue #222・fail-closed 設計転換（Claude 版と同一設計）: 具体的な違反コマンドを
        # 特定できなくても、パイプ/xargs プレースホルダ/プロセス置換が interpreter や git/gh に
        # 到達することは確定しており、そこに至る内容を安全と静的に確認できなかった。役割非対称
        # メッセージ（"is reserved for pr-reviewer" 等）は「もう一方のロールなら許可される」と
        # いう誤った含意を持つため使わず、専用の理由文を返す。ここに到達する時点で role は
        # 既に issue-implementer/pr-reviewer のいずれかに確定している（"unknown" は上の
        # `if role == "unknown": pass` で早期に抜けている）。
        reason = (
            f"{agent_type} role: a pipe segment or xargs -I{{}} placeholder reaches an "
            "interpreter (or git/gh), but the content flowing into it could not be statically "
            "verified as safe (unrecognized/unenumerated shell construct between the source and "
            "the sink). Denying conservatively by default (fail-closed; Issue #222) instead of "
            "assuming it is safe."
        )

if reason:
    debug_payload(payload, "deny", reason)
    trace_event(agent_type, tool_name, "deny")
    deny(reason)
else:
    debug_payload(payload, "allow", "")
    trace_event(agent_type, tool_name, "allow")
PYEOF
exit 0
