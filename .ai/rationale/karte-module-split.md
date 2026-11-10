# karte / karte_notify の責務分割で移設した設計理由（PR #696）

`karte/cli.py` と `karte_notify/notify.py` から責務ごとに新モジュールへ切り出した際、連続コメント3行以内の規約（Issue #539）に合わせて縮めたコード側の説明を、移設元の文言のまま保管する。コード側は各モジュール冒頭から本ファイルへ1行で辿れる。

## `karte_notify/trigger.py`：tool 呼び出しの検出（移設元：`karte_notify/notify.py`・Issue #512）

### 検出の対象は `-m karte` 経由の起動だけ（`TRIGGER_RE`）
`karte ingest-review` / `karte close-attempt` の実行を検出する（Issue #512 Scope 1）。`-m karte` 経由の module 起動だけを見る（`karte` package の CLI 契約そのものなので、エイリアス・別実行形は対象外＝取りこぼしても fail-open で実害が小さい方に倒す）。

### 検出対象の tool_name と `ctx_execute_file` の除外（`SUPPORTED_TOOL_NAMES`）
本フックが検出対象とする tool_name（Issue #512 是正・F-512-02）。`Bash` に加え、`.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」で issue-implementer / issue-fixer / pr-reviewer / 主文脈 / dsv2-lookup に付与済みの実行系 MCP ツール（`ctx_execute`/`ctx_batch_execute`）経由の `karte ingest-review`/`close-attempt` 実行も同じ通知対象にする。`ctx_execute_file` は既存方針で全ロール未付与のため対象に含めない（`.claude/rules/05-skills-agents.md` 同節）。

### 検出規則は経路によらず一本（旧 `karte_notify/notify.py` docstring「検出対象コマンドの拾い方」の要点）
トリガー実行は `Bash` 経由とは限らない。主文脈・`issue-implementer`・`issue-fixer`・`pr-reviewer`・`dsv2-lookup` にはいずれも実行系 MCP ツール（`ctx_execute`・`ctx_batch_execute`）が付与済みで、`python3 -m karte ingest-review`/`close-attempt` はこれらの `tool_input`（`code` / `commands[].command`）経由でも実行されうる。そこで `extract_commands` が `tool_name` ごとに検査対象の文字列を取り出し、`detect_trigger` がその文字列単位で `Bash` と同じ正規表現を適用する。判定ロジック自体は分岐させない＝経路が増えても検出規則は一本のまま。

### `language` を検査しない理由（`extract_commands`）
`Bash` は `tool_input.command`。`ctx_execute` は `tool_input.code`（`language: shell` 前提の呼び出し規約だが、ここでは `language` の真偽は検査しない——実行される文字列そのものを見れば検出には十分で、詐称されていても検出漏れ側には倒れない）。`ctx_batch_execute` は `tool_input.commands[].command` の全件を対象にし、どれか1件が一致すれば検出する。`tool_name` が対象外、または形が不正なら空リスト（呼び出し側はこれを「検出なし」として扱う＝fail-open）。

### 進行ポインタへのフォールバック（`issue_from_command`）
`--issue N` を `command` からベストエフォートで取り出す。見つからない／不正な形式なら `None`——呼び出し側は進行ポインタ（`tmp/_karte/active.json`）へのフォールバックを別途持つ（`karte status` 自身の `--issue` 省略時の補完と同じ扱い）。

## `karte/active_pointer.py`：進行ポインタの読み書き（移設元：`karte/cli.py` の `_read_active`）

`--issue` / `--round` の補完に使う（＝これが唯一の情報源）とき `required=True`。ポインタが**まだ無い**場合に `{}` を返さず `KarteUsageError` を送出する。

**壊れている場合は `required` によらず常に拒否する**（K-13/K-14/K-15）。JSON として読めない・dict でないポインタを黙って「無い」と同じ `{}` に潰すと、補完が沈黙のうちに別の値（別 Issue・別ラウンド）へ倒れ、誤った台帳を書き換えても観測できない。「まだ無い」（正常な初期状態）と「壊れている」（異常）は別物として扱う。

## `karte/ingest_review.py`：取り込み本体（移設元：`karte/cli.py` の `_ingest_review_locked`）

### K-06：「不在＝解消」の廃止
前ラウンド時点で未解消だった finding が 1 件でも欠けていれば取り込みごと拒否する（部分的なレポート 1 通で `harm: real` の指摘が消える fail-open だった）。欠けている ID は全て列挙する（1 件ずつ往復させない）。解消は**明示宣言**（`status: resolved`）でのみ成立し、`harm` の値によらず一律に扱う。

## `karte/ingest_apply.py`：台帳への反映（移設元：`karte/cli.py`）

### `scope` と `disposition` 系を毎ラウンド上書きする理由（Issue #495）
`scope` と `disposition` 系もレポートの値で毎ラウンド上書きする（他の欄と同じ扱い）。据え置きにすると「1 度書いた disposition が、以後書かれなくても残り続ける」ことになり、レポート側の記述と台帳が静かにずれる。書き忘れは未決定へ倒れて verdict のゲートに掛かる＝fail-close 側へ倒れる。

## `karte/ingest_checks.py`：レポート検証（移設元：`karte/cli.py`）

### `distinct_from` の参照先検査（K-05）
`distinct_from` の参照先が実在するか（K-05 のエスケープハッチを監査可能に保つ）。名指しできるのは **台帳にある finding** か、**同じレポート内で先に現れた finding** だけ。実在しない ID を書けてしまうと「何と別物か」の名指しが検証されず、重複判定を無効化するだけの呪文になる（＝握りつぶしの経路になる）ので fail-close で拒否する。自分自身の名指しも、判定を外す相手が存在しない無意味な宣言なので拒否する。

### 再発番検出で外すのは名指しされたペアだけ（K-05）
新規採番しようとしている指摘が、既存の未解消 finding の焼き直しでないかを見る。`item.distinct_from` で名指しされた相手は比較から外す（K-05）。外れるのは**名指しされたペアだけ**で、判定そのもの・閾値（`model.DUPLICATE_SIMILARITY_THRESHOLD`）は据え置く——偽陽性の逃げ道として閾値を下げると、本来検出したい再発番まで一律に見逃す。

## `verb_support.py` の分割（F-696-14）

当初の `karte/verb_support.py`（repo-root 解決・diff 用 cwd・issue 解決・台帳ロード・整数検証の5責務）は、名前が責務を表さず、ポインタ由来の補完も issue（`verb_support.resolve_issue`）と round（`cli._pointer_round`）の2箇所に分かれていた。責務ごとに次へ分け、`verb_support` は廃止した（以下の節の「移設元」は元の `karte/cli.py`、現在の実体は括弧内）。

| 責務 | 現在の module |
| --- | --- |
| repo-root の遅延解決・diff 用 cwd | `karte/repo_roots.py`（`repo_root_of`・`invoking_worktree`・テスト用上書き点 `_REPO_ROOT`／`_PACKAGE_ROOT`） |
| `--issue` / `--round` のポインタ補完（公開関数） | `karte/pointer_completion.py`（`resolve_issue`・`resolve_round`・`ingest_target`。`resolve_round` の旧名は `pointer_round`＝F-696-26） |
| 整数引数の検証 | `karte/int_args.py`（`ascii_int_or_none`・`require_ascii_int`・`parse_int`＝F-696-21） |
| 台帳の読み込み | `karte/karte_loader.py`（`load_karte`） |
| UTF-8 として正しい入出力だけを通す | `karte/utf8_text.py`（`read_stream_text`・`require_utf8_encodable`） |

上段（`owner_cli`／`reviewer_cli`／`pointer_round`）が private（`cli._pointer_round` 等）を import せずに済むよう、補完は公開関数として `pointer_completion` に置いた。

## repo-root と diff の cwd（現在の実体：`karte/repo_roots.py`・移設元：`karte/cli.py` の `_repo_root`・`_diff_cwd`・`_resolve_issue`）

### repo-root は呼び出しごとに遅延解決する（K-12・K-03）
linked worktree（`issue-implementer` 等の isolated worktree）でも main worktree の `tmp/_karte/` へ収束させる（K-01）。`.git` がファイルなら `gitdir:` を辿る `paths.main_worktree_root` を使う。**import 時に評価しない**。`main_worktree_root` は `.git` ファイルが不正形式なら `KartePathError` を送出するが、モジュールレベルで評価するとその例外はどの verb の fail-close 境界の内側でもない import 時に飛ぶ。`.git` が壊れた worktree では `python3 -m karte <任意の verb>` が未捕捉例外で終了し、文書化された終了コード `{0,2,3,4}` の外に漏れる（K-03 と同種＝観測不能）。呼び出しごとの解決なら `main()` 経由でも `cmd_*` 直呼びでも必ず境界の内側に入る。結果をキャッシュしないのは、プロセス内で worktree を跨ぐテスト・フックの挙動が呼び出し順に依存するため。

### `git diff` の cwd は main worktree へ収束させない（Issue #437）
台帳（`tmp/_karte/`）は worktree 間で共有すべき単一の正本なので main worktree へ収束させる。一方 `git diff` が測るべきなのは呼び出し元 worktree そのものの変更で、同じ収束をかけると isolated worktree（`.claude/worktrees/agent-*`）で行った commit が main の作業ツリーに存在せず diff が常に空になり、Issue #355 の空 diff fail-close が spurious に発火していた。そのため `repo_root_of`（台帳用）と `invoking_worktree`（diff 用）は別関数にしてある。`args.repo_root` の上書き（テスト専用）は台帳解決専用で、diff の cwd には効かない。

### `--issue` の補完（K-13/K-14/K-15）
フック（SubagentStart の `render`／SubagentStop の `ingest-review`・`check`／PostToolUse の `status`）は dispatch prompt を読めないため、Issue 番号の唯一の情報源は進行ポインタになる。ポインタが無い・壊れている・`issue` を欠くときは推測せず fail-close する。

### 整数引数は ASCII 数字だけを受ける（K-03・移設元：旧 `_validate_attempt_number`・`_validate_round`）
旧 `_validate_attempt_number` の docstring（原文）：「`--attempt` を検証する（`_validate_round` と同型・K-03）。`int(args.attempt)` を無検証で呼ぶと非数値入力で `ValueError` が送出され、`_fail_close` の捕捉対象外（文書化された終了コード `{0,2,3,4}` の外）に漏れる。」旧実装は `str.isdigit()` で判定していたが、`"²"` のような非 ASCII 数字も `isdigit()` は真を返し、続く `int()` が `ValueError` で同じ漏れを起こした。`parse_int` は ASCII 数字に限り、桁数が多すぎる入力（`int` の変換上限）も `KarteUsageError` に統一する。

## `karte/verb_boundary.py`：verb 単位の終了コード境界とロック要否の宣言（移設元：`karte/cli.py` の `_fail_close`・PR #696 レビュー L-2・L-6・F-696-01）

### なぜ verb 単位が終了コードの境界か（旧 `_fail_close` docstring の原文）
`cmd_*` を「例外を投げず終了コードを返す」境界にする。verb 単位が終了コードの境界（＝呼び出し側は `main` 経由でも直呼びでも同じ fail-close 挙動を得る）。`main` にだけ `try/except` を置くと、フックやテストのように `cmd_*` を直接呼ぶ経路では例外が素通りし、「拒否されたのに exit code が返らない」＝判定不能になる。ガードの効力を呼び出し経路に依存させない。

### 出荷されていた状態（origin/main）から現状への変更
- 出荷されていた `_fail_close` は、`func.__name__ in {"cmd_append", "cmd_close_attempt"}` という**関数名の判定**でロックを取っていた。一方 `cmd_ingest_review` は自分で `with paths.writer_lock(...)` を書く別流儀で、ロック要否の決まり方が二通りあった。名前判定は verb を改名・追加するとロックが静かに外れる。
- 現状の `fail_close(*, locked, prepare=None)` は `locked` を**必須で既定値なし**にし、宣言を返す関数の `locked` 属性に残す。`build_parser` が `require_declared` で全 verb を検査し、宣言の無い verb は組み立てを拒否する。これにより、拡張点 `extra_registrars`（#696 で足した、別モジュールの verb を登録する口）の登録 verb がロックを付け忘れても静かに動くことはない。
- repo-root はラッパーが 1 回だけ解決して verb 実装 `func(args, repo_root)` へ渡す（出荷時は 1 回の実行で複数回解決していた）。

### `ingest-review` のロック範囲（出荷時→L-6→F-696-01）
1. 出荷時：`--issue`・次ラウンドの導出（進行ポインタの読み取り）と本文の読み取りを**ロックの外**で行ってから `writer_lock` を取っていた。並行 ingest が同じ次ラウンドを選び、後続が「単調増加」の検査で落ちうる穴があった。
2. L-6 の是正：ポインタの読み取りをロックの内側へ移した。このとき本文の読み取りまで一緒にロック内へ入れ、「代償として `--from -` の標準入力読み取りもロック内になる（フックは本文を即座に流し込むので実害は小さい）」と記録した。
3. F-696-01（real・minor）でこの判断が誤りと判明した：標準入力が閉じないと無期限に排他ロックを握り、他の `append`／`close-attempt`／`ingest-review` が全てブロックされる。フックが即座に流し込む前提は、手動実行・パイプの上流が詰まった場合に成り立たない。現状は `prepare` 段（`prepare=_read_report`）で**本文の読み取りだけをロックの前**に行い、ポインタの読み取りから台帳置換まではロック内に保つ。
4. 副次効果（F-696-11 で是正済み）：本文が空・`--from` 不正の拒否はロック前に起きるので `tmp/_karte/` を作らないが、進行ポインタ由来の拒否（無い・破損・食い違い）と `--issue abc`・`--round ²` のような引数由来の拒否は、補完と検証が `func`（ロック内）にあったためロック用ファイルとディレクトリを作っていた。拒否の優先順位も出荷時の issue→round→本文から repo-root→本文→issue→round に変わり、ポインタが壊れていても標準入力を先に読み切っていた。
5. F-696-11 の是正：`prepare`（ロック前）で `ingest_target`（issue→round）→本文の順に検証する（`cli._prepare_ingest`）。引数・ポインタ・本文由来の拒否はロックを取る前に起きるので何も作らず、優先順位も出荷時に戻る。ポインタ由来の値は並行 ingest が先に進めうるので**ロック内で読み直した値だけを使う**（ロック前の値は検証用に捨てる）。このためポインタを2回読む（読取のみ・副作用なし）。**何も作らずに拒否できるのは `prepare` 段で拒否できる範囲に限る**。ロックを取ったあとの拒否は、新規 repo でも `tmp/_karte/` と `.writer.lock` を残す（台帳・ポインタは書かない）。対象は、ロック前の検証を通ったあとにポインタが変わりロック内の読み直しで拒否された競合、レポート内容の検証（harm 欄欠落・ID 重複・再発番等）、台帳との突き合わせ（前ラウンド未解消の不在等）。当初ここを「競合時だけ」と書いていたのは誤りで、PR #696 第4回独立レビュー F-7 で実測に合わせて訂正した（`test_karte_pointer_completion.py` の `TestRefusalInsideTheLockLeavesTheLockFile` が固定）。

### 入力のエンコーディング（F-696-13）
`UnicodeDecodeError`／`UnicodeEncodeError` は `ValueError` 系で、`verb_boundary._REFUSALS` の5種に含まれず終了コード契約 {0,2,3,4} の外へ漏れる（出荷時の origin/main でも同じ漏れ）。読み側は `path_io.read_text`（レポート本文・台帳・進行ポインタ・`--diff-file`）と `utf8_text.read_stream_text`（標準入力）で、書き側は `path_io` の書込み前に `utf8_text.require_utf8_encodable` で、いずれも拒否例外に畳む。C ロケールでは標準入力が `surrogateescape` で読まれて不正バイトが lone surrogate として検証を通り、台帳への書込みで初めて失敗するため、読んだ直後に UTF-8 へ戻せることも確かめる。`git diff` の出力復号は `errors="replace"` で、`.git` の読取も `replace` のため漏れない。

### `fail_close` の戻り値の型（PR #696 第4回 T11）
`fail_close` は注釈が無く、装飾後の verb の型が推論されず元の `func(args, repo_root[, prepared])` の署名に見えていた。pyright が `cli.cmd_*(args)` の呼び出しに「`repo_root` が無い」と報告し、`wrapper.locked` の代入も属性未定義になっていた（実行時は正しい）。`Verb` Protocol（`__call__(args) -> int` と `locked: bool` と `__name__`）を戻り値の型にして、`cast` 1 箇所でラッパーに宣言を付ける。呼び出し側の型は `cmd(args) -> int` に揃い、`.locked` の参照も型検査を通る。

### `prepare` 段の契約
`prepare(args, repo_root)` はロックの外で 1 回だけ呼ばれ、戻り値が `func(args, repo_root, prepared)` の第 3 引数になる。`prepare` を渡さない verb の署名は `func(args, repo_root)` のまま。

### `--round` の補完
`--round` 省略時の補完は `ingest-review`（ポインタ＋1）と `check`（そのまま）で1つの `pointer_completion.resolve_round`（当時は `cli._pointer_round`、F-696-26 までは `pointer_completion.pointer_round`）を共有する。ポインタが `round` を欠く・別 Issue を指す場合は推測せず fail-close（旧 `_resolve_ingest_round`／`_resolve_check_round` は同一ブロックの複製だった）。

### 整数変換の入口一本化（F-696-21・scope out の既存漏れを本 PR で閉じた）
`parse_int` が閉じた `ValueError` 漏れ（非 ASCII 数字・変換上限 4300 桁超）と同型の経路が、`validate_issue`・`_require_int_list`・`resolved_round`・`parse_finding_id`・カルテ見出し（`# Karte: issue-N`／`Attempt N`／`Result N`）に残っていた（origin/main にもある。終了コード契約 {0,2,3,4} の外＝traceback の 1）。変換は `int_args.ascii_int_or_none`（`None` を返す）と `require_ascii_int`（呼び出し側が渡した拒否例外を投げる）に集約し、各所は自分の拒否例外（`KartePathError`／`KarteFormatError`／`KarteUsageError`）を渡して終了コード 4 に収める。オーナー決定で scope out を本 PR で直した（値引き・先送りしない）。

### 桁数の上限を 18 桁にした理由（第5回 R5-01）
当初の `ascii_int_or_none` は `int()` の変換上限（4300 桁）を超える入力だけを拒否していた。4300 桁ちょうどの `--round` は受理され、次の自動補完（ポインタの `round` ＋1）で 4301 桁になり、`str()` が `ValueError`（traceback の終了コード 1）になった。選択肢は (a) 上限を 4300 桁より十分小さく置く、(b) `+ 1` の直後に再検査する、の2つで、(b) だけでは `+ 1` する他の箇所（finding の連番・Attempt 番号）を個別に塞ぐことになる。(a) を採り、`int_args.MAX_DIGITS = 18`（64bit に収まる桁数）で入口を一本化した。ただし 18 桁ちょうどの値に `+ 1` すれば 19 桁になり、書いた台帳が以後読めなくなる——`+ 1` して**書く**3か所（`ingest_target` の補完・`format_finding_id`・`next_attempt_number`）は足した結果も同じ上限で検査する。進行ポインタの `round` を `render` の見出しへ出す経路は検証が漏れていたため、`append` の補完と同じ `recorded_round` に寄せた（subagent の `additionalContext` へ注入される本文に検証前の値を出さない）。消費者 `issue_start/subagent_hooks.py` は `render` を呼ぶ前に自分で `round` を「1 以上の整数」と検査して `read_active_pointer` で弾くため、`render` が不正な `round` で `4` を返しても注入が欠けるのは、その検査を通る 19 桁以上の整数だけである。

### `--round` 補完の戻り値（F-696-26）
`pointer_round(args, repo_root, issue, no_round_hint: str) -> int` は、エラー文言の断片を呼び出し側から文字列で受け取り、さらに `ingest_target` が「`--round` が明示されたか」の判定を関数の内と外で二重に持っていた。`resolve_round(args, repo_root, issue, missing_hint: MissingRoundHint) -> ResolvedRound`（`karte/round_resolution.py`：案内の列挙と結果の dataclass＝データのみ）に改め、明示/補完の別（`explicit`）を戻り値で一度だけ返す。`ingest_target` は `explicit` だけを見て +1 を決める。上段が再利用するときも、案内は列挙値で選び、文言を組み立てない。

## `karte/model.py` の解析責務分割（Issue #746・K-01・親 #745）

`karte/model.py`（1297 行・連続コメント違反 10 件）から解析・検証責務を新モジュールへ移した際、連続コメント 3 行以内（Issue #539）に縮めたコード側の説明を、移設元の文言のまま保管する。公開名は `karte.model` から従来どおり再エクスポートしている（挙動比較は `tests/unit/test_karte_model_compat.py`）。

| 新モジュール | 移設元（`karte/model.py`） |
|---|---|
| `format_error.py` | `KarteFormatError` |
| `vocabulary.py` | 列挙値・セクション名・書式正規表現 |
| `value_codec.py` | `parse_value`/`format_value`/`check_scalar`/`check_list`/`normalize_locus` |
| `finding_id.py` | `format_finding_id`/`parse_finding_id` |
| `block_parser.py` | `Block`/`parse_blocks` |
| `block_fields.py` | `_require*`/`_optional*`（公開名 `require*`/`optional*` へ改名） |
| `disposition.py` | `Disposition`/`parse_disposition` |
| `harm_detail_lint.py` | `harm_detail` 内容 lint |
| `field_validators.py` | `validate_*` |
| `review_finding.py`/`review_block.py`/`review_report.py` | `ReviewFinding`/`parse_review`（ブロック変換と報告集約を分離） |

### `karte/vocabulary.py`：語彙定義の移設元コメント

`change_kind`（`CHANGE_KINDS`）：

```text
``change_kind``＝是正の変更種別。類似判定の**宣言信号**（:mod:`karte.similarity`）が
``root_cause`` 一致に加えて見る軸であり、飽和検知（同じアプローチの無駄連打の停止）の入力。

``doc``（Issue #503 観測2・2026-09-09 追加）＝**文書だけを変更する是正**
（README・`docs/**`・エージェント定義本文・docstring のみ。コードの挙動を変えない）。
追加前は文書のみのラウンドで実態に合う値が無く、是正担当が已むなく ``config`` を選んだ
（Issue #493 の是正ラウンド2 で実測）。実態と違う値が入ると (a) 後から読む者が
「設定を変えた是正」と誤読し、(b) 飽和判定が**別の ``config`` 変更との距離を実態より近く**
算出する——是正ラウンドの相当数は文書のみの変更なので、再発頻度は低くない。

**既存カルテの ``config`` 記録は遡って読み替えない**（Issue #503・本 PR で確定）。
台帳は追記のみ（本モジュール docstring「追記規律」）で、書かれた Attempt ブロックは
どの verb も書き換えないから、過去の ``config`` は ``config`` のまま残る。移行スクリプトも
読み替えマップも持たない。理由は 2 つ——
  * 遡って書き換えると append-only の不変条件（＝改ざん防止の前提）を自ら破ることになる。
  * 「当時どう申告したか」は飽和判定が実際に使った入力であり、後から書き換えると
    過去ラウンドの判定結果を再現できなくなる（監査可能性の喪失）。
**飽和判定への影響**は「新しい ``doc`` の Attempt は、過去の ``config`` の Attempt と
``change_kind`` 経由では類似と判定されなくなる」ことに限られる（``root_cause`` 一致＋
``targets`` 交差、あるいは実測 touched-set 一致の経路は従来どおり効く）。すなわち
語彙追加は飽和判定を**緩める方向**に働きうるが、それは「実態が違う変更を同種と数えていた」
過大計上の解消であって、検知力の意図的な低下ではない。
```

`SEVERITIES`：

```text
指摘の優先度（``harm`` とは独立の軸。``harm: none`` でも ``severity: major`` はあり得る）。
```

`scope`（`SCOPES`）：

```text
``scope``（Issue #495）＝レビューアの**申告**としての当該 PR スコープ内/外。
**免除力を持たない**——``scope: out`` でも ``harm`` の判定・台帳への記録・verdict の
ゲートはまったく同じに掛かる。スコープ外指摘を別経路（チャットでの列挙）へ逃がすと、
実害判定もカルテ記録も verdict も一度に迂回でき、実害ありの指摘が未処置のまま
clean を通過した（PR #490 → Issue #493 の流出経路）。`scope` は監査材料として残すだけ。
```

`DEFAULT_SCOPE`（移行措置）：

```text
移行措置（Issue #495・互換性）: ``scope`` を持たない**既存カルテ**は ``in`` として読む。
`tmp/` は版管理外だが、進行中の Issue の台帳が読めなくなると是正ループが止まるため。
**新規の ``ingest-review`` では必須**（:func:`parse_review` は既定へ倒さず拒否する）。
```

`disposition`（`DISPOSITIONS`）：

```text
``disposition``（Issue #495）＝``harm: real`` の指摘に対するオーナー判断の記録。
  ``fix-here`` … 当該 PR で直す（直るまで clean を妨げる）。
  ``deferred``  … 別 Issue へ申し送る（``deferred_to`` 必須）。
  ``waived``    … オーナーが明示的に処置不要を許可（``waived_by``/``waived_reason`` 必須。
                  CLAUDE.md「『対応不要』を AI が独断で書かない」に対する**記録の強制**で、
                  許可者本人であることの機械検証ではない＝:func:`parse_disposition` の
                  「既知の限界」）。
```

`CLEARING_DISPOSITIONS`：

```text
「当該 PR では処置しない」とオーナーが決めた disposition（Issue #495 の二層設計）。
``status`` は ``open`` のまま残す——``deferred`` を ``resolved`` にすると
「別 Issue へ移したと書くだけで指摘が消える」経路ができ、本 Issue が塞ぐ穴が形を変えて再発する。

**この 2 定数を参照してよいのは :attr:`Finding.cleared_by_disposition` だけ**
（Issue #503）。判定経路ごとに個別実装すると同じ取りこぼしが経路の数だけ生まれる
——実際、Issue #495 の実装が除外を verdict 算出にしか入れなかったため、``check`` の
診断網羅要求（観測1）と無進捗検知（観測3）が同じ穴を別々に開けていた。以後
``deferred``/``waived`` を参照する判定を足すときは、この述語を経由させれば自動的に
同じ規則が効く。
```

`CLEARING_HARM`：

```text
**解除力は ``harm: real`` の finding にだけ与える**（オーナー確定・2026-09-07・PR #496 F-495-01）。
``disposition`` はそもそも「``harm: real`` に対するオーナー判断の記録」として導入した
（:data:`DISPOSITIONS` の説明・Issue #495「提案挙動」3〜5 はいずれも ``harm: real`` が主語）。
解除力を harm の値によらず与えると、``harm: none`` の未解消 finding に ``deferred`` と
適当な Issue 番号を 2 行書くだけで verdict が ``no-harm-only`` から ``clean`` へ変わり、
「未解消がすべて ``none`` になったらオーナーへ打ち上げる」既存の STOP
（`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」）を AI が単独で
消せてしまう——本 Issue が塞いだ「ラベルを書くだけで clean を通す」経路と同型のものを
``harm: none`` 側に新設することになる。
``harm: none`` に ``disposition`` を書くこと自体は拒否しない（申し送り先の記録は残せる）。
記録は残るが verdict は動かない、という非対称でよい。
```

`DEFERRED_TO_RE`：

```text
``deferred_to``（Issue #495）は**行き先を機械的に解決できる形**だけを受ける。
「別 Issue で対応」のような散文を許すと、申し送りの宛先が不明のまま clean を通せてしまい、
`deferred` を必須化した目的（リンク無しの申し送りを作らない）が達成できない。
```

`FORBIDDEN_VALUE_CHARS`/`FORBIDDEN_LIST_ITEM_CHARS`：

```text
台帳の値に持ち込めない文字（1行 key: value ＋ `[a, b]` 記法を壊すため）。
```

### `karte/value_codec.py`：`normalize_locus` の docstring（全文）

```text
    """``locus`` をリストへ正規化する（スカラ 1 件でもリストでも受ける）。

    レビューアが 1 箇所しか書かないときに ``[...]`` を強制すると書き味が悪いのでスカラを許し、
    台帳側は常にリストで持つ（表示・比較の分岐を 1 箇所に閉じる）。空は空リスト＝任意キー。

    **スカラ経路もリスト要素と同じ文字検査を通す**（:data:`FORBIDDEN_LIST_ITEM_CHARS`）。
    ここを緩めると、角括弧を省いて ``locus: a.md::x, b.toml::x`` と書いたときに 1 要素として
    受理され、:func:`format_value` が ``[a.md::x, b.toml::x]`` と書き出すので、**台帳を読み直した
    時点で 2 要素へ静かに割れる**。:func:`is_same_finding` は locus の交差で再発番を判定するため、
    レポート側（1 要素）と台帳側（2 要素）で照合面がズレ、**同一指摘の再発番を見逃す**方向に効く
    ——locus を複数化した目的そのものを裏切るので、fail-close で拒否する。
    """
```

### `karte/block_parser.py`：`parse_blocks` の docstring と inline コメント（全文）

```text
    """``## Section`` / ``### Title`` ＋ ``key: value`` 行の決定論パーサ。

    解釈できない行が 1 行でもあれば :class:`KarteFormatError`（fail-close）。

    ``allow_preamble``
        最初の ``### `` 見出しより**前**の自由記述行（レポート冒頭のタイトル・総括）を
        読み飛ばす。レビューレポート（レビューアが書く入力）専用の緩和で、カルテ本体
        （機械が書き機械が読む正本）は既定どおり 1 行でも解釈できなければ拒否する。
        1 件目のブロックに入った後は緩和しない——要約の折り返し行を黙って捨てると
        指摘の内容が欠落するため、そこは fail-close のままにする。
    """
...
        if allow_preamble and not seen_block and not matched:
            continue  # 1 件目の `### ` より前の自由文だけを無視する（レビューレポート限定）。
            # `key: value` 形の行は preamble でも黙って捨てず拒否する（K-10：無言の欠落防止）。
```

### `karte/block_fields.py`：`_optional_enum` の docstring（全文）

```text
    """任意キーを列挙で検証する（未記載・空は ``default``・綴り違いは fail-close）。

    「無い」（＝既定へ倒してよい）と「値が不正」（＝倒すと意味が変わる）を分ける。
    :func:`_optional_status` と同じ考え方で、綴り間違いを黙って既定へ落とさない。
    """
```

### `karte/disposition.py`：コメントと docstring（全文）

`Disposition` の docstring：

```text
    """``harm: real`` の指摘に対するオーナー判断の記録（Issue #495）。

    ``kind`` が空文字＝**未決定**。未決定のまま未解消で残る ``harm: real`` の finding が
    1 件でもある間、``status`` の verdict は ``clean`` を返さない（:mod:`karte.cli`）。
    """
```

`DISPOSITION_REQUIRED_KEYS` のコメント：

```text
``disposition`` の値ごとに**必須**の付随キーと、**書いてはならない**付随キー。
片方だけを検査すると「別の kind の付随キーが残ったまま」の台帳を許してしまい、
後から読んだ側が古い申し送り先を現行の処置方針と誤読する（PR2：機械判定できる所は機械で）。
```

`parse_disposition` の docstring：

```text
    """``disposition`` とその付随キーを読む（未記載は未決定・不整合は fail-close）。

    * ``deferred`` は ``deferred_to``（行き先 Issue）を必須にする——リンク無しの申し送りは
      行き先不明になり、「別 Issue へ回す」と書くだけで指摘を消せる経路になる。
    * ``waived`` は ``waived_by`` と ``waived_reason`` を必須にする。これは
      `.claude/rules/03-operational.md`「『対応不要』を AI が独断で書かない」に対する
      **記録の強制**で、誰が許可したかと理由が無い処置不要を台帳へ入れられなくする。
    * 宣言した ``disposition`` に属さない付随キーは空でなければならない（取り違え防止）。

    **既知の限界（オーナー判断そのものは機械強制していない・PR #496 F-495-04）**:
    ``waived_by``/``waived_reason`` は自由記述のスカラであり、**書いた主体がオーナー本人か
    どうかを機械側は区別しない**。``ingest-review`` を実行するのは主文脈（AI）であり、
    `.claude/hooks/agent-command-gate.sh` の ``KARTE_ALLOWED_SUBCOMMANDS`` が締め出して
    いるのは是正当事者ロールだけである。``deferred_to`` も :data:`DEFERRED_TO_RE` の
    **形式**だけを検査し、指す Issue が実在するかは検証しない。したがってここで強制して
    いるのは**記録**であって**オーナー判断**ではない——多層防御の一枚であって sandbox では
    ない（本モジュール docstring「改ざん防止の機械的裏付けと既知の限界」と同じ制約＝
    Issue #129）。運用規律（`.claude/rules/03-operational.md`）との併用が前提。
    """
```

### `karte/harm_detail_lint.py`：Issue #511 の設計コメント（全文）

```text
--- harm_detail の内容 lint（Issue #511） -------------------------------------

``harm_detail`` は**放置したときに何が壊れるか**だけを書く欄である
（`.ai/agents/pr-reviewer.md` の finding 書式定義）。ところが実運用では
**処置方針（disposition）と判断経緯**が同じ欄へ書かれ、そのまま台帳へ入った
（Issue #511「実際に発生した混入」＝PR #509 の F-431-07「…本PRの差分範囲外の既存行に
おける既存パターンで、新規追加テストによる新規発生ではない」／F-431-02
「…（オーナー確認済み・…で fix-here）」）。

これは書き手の不注意だけが原因ではない——**契約が誤指示を出し、機械検査がそれを通す**
という構造に支えられていた（`.ai/agents/pr-reviewer.md` が「別 Issue にすべきだと
考える場合も…harm_detail と expected に書いて返す」と指示する一方、同じ節が
「処置方針は書かない。オーナー専権」と述べていた自己矛盾）。契約側は Issue #511 で
是正済みで、本 lint はその機械側の半分である。

**なぜ実害があるか**：処置方針が ``harm_detail`` に混ざると、(a) オーナーが決める前に
「対応不要」等の結論が台帳へ既成事実として載り、(b) ``disposition``/``waived_reason``
という**そのための欄**が空のまま verdict ゲートを素通りする見かけになり、
(c) 後から読む者が「実害」と「処置方針」を区別できなくなる。

**判定の性質**：決定論的な部分文字列一致（形態素解析器のような外部依存は持てない
＝標準ライブラリのみの制約）。照合前に ASCII 大小文字を畳み、空白を除去するので
「別 Issue」と「別Issue」は同一視される。取りこぼし（fail-open）はありうるが、
観測された混入の型は確実に捕まえる。誤検出は :mod:`karte.allowlist` へ
**理由付きで**登録して抑制する（消さず理由を残す運用）。

処置方針（disposition）の語彙。**オーナー専権**の判断であり、レビュー担当も
是正担当も ``harm_detail`` に書いてはならない（どこで直すべきかという見立ては
そもそもどの欄にも書かず、決まったオーナー判断だけが
``disposition``/``deferred_to``/``waived_reason`` に載る）。
```

`PROCESS_TERMS` のコメント：

```text
判断経緯・プロセスの語彙。「なぜそう判断したか」であって「放置すると何が壊れるか」
ではない。観測された混入（Issue #511）はすべてこの型だった。
```

`normalize_for_term_match`/`check_harm_detail` の docstring：

```text
    """語彙照合用の正規化（ASCII 大小文字を畳み、空白をすべて除去する）。

    :func:`normalize_text`（再発番判定用）とは別物で、**記号を落とさない**
    ——``fix-here`` のハイフンを落とすと ``fix here`` 以外の無関係な並びまで
    一致しうるため。空白の除去は「別 Issue」「別Issue」の表記ゆれを吸収する。
    """

    """``harm_detail`` の内容 lint（fail-close・Issue #511）。

    :data:`HARM_DETAIL_FORBIDDEN_TERMS` のいずれかを含み、かつ
    :mod:`karte.allowlist` に理由付きで登録されていなければ
    :class:`KarteFormatError` を送出する。呼び出し元（:func:`parse_review`）が
    他の検証エラーと同じ列に集約するので、取り込みは**レポート全体**として拒否される
    （1 件だけ黙って落とすと、指摘が記録されないまま消える）。
```

### `karte/review_block.py`：`_optional_status`/`_parse_distinct_from` の docstring（全文）

```text
    """レビューレポートの任意キー ``status``（既定 ``open``）を読む（K-06）。

    ``resolved`` と**書いたときだけ**解消として扱う。値の綴り間違いは既定へ倒さず
    :class:`KarteFormatError`（fail-close）——「resolve」等の誤記を黙って ``open`` に
    落とすと、レビューアの解消宣言が無言で失われる。
    """

    """任意キー ``distinct_from``（再発番判定のペア限定エスケープハッチ・K-05）を読む。

    スカラ（``distinct_from: F-307-01``）とリスト（``distinct_from: [F-307-01, F-307-02]``）の
    両方を受ける。形式違反・対象 issue 違いはここで拒否し、**台帳に実在するか**は
    台帳を持つ CLI 側で検査する（ここは書式の責務だけを負う）。
    """
```

### `karte/review_report.py`：`parse_review` の docstring（全文）

```text
    """レビューレポートをパースする（``### F-<issue>-<seq>`` か ``### new`` のブロック列）。

    ``harm`` 欄の欠落・不正な ID 形式・要約欠落はすべて集めて 1 度に報告する
    （1 件ずつ往復させない）。1 件でもあれば :class:`KarteFormatError`（fail-close）。

    レポート冒頭の前書き（``# レビュー結果`` とその下の総括文）は無視する。ブロックが
    1 件も無いときは「解釈できない行」ではなく **finding ブロックが無い** と報告する
    ——書式違反の指摘より「取り込むものが無い」ことの方が呼び出し側の処置に直結する。

    必須キー: ``harm`` / ``harm_detail`` / ``severity`` / ``scope`` / ``summary`` /
    ``evidence`` / ``expected`` / ``recheck``（``locus`` は任意）。``scope`` は Issue #495 で
    必須化した——スコープ外と分類された指摘が finding の列に入らず、実害判定・カルテ記録・
    verdict のすべてを迂回して ``clean`` を通過した（PR #490 → Issue #493）。任意キーにすると
    書かれないので、欠落は取り込みごと拒否する（``harm`` 欠落と同じ扱い）。
    **台帳（:func:`parse`）側では任意**＝``scope`` を持たない既存カルテを読むための移行措置。
    ``severity`` / ``expected`` / ``recheck`` は
    Issue #341 F-341-01 で必須化した——``pr-reviewer`` の出力契約が必須と宣言している一方で
    台帳が持っておらず、2 ラウンド目以降に ``expected``（解消条件）と ``recheck``（再検証手順）を
    復元できなかった。``evidence`` は同レビューの書式 feedback で追加——「そう言える根拠」を
    ``harm_detail``（実害の内容）に混ぜると、再レビュー側が実体確認の有無を検証できない。

    ``harm_detail`` は**非空であることに加えて内容も検査する**（Issue #511・
    :func:`check_harm_detail`）。処置方針・判断経緯の語彙を含むレポートは取り込みごと
    拒否する。**この lint は新規の ``ingest-review`` にだけ掛かり**、既存カルテを読む
    :func:`parse` 側には掛けない（``tmp/`` は版管理外だが、進行中の Issue の台帳が
    読めなくなると是正ループが止まる——``scope`` 必須化と同じ移行方針）。

    ``locus`` は**スカラでもリストでも書ける**（:func:`normalize_locus` が正規化する）。
    同じ欠陥が対称ミラーの複数ファイルに出るときは ``locus: [a, b]`` と書いて **1 指摘のまま**
    複数箇所を指す——箇所ごとに finding を割ると未解消件数が水増しされ、``status`` の
    「同一 finding が N ラウンド連続未解消」判定まで歪む。

    任意キー:
      ``status``
          ``open``（既定）／``resolved``。**解消は明示宣言でのみ成立する**（K-06）。
          再掲されなかった finding を「不在＝解消」と見なす旧仕様は、部分的なレポートを
          1 回取り込むだけで ``harm: real`` の指摘が消える fail-open だったため廃止した。
      ``distinct_from``
          ``F-<issue>-<seq>``（``[a, b]`` で複数可）。再発番判定（:func:`is_same_finding`）の
          **偽陽性に対する明示的なエスケープハッチ**で、ここに名指しした相手との**ペアに限って**
          判定を無効化する（K-05）。判定そのもの・閾値は動かさない。ID の実在検査は台帳を持つ
          CLI 側（``cmd_ingest_review``）で行う。
      ``disposition`` / ``deferred_to`` / ``waived_by`` / ``waived_reason``
          オーナー判断の記録（Issue #495・詳細は :func:`parse_disposition`）。
          **レビューアが埋める欄ではない**——取り込み時点で未決定なのが通常で、
          未決定の ``harm: real`` が未解消で残る間は ``status`` の verdict が ``clean`` を
          返さない。決まった処置方針を主文脈が次ラウンドのレポートに書いて取り込む。
    """
```

`harm` 検証を先に済ませる理由（inline コメント）：

```text
``harm`` の検証を先に済ませてから内容 lint を掛ける（欄の欠落という
より基本的な違反を、内容違反が覆い隠さないようにするため）。
```

### `karte/model.py` 側に残した `Finding`/`parse` の field コメント（移設元の全文）

```text
``locus`` は**リスト**（Issue #341 レビュー feedback）。同じ欠陥が対称ミラー
（`.claude/` ↔ `.codex/` 等）の複数ファイルに出る本リポジトリでは、1 箇所しか持てないと
**同一欠陥が複数 finding に分裂**し、未解消件数が水増しされて `status` の
「同一 finding が N ラウンド連続未解消」判定まで歪む。1 指摘＝1 欠陥のまま複数箇所を指せる。

``evidence``＝そう言える**根拠**（読んだファイル/行・実行したコマンドと結果）。
``harm_detail``（実害の内容）と混ざると、再レビュー側が「本当に実体で確認したのか」を
検証できない。`pr-reviewer` の「指摘の根拠は必ず実体で確認する」を書式側で要求する。

``expected`` / ``recheck`` は**ラウンドをまたぐ**情報なので台帳に持つ（Issue #341 F-341-01）。
``expected``＝どうなっていれば解消か（``issue-fixer`` の Step 1 診断の入力契約）。
``recheck``＝次ラウンドで何を実行して解消を判定するか（再レビュー側の判定根拠）。
ここに持たないと 2 ラウンド目以降に台帳から復元できず、是正も再検証も
「レビューアのチャット発言を覚えている」ことに依存してしまう。

``scope``（Issue #495）＝レビューアの申告（当該 PR のスコープ内/外）。**免除力を持たない**。
既定は :data:`DEFAULT_SCOPE`＝``scope`` を持たない既存カルテの移行措置でもある。

移行措置（Issue #495）: ``scope`` は**台帳側では任意**で、欠落は :data:`DEFAULT_SCOPE`
として読む。`tmp/_karte/` に実在する既存カルテ（本 Issue 起票時点で 19 件）を
読めなくすると進行中の是正ループが止まるため。新規取り込み（:func:`parse_review`）
側では必須にしてあるので、以後書かれるカルテには必ず ``scope`` が載る。
```

## K-02 分割計画（#747）

Issue #747（親 #745・K-02・下段 #796＝K-01）の分割を実装した。設計者＝Claude Code (AI)。K-01 の節は変更しない。

### 着手時点の実測
- L1 head（53d4e7a8）で `python3 -m maintainability_lint check` は `accepted_debt=62`（全体）。`karte/model.py` の登録は `module-over-100-lines`（635行）の1件のみで、`comment-over-3-lines`・dataclass 同居の登録は 0。
- Issue #747 本文の「初期11件」は K-01 前の件数で、現在値と食い違う。実装 PR では着手時と完了時の件数を再計測して記す。
- 635行の内訳は、モジュール docstring（約110行・「追記規律」「改ざん防止の機械的裏付けと既知の限界」等）、import（約60行）、dataclass 4つ、解析・類似・描画の関数群。**docstring を残すだけで入口が100行を超える**ため、分割だけでは足りず docstring の移設が要る。

### 新規モジュール（各100行以内・依存は上から下の一方向）
| 順 | モジュール | 内容（移設元 `karte/model.py`） | 備考 |
|---|---|---|---|
| 0 | `vocabulary.py`（既存へ追記） | `FORMAT_VERSION` | 35行の既存に1行足すだけ |
| 1 | `finding_record.py` | `Finding`（dataclass＋プロパティ） | dataclass のみ。長い docstring は本節の下へ逐語移設し、本体は短い docstring にして100行に収める |
| 1 | `attempt_record.py` | `Attempt`, `Result` | dataclass のみ |
| 1 | `karte_record.py` | `Karte`（dataclass＋参照メソッド）, `new_karte` | 具体ロジック class は持たない |
| 2 | `finding_dedup.py` | `normalize_text`, `shingles`, `_jaccard`, `is_same_finding`, `SHINGLE_SIZE`, `DUPLICATE_SIMILARITY_THRESHOLD` | 既存 `similarity.py`（Attempt 類似）とは別物。名前で区別 |
| 2 | `block_records.py` | `_finding_from_block`, `_attempt_from_block`, `_result_from_block` | 先頭の `_` は維持（互換） |
| 3 | `karte_parse.py` | `parse` | `block_records` と `karte_record` に依存 |
| 3 | `karte_render.py` | `_emit`, `render_finding`, `render_attempt`, `render_result`, `dumps` | `finding_record`/`value_codec` に依存 |
| 4 | `model.py`（公開互換入口） | docstring 約20行＋再エクスポートのみ | 100行以内。ロジック・dataclass を持たない |

- どのモジュールも `karte.model` を import しない（循環を作らない）。既存 K-01 モジュールにも `model` を import するものは無い想定で、実装時に grep で確認する。
- `finding_record.py` が100行に収まらない場合も、判定述語（`cleared_by_disposition` 等）を別モジュールへ分けず、**docstring の移設で縮める**ことを先に試す。分けると述語の単一点性（Issue #503）を崩すため。

### `karte.model` の再エクスポート名（漏れ防止）
実装時に `vars(karte.model)` から機械的に列挙し、**`dataclass`/`field`/`re`/`unicodedata`/`annotations` 以外の全名**を再エクスポートする。着手時の実測は次のとおり。
- 型: `Attempt Block Disposition Finding Karte KarteFormatError Result ReviewFinding`
- 関数: `check_harm_detail check_list check_scalar dumps find_harm_detail_terms format_finding_id format_value is_same_finding matched_int new_karte normalize_for_term_match normalize_locus normalize_text parse parse_blocks parse_disposition parse_finding_id parse_review parse_value render_attempt render_finding render_result require_ascii_int shingles validate_change_kind validate_finding_ids validate_slug validate_targets`
- 非公開名（互換のため維持）: `_attempt_from_block _emit _finding_from_block _jaccard _optional_enum _require_enum _require_int_list _require_nonempty _result_from_block`
- 定数: `ATTEMPT_TITLE_RE CHANGE_KINDS CLEARING_DISPOSITIONS CLEARING_HARM DEFAULT_SCOPE DEFERRED_TO_RE DISPOSITIONS DISPOSITION_ALL_KEYS DISPOSITION_REQUIRED_KEYS DISPOSITION_TERMS DISTINCT_FROM_KEY DOC_HEADER_RE DUPLICATE_SIMILARITY_THRESHOLD FINDING_ID_RE FINDING_STATUSES FORBIDDEN_LIST_ITEM_CHARS FORBIDDEN_VALUE_CHARS FORMAT_VERSION HARM_DETAIL_FORBIDDEN_TERMS HARM_LEVELS KEY_RE NEW_FINDING_TITLES OUTCOMES PROCESS_TERMS RESULT_TITLE_RE SCOPES SECTION_ATTEMPTS SECTION_FINDINGS SEVERITIES SHINGLE_SIZE SLUG_RE`
- import 行の数がそのままでは入口が100行を超えるため、1行に複数名を並べる（1名1行にしない）。`__all__` は足さない（`import *` の挙動を変えないため）。
- `Finding` 等の `__module__` は `karte.finding_record` 等に変わる。`pickle` 等で `__module__` に依存する箇所が無いことを grep で確認し、あれば互換を再検討する。

### モジュール docstring の移設（100行制約の要点）
- 「追記規律」「改ざん防止の機械的裏付けと既知の限界」等の約110行は、本ファイルへ**逐語で**移設する（K-01 と同じ。移設前に必ず保全してから削る）。
- 他文書が `karte/model.py` の「改ざん防止の機械的裏付けと既知の限界」を名指ししている（`karte/README.md`・`feedback_ledger/README.md`。`.claude/rules/05-skills-agents.md` も `karte/model.py` を名指しする記述がある）。**参照切れを避けるため、入口の docstring に同名の見出し＋要約数行を残し、全文への参照（本ファイルの節）を付ける**。`.claude/rules/*.md` は governance 正本集合に入るため、そこを書き換えるとドリフト検査が動く。書き換えずに済む方針を採る。
- 連続4行以上の行コメントは作らない（docstring は対象外だが、dataclass 内の `#` コメントは3行以内。`Finding` の現状は3行以内）。

### 互換性・同値性の守り方
- 既存 `tests/unit/test_karte_model_compat.py` と `tests/fixtures/karte/model_parse_golden.json` が、parse の有効/無効入力の結果（成功は sha256、失敗は例外クラス名とメッセージ）と公開名の importability を固定している。**golden は書き換えない**（書き換えると分割前との同値性証拠が失われる）。
- 足りない検出力の候補（追加はテストのみ。ソースは変えない）。要否は実装ラウンドで判断する。
  1. **parse→dumps→parse の同値性**：VALID と各 `karte_extras()` について `parse(dumps(parse(x)))` が `parse(x)` と dataclass として等しいこと。現 golden が `dumps` 出力を固定しているか未確認で、固定していなければ `dumps` の出力固定が欠ける。
  2. **render 系の直接入力**：`render_finding/attempt/result` を、locus 複数・空値・`resolved_round`・`rounds` 空の Finding 等で直接呼ぶ入力を `helper_calls()` に足す。
  3. **`is_same_finding`/`shingles`/`normalize_text`**：境界（空・全角・閾値ちょうど 0.6・locus 交差のみ一致）の入力が `helper_calls()` にあるか確認し、無ければ追加。
  4. **`Finding` の述語**：`cleared_by_disposition`/`needs_remediation`/`needs_disposition`/`max_consecutive_rounds` の真偽表（harm × disposition × status）。単一点の規則（Issue #503）が移設で壊れないことを固定する。
  5. `karte.model` が新モジュールを import し、新モジュールが `karte.model` を import しないこと（循環の検査）。
- 公開 API・CLI の出力・終了コード・書込副作用は変えない（#745 C01）。`#683`/`#614`/`#513` の動作変更を暗黙に取り込まない。

### 実装時の互換契約と実測（F-799-01・02）
- 入口 docstring は「改ざん防止の機械的裏付けと既知の限界」と `Edit(/tmp/_karte/**)` を残し、追記規律・二層保護・Bash の限界を要約する。既存の `test_the_model_docstring_documents_the_edit_deny` は変更しない。
- 公開面の維持を最優先する #745 C01 に従い、repo 内に外部参照のない非公開名9個と `matched_int`・`require_ascii_int` も含めた76名を `REQUIRED_NAMES` で固定する。4変異（閾値・shingle 長・解除条件・是正条件）を追加テストで検出する。
- 分割前の実測では、`mutations(VALID)` の成功入力4件で往復等価性が成立しない。`diagnosis` と `note` のリスト入力は文字列化後の再解析で引用符が増える。動作を変更せず、この4件は分割前の実測値を固定し、それ以外の成功入力の往復等価性を検査する。
- 実装後の物理行数: `vocabulary.py` 37、`finding_record.py` 70、`attempt_record.py` 29、`karte_record.py` 70、`finding_dedup.py` 48、`block_records.py` 88、`karte_parse.py` 62、`karte_render.py` 72、`model.py` 78。
- `python3 -m maintainability_lint check` は `violations=1 accepted_debt=61`。違反は短縮後の `karte/model.py` に残る stale-baseline のみで、新規モジュールの違反はない。baseline の更新は呼び出し元が行う。

### baseline を 0 にする手順
1. 実装・docstring 移設後、`python3 -m maintainability_lint check` を実行する。新規モジュールに違反が出たら分割をやり直す（除外・例外の追加は禁止）。
2. baseline は手で編集しない。`python3 -m maintainability_lint baseline` は現在の違反スナップショットを JSON で標準出力へ出す verb なので、その出力で `maintainability_lint/baseline.json` を更新する。差分は `karte/model.py` の登録削除だけであることを確認する（他の登録が増減していたら、下段・main の変更の取り込み結果なので理由を PR に記す）。
3. `check` の `accepted_debt` が着手時から1減ること、`karte/model.py` を含む行が 0 件であることを PR に記録する。
4. `python3 -m unittest discover -s tests/unit` を通す（資産を触った場合は `python3 -m asset_parity check` も）。

### 未確認事項（実装時に確認）
- golden の `names` に非公開名や stdlib 名が含まれるか（含まれるなら維持）。
- `Finding` が100行に収まるか。収まらなければ docstring をさらに本ファイルへ移す。

## K-02 実装で移設した docstring（#747）

旧 `karte/model.py` の説明を逐語保全する。field コメントは K-01 節にも全文を記録している。

### `module`

```python
"""カルテ書式のデータモデル・パーサ・シリアライザ・バリデータ。

書式（``tmp/_karte/issue-<N>.md``）:

    # Karte: issue-307

    ## Findings

    ### F-307-01
    status: open
    harm: real
    harm_detail: required 属性が消え必須入力が素通りする
    severity: blocker
    scope: in
    disposition: fix-here
    deferred_to:
    waived_by:
    waived_reason:
    locus: [review_system/forms.py::build_attrs, .codex/forms.toml::build_attrs]
    summary: build_attrs が既存 attrs を破棄している
    evidence: forms.py:120 を Read。attrs = {...} で辞書を作り直している
    expected: 既存 attrs を保ったまま追加分だけマージする
    recheck: required 付きフィールドを描画し required 属性が残ることを確認する
    rounds: [1, 2]
    resolved_round:

    ## Attempts

    ### Attempt 1
    round: 1
    finding_ids: [F-307-01]
    root_cause: boundfield-attrs-overwrite
    change_kind: logic
    targets: [review_system/forms.py::build_attrs]
    diagnosis: 既存 attrs を dict リテラルで作り直している

    ### Result 1
    attempt: 1
    finding_ids: [F-307-01]
    touched: [review_system/forms.py, review_system/forms.py::build_attrs]
    outcome: partial
    note: required は残ったが aria-* が欠ける

追記規律:
  * ``## Findings`` は **ID 付き指摘台帳**。``ingest-review`` だけがこのセクションを更新する
    （status/rounds の遷移を持つ台帳なので、セクション単位で書き直す）。
  * ``### Attempt k`` / ``### Result k`` は **追記のみ**。いったん書かれたブロックは
    どの verb も書き換えない。``close-attempt`` は Attempt を書き換えるのではなく
    対応する ``### Result k`` を追記する（実測 touched-set の記録先）。

改ざん防止の機械的裏付けと既知の限界（Issue #363 F-363-09）:
  * この追記規律は CLI（本モジュール・``karte/cli.py``）が既存 Attempt/Result への再実行を
    ``KarteUsageError`` で拒否することで守られる。それに加え ``.claude/settings.json`` の
    ``permissions.deny`` に ``Edit(/tmp/_karte/**)`` を登録し、
    Edit/Write 系ツールによる ``tmp/_karte/**`` への直接書込みを全ロール共通で拒否する
    （是正当事者自身を含む——権限規則はロールを区別しないので例外を作らない）。
    ``python3 -m karte`` 経由の追記はこの deny の対象外で従来どおり機能する。
    ``Edit`` 規則は ``Write`` も覆うため、``Write(/tmp/_karte/**)`` 専用のエントリは置かない
    （置くと Claude Code が "never matches" 警告を出す。経緯は
    ``.ai/rationale/karte-deny-write-entry.md``）。**台帳の保護は実際には二層で成立している**。
    非隔離で動く主文脈には ``permissions.deny`` が発火する（実測：``Edit`` エントリのみの状態で
    メインチェックアウトの ``tmp/_karte/probe-pattern-522.md`` への ``Write`` が
    "File is in a directory that is denied by your permission settings." で拒否された）。
    隔離ロール（是正・実装当事者）には worktree isolation が同じ書込みを構造的に拒否する
    （実測：隔離 worktree からメインチェックアウトの同パスへの ``Write`` が "This agent is
    isolated in the worktree ... Edit the worktree copy of this file instead of the
    shared-checkout path." で拒否された。自分の worktree 内への ``Write``/``Edit`` は成功するが、
    そこは CLI が参照しない場所であり本物の台帳ではない）。
  * **既知の限界**：この deny は Claude Code の Edit/Write ツール経由の書込みだけを塞ぐ。
    Bash 経由の ``sed -i``・``tee``・シェルリダイレクト等でのファイル改変には掛からない。
    多層防御の一枚であって sandbox ではない（``.claude/hooks/agent-command-gate.sh`` の
    静的検査と同じ制約＝Issue #129）。訂正が必要な Result の内容誤りは、当事者が
    この防御を回避して直接書き換えるのではなく、主文脈による確認つき訂正、または
    安全な訂正用 verb の新設（本 Issue の範囲外）等、当事者以外が介在する経路を通すこと。

スコープ外指摘の一本化（Issue #495）:
  ``## Findings`` は**スコープの内外を問わない単一の指摘台帳**である。スコープ外の指摘を
  別のセクション・別の経路（チャットでの列挙）へ逃がすと、実害判定（``harm``）・カルテ記録・
  ``status`` の verdict をまとめて迂回でき、実害ありの指摘が未処置のまま ``clean`` を
  通過する（PR #490 でこれが起き、Issue #493 が merge 後に流出した）。よって
  * ``scope``（``in``/``out``）は**申告**として残すが**免除力を持たない**、
  * ``harm: real`` にはオーナー判断（``disposition``）の記録を要求し、
  * 未決定のまま残る間は verdict を ``clean`` にしない、
  という3点で経路を1本に閉じる。``issue-implementer``/``issue-fixer`` のハンドオフ
  ``out_of_scope_findings`` も、同じ書式の finding ブロックへ写して ``ingest-review``
  （実行するのは主文脈）でこの列に取り込む。

``harm_detail`` の内容 lint（Issue #511）:
  ``harm_detail`` は**放置時の実害だけ**を書く欄で、処置方針（「対応不要」「別 Issue」）や
  判断経緯（「オーナー確認済み」「新規発生ではない」）を書く欄ではない。
  :func:`check_harm_detail` が :func:`parse_review`（＝``ingest-review`` の入力）に対して
  これを機械的に検査し、違反はレポート全体の取り込みごと拒否する（fail-close）。
  既知の誤検出は :mod:`karte.allowlist` へ**理由付きで**登録して抑制する。
  **既存カルテを読む :func:`parse` 側には掛けない**（``scope`` 必須化と同じ移行方針）。

値の書式は「1行 1 ``key: value``」のみ（複数行の自由記述は持たない＝決定論パースのため）。
``[a, b]`` はリスト、それ以外はスカラ文字列として解釈する。

解析・検証の部品（語彙・値/ブロックのパーサ・``disposition``・``harm_detail`` lint・レビュー
レポートのパーサ等）は責務別のモジュールへ分け、公開名は本モジュールから再エクスポートする
（Issue #746・移設した設計理由は ``.ai/rationale/karte-module-split.md``）。

依存仕様: :mod:`karte` の docstring（Issue #307「カルテの実体」「finding ID による結合」
「Attempt の機械比較可能ヘッダ」）／Issue #495「提案挙動」1〜6（finding の一本化・``scope``・
``disposition``・verdict ゲート・``deferred`` を ``resolved`` にしない・ハンドオフの取り込み）／
Issue #503「提案挙動」（``deferred``/``waived`` の除外を単一の述語
:attr:`Finding.needs_remediation` へ集約し、verdict・``check``・無進捗検知が共有する）・
「観測2」（``change_kind`` に文書のみの変更を表す ``doc`` を追加し、既存の ``config`` 記録は
遡って読み替えない）／Issue #511「提案挙動」（``harm_detail`` に処置方針・経緯の語彙を
検出したら取り込みごと拒否し、該当行と検出語を示す）。
"""
```

### `Finding`

```python
    """ID 付き指摘（台帳の 1 行）。"""
```

### `cleared_by_disposition`

```python
        """「当該 PR では処置しない」とオーナー判断で決まったか（Issue #495／#503）。

        **``deferred``/``waived`` の除外規則はここ 1 箇所にだけ書く。** ``status`` の
        verdict・``check`` の診断網羅要求・無進捗検知は、いずれもこの述語を経由する
        :attr:`needs_remediation` を通して同じ規則を共有する（Issue #503）。

        **``harm: none`` には解除力を与えない**（:data:`CLEARING_HARM`・オーナー確定
        2026-09-07）。``harm: none`` の finding に ``disposition`` を書いても記録が残るだけで
        verdict は ``no-harm-only`` のまま——実害なしの指摘だけが残った状態はオーナーへ
        打ち上げる（AI が 2 行書いて STOP を消せる経路を作らない）。

        ``status`` を ``resolved`` に倒さないのは、「別 Issue へ移したと書くだけで指摘が
        台帳から消える」経路を作らないため（二層設計）。よってこの述語が ``True`` でも
        finding は ``status: open`` のまま台帳に残る。
        """
```

### `needs_remediation`

```python
        """**この PR で是正が求められている未解消 finding か**（Issue #503・判定の単一点）。

        3 つの判定経路がこの述語だけを共有する:
          * ``status`` の verdict … ``clean`` を妨げる未解消 finding
            （:meth:`Karte.remediation_findings`）。
          * ``check`` の診断網羅要求 … 当該ラウンドで診断（Attempt）が要る finding。
          * 無進捗検知 … 「3 ラウンド連続で未解消」を数える対象。

        Issue #495 の実装は除外を verdict 算出にしか入れておらず、``check`` は
        ``deferred`` の finding にも診断を要求して**毎ラウンド必ず 1 回 block**し
        （Issue #503 観測1）、無進捗検知は誰も直さないと決めた finding を拾って
        ``escalate: yes`` を偽陽性で出していた（同 観測3）。どちらも「常に鳴るゲートは
        本物を検出できなくなる」形で安全機構を形骸化させるため、除外を 1 箇所へ寄せる。
        """
```

### `needs_disposition`

```python
        """``harm: real`` なのにオーナー判断（disposition）が未決定のまま未解消か。

        ``scope`` の値によらない——``scope: out``（スコープ外の申告）は実害判定・記録・
        ゲートのいずれの免除にもならない、が Issue #495 の要点そのもの。
        """
```

### `max_consecutive_rounds`

```python
        """未解消のまま連続して挙げられたラウンド数の最大値（無進捗判定に使う）。"""
```

### `Attempt`

```python
    """1 回の是正試行の宣言（機械比較可能ヘッダ）。"""
```

### `Result`

```python
    """Attempt の処置結果（実測 touched-set の記録先・追記のみ）。"""
```

### `remediation_findings`

```python
        """**この PR で是正が求められている未解消 finding**（Issue #503・単一の集合）。

        verdict の「``clean`` を妨げる未解消」（``status --json`` の ``blocking_findings``）・
        ``check`` の診断網羅要求・無進捗検知は、いずれもこの 1 つの集合を使う。
        除かれるのは **``harm: real`` かつ** ``deferred``/``waived`` のものだけ
        （:data:`CLEARING_HARM`）。``harm: none`` は ``disposition`` を書いても残る。
        """
```

### `undecided_findings`

```python
        """``harm: real`` かつ disposition 未決定のまま未解消の finding（Issue #495）。"""
```

### `parse`

```python
    """カルテ文書全体をパースする。書式違反は :class:`KarteFormatError`。"""
```

### `normalize_text`

```python
    """比較用の正規化（``casefold`` ＋ 「文字・数字」以外を区切りへ畳む・空白圧縮）。

    **保持する文字を列挙しない**（K-07）。以前は ``[^0-9a-z ぁ-ヿ 一-鿿]+`` という
    ホワイトリストで畳んでいたため、全角英数・ハングル・アクセント付きラテン・CJK 拡張漢字
    （Ext-A 以降）が丸ごと空白になり、要約がそれらだけで構成されると正規化結果が**空文字**に
    なった。空文字同士は :func:`is_same_finding` の完全一致判定でも n-gram 判定でも
    「同一ではない」と扱われる（:func:`_jaccard` は空集合を 0.0 で返す）ため、
    **再発番を見逃す fail-open** になっていた。

    そこで :mod:`unicodedata` の一般カテゴリで「文字（``L*``）・数字（``N*``）」だけを残し、
    それ以外（記号・句読点・空白・制御）を区切りに畳む。文字体系を列挙しないので、
    新しい文字種が出てきても取りこぼさない（fail-open が構造的に起きない）。

    NFKC 等の互換正規化は**行わない**——全角と半角、丸数字と数字を勝手に同一視すると、
    「別物として起票された指摘」を再発番と誤検出しうる（偽陽性は K-05 の逃げ道と違って
    レビューアが正当な新規指摘を挙げられなくなる方向の害）。畳むのは大小文字だけに留める。
    """
```

### `shingles`

```python
    """比較用の文字 n-gram 集合（既定は bigram）。

    語の区切りに**空白を使わない**（＝空白位置が言い換えで揺れる）ため、空白トークン化は
    使わない。``「既存 attrs を破棄」`` と ``「既存の attrs を破棄」`` は空白トークンでは
    ``が既存`` / ``が既存の`` という別トークンになり、同一指摘なのに一致率が閾値を割る。
    文字 n-gram は言語非依存・決定論的で、語形の揺れ（助詞の挿入・「（再掲）」等の付記）に
    強い。形態素解析器のような外部依存も要らない（標準ライブラリのみの制約）。
    """
```

### `is_same_finding`

```python
    """「同一指摘に新しい ID を振り直した」かどうかの決定論判定。

    2 つの独立した信号の OR:
      * 要約の正規化文字列が完全一致（locus は問わない＝一字一句の再掲）。
      * locus が**交差**し、かつ要約の文字 n-gram Jaccard 係数が閾値以上
        （言い換え・付記つきの再掲）。

    locus の交差を必須にしているのは、同じ箇所への**別の**指摘（例「docstring が古い」）を
    誤って同一視しないため——文字 n-gram だけで判定を回すと、短い要約同士が偶然似ただけで
    再発番と誤検出し、レビューアが正当な新規指摘を挙げられなくなる。

    ``locus`` は複数箇所を持てる（Issue #341 レビュー feedback）ので、完全一致ではなく
    **1 箇所でも共通なら同じ箇所とみなす**（``targets`` の交差判定と同じ考え方）。
    完全一致にすると、前ラウンドで 1 箇所だけ直してミラー側が残った再掲を「別物」と誤判定し、
    再発番を見逃す。

    それでも残る偽陽性（同一 locus に出た短い別指摘同士が閾値を超える）には、レビュー
    レポート側の ``distinct_from``（K-05）で**名指ししたペアだけ**判定を外せる。閾値
    :data:`DUPLICATE_SIMILARITY_THRESHOLD` は逃がすために動かさない——「通すために閾値を
    下げる」と、本来検出したい再発番まで一律に見逃す。
    """
```

### `dumps`

```python
    """カルテ全体を文字列化する（``## Attempts`` を最後に置き、追記が必ずそこに入る）。"""
```

### 旧行コメント（逐語）

```python
    # Karte: issue-307
    ## Findings
    ### F-307-01
    ## Attempts
    ### Attempt 1
    ### Result 1
# 同一指摘の再発番判定（`is_same_finding`）に使う文字 n-gram の粒度と閾値。
    # ``locus`` はリスト（ミラー複数ファイルの同一欠陥を 1 指摘で指す・Issue #341）。
    # ``evidence``＝そう言える根拠（読んだファイル/行・実行したコマンドと結果）。
    # ``expected``＝解消の条件、``recheck``＝次ラウンドの判定手順（ラウンドをまたぐため台帳に持つ）。
    # ``scope``＝レビューアの申告（免除力なし）。既定は ``scope`` 無しの既存カルテの移行措置。
    # ``disposition``＝オーナー判断の記録。空文字＝未決定。
    # --- 参照 ---
# --- パース ------------------------------------------------------------------
    # ``scope`` は台帳側では任意（欠落は DEFAULT_SCOPE）。新規取り込み側で必須にしてある。
# --- 同一指摘の再発番検出 -----------------------------------------------------
# --- シリアライズ -------------------------------------------------------------
```

## K-03 分割計画（#748）

Issue #748（親 #745・K-03・下段 #799＝K-02）の設計と実装結果。設計者＝Claude Code (AI)。K-01・K-02 の節は変更しない。

### 着手時点の実測（L2 head a5cb5d2d 上）
- `python3 -m maintainability_lint check`: `violations=0 accepted_debt=61`（全体）。
- `karte/cli.py` の登録は3件: `module-over-100-lines`（1101行）、`comment-over-3-lines`が2件（892行目から6行・924行目から5行。どちらも `cmd_status` 内）。Issue #748 本文の「初期5件・現main 1,519行」は #696/#697 統合前の値で、現在値と食い違う。
- `cli.py` の構成（行数）: モジュール docstring 約90、import・定数 約25、`_read_report` 26、`_resolve_close_attempt_number` 43、`_view_of`/`_priors_for`/`_stalled_ids`/`_saturated_groups`/`_group_directive` 計約100、`cmd_ingest_review` 15、**`cmd_render` 129**、`cmd_append` 61、`cmd_close_attempt` 77、`cmd_check` 96、**`_status_payload` 115**、**`cmd_status` 149**、`build_parser` 91、`main` 5。

### 方針
- 移す対象は「render/status の表示整形・状態集計」のみ（#748 のスコープ）。`cmd_append`・`cmd_close_attempt`・`cmd_check`・`build_parser` は K-04（#749）の対象なので動かさない。
- **`cmd_render` と `cmd_status` は `cli.py` に薄い入口として残す**（`@fail_close` の宣言・`pointer_completion.resolve_issue`・`karte_loader.load_karte` の呼び出し・`print`・戻り値 `EXIT_OK`）。`build_parser` の `set_defaults(func=cmd_render/cmd_status)` と `require_declared` の検査を変えない。#721（usage error の終了コード）・#728 が後続で触るため、終了コードの経路は動かさない。
- 本文の組み立て（文字列の行リスト生成）は純関数に分け、**1行ごとの文言・順序・空行を1文字も変えない**。長い docstring・コメントは本節の下へ逐語移設し、新モジュールには3行以内の要約だけを残す（K-01・K-02 と同じ運用）。

### 新規モジュール（各100行以内・依存は上から下の一方向）
| 順 | モジュール | 移す内容（移設元 `karte/cli.py`） |
|---|---|---|
| 1 | `stall_detection.py` | `STALL_ROUNDS`、`_stalled_ids`（→`stalled_ids`） |
| 1 | `saturation_groups.py` | `_view_of`、`_priors_for`、`_saturated_groups`、`_group_directive`（公開名で移設。`_saturated_groups` の約35行 docstring は逐語で本節へ） |
| 2 | `status_verdict.py` | `_status_payload` の前半（open/harmful/blocking/undecided の集合と verdict の算出） |
| 2 | `status_findings.py` | `_status_payload` の `findings` 配列の整形 |
| 3 | `status_payload.py` | `status_payload(karte)`（上の2つと `stall_detection`/`saturation_groups` から `--json` の dict を組み立てる。キー順を変えない） |
| 4 | `status_text.py` | `cmd_status` の非 `--json` 本文（verdict ラベル表・要約行群・escalate 行）。`status_finding_lines.py` に「残存 finding」節を分けてよい（100行に収めるため） |
| 2 | `render_attempt_lines.py` | `cmd_render` の「Prior attempts」節 |
| 2 | `render_finding_lines.py` | `cmd_render` の「Open findings」節 |
| 3 | `render_saturation_lines.py` | `cmd_render` の「飽和したアプローチ」節 |
| 4 | `render_text.py` | `cmd_render` の本文全体の組み立て（見出し・導入文・各節の連結） |

- `status_text.py` と `render_text.py` は `cli` を import しない。どのモジュールも `karte.cli` を import しない（循環を作らない）。`karte.model`・`karte.similarity`・既存の K-01/K-02 モジュールにだけ依存する。
- 各モジュールが100行に収まらない場合は、**関数の責務で分け、行数のために任意の位置で切らない**。`dataclass` は作らない（作る場合はロジック class と別 file）。

### `cli.py` に残す公開名と互換
- 残す: `main`、`build_parser`、`cmd_*`（`cmd_render`・`cmd_status` は薄い入口）、`STALL_ROUNDS`、`EXIT_*`、`STDIN_SOURCE`。
- 既存テストが `cli._saturated_groups`・`cli._priors_for`・`cli._stalled_ids`・`cli._status_payload` を直接呼ぶ（`tests/unit/test_karte_cli.py` 1357・1360・1421・1436・3541・3543 行付近）。いずれも **patch ではなく呼び出し**なので、`cli.py` で `from .saturation_groups import saturated_groups as _saturated_groups` のように別名で再エクスポートすれば import 先を変えずに通る。`mock.patch` で `karte.cli.<name>` を差し替えているテストは無い（`repo_roots._PACKAGE_ROOT` 等の他モジュールのみ）。実装時に grep で再確認する。
- `cmd_check`・`cmd_append` が `_stalled_ids`・`_saturated_groups`・`_priors_for` を使うので、その参照が再エクスポート経由で引き続き解決することを確認する。
- `karte_notify/*` の docstring が `karte/cli.py::_status_payload` を依存仕様として名指しする。再エクスポートで名前は残るが、実体は `status_payload.py` に移る。これらの参照の更新は K-03 のスコープ外とし、必要なら別 Issue で申し送る（本 PR では `karte_notify` を編集しない）。

### 同値性の検証（足りない回帰検出力）
既存の `tests/unit/test_karte_cli.py`（verdict 行を厳密に検査する `clean`/`harmful-open` 系、#720 で強化）は**一切書き換えない**。足りないのは「分割前と出力が1文字も変わらない」ことの直接固定なので、次を**分割前のコードで先に記録**してから分割する（K-01・K-02 の golden と同じ手順）。
1. `tests/unit/test_karte_cli_split_compat.py` と `tests/fixtures/karte/cli_render_status_golden.json` を追加。分割前（本 PR の最初の実装 commit より前）の `render`・`status`・`status --json` の stdout 全文の sha256 と終了コードを記録する。
2. 入力は決定論的な karte 文書の変異: verdict の3値（clean・harmful-open・no-harm-only）、`deferred`/`waived`/`fix-here`/未決定の disposition、`scope: out`、`harm: none` への disposition、無進捗（3 ラウンド連続）、飽和（pairwise の組と推移律で広がらない組）、Attempt なし・未クローズあり・Result 複数、locus 複数・空、進行ポインタ補完あり/なし。
3. 異常系: カルテ未作成（`EXIT_NOT_FOUND`）、`--issue` 不正・補完不能、壊れた karte（`KarteFormatError` 経路）。stderr 全文と終了コードを固定する。現状の終了コードを変えない（#721 の挙動変更を入れない）。
4. `status --json` は `json.loads` した dict の**キー順込み**の比較（`status_payload` のキー順が消費者 `karte_notify` に影響しうるため）。
5. 変異検出の確認: verdict 判定の1条件削除、`STALL_ROUNDS` の変更、`render` の節見出しの1文字変更が、いずれもこのテストで検出されることを実装 PR で実測して記す。

### baseline の手順と残存違反（K-03 完了時点）
- baseline は手で編集しない。`python3 -m maintainability_lint baseline` の出力で `maintainability_lint/baseline.json` を更新する。fixer は契約上更新できないため、主文脈が機械的に実行する（K-02 と同じ）。
- 予定差分: `karte/cli.py` の `comment-over-3-lines` 2件の削除と、`module-over-100-lines` の行数・fingerprint の更新。**`accepted_debt` は 61→59 の見込み**（`cli.py` の `module-over-100-lines` は残る）。新規免除・対象除外は追加しない。
- K-03 完了時点で `karte/cli.py` に残る違反: `module-over-100-lines` 1件（目標は概ね600行以下。見込みは約630行）、コメント違反 0。K-04（#749）で `cli.py` を100行以内にし、登録を 0 にする。
- 新しい `#` コメントの連続4行以上は作らない。移設する長いコメント（`cmd_status` 内の 892・924 行目の塊）は3行以内に縮め、全文は下の「移設元コメント」へ。

### 実装時の互換契約と実測（F-806-01・02・04・05・06・07）
- `cmd_render`・`cmd_status` のデコレータ、読込、出力と終了コードを維持し、行組立と判定を各モジュールへ移した。旧 API の `_group_directive` を含む互換名と `model` を `cli` に残す。
- 分割前に確定した golden を変更せず、stdout・stderr・終了コード・JSON キー順を検証する。解除定数の参照は `Finding.cleared_by_disposition` に限り、AST 検査で全 `karte` モジュールのコードを確認する。
- 物理行数は `cli.py` 1101→625。残る verb・parser・既存 docstring は K-04 の対象であり、600 行の目標を 25 行超える。新規モジュールは 15〜92 行。
- `maintainability_lint check` は `violations=3 accepted_debt=58`。`cli.py` の行数変更と古いコメント登録 2 件に由来し、新規モジュールに違反はない。baseline 更新後の見込みは accepted_debt 59。
- verdict、無進捗閾値、render 見出し、解除定数参照、互換名の 5 変異はいずれも対応テストが検出し、各変異を復元した。

### 移設元の docstring・コメント（逐語保全）

#### `_stalled_ids` docstring

```python
    """無進捗（同一 finding が ``STALL_ROUNDS`` ラウンド連続未解消）の finding ID。

    対象は :meth:`model.Karte.remediation_findings`＝**この PR で是正が求められている**
    未解消 finding に限る（Issue #503 観測3）。``disposition: deferred``/``waived`` は
    「誰も直さないと決めた」finding なので、進捗が無いのは当然であり無進捗ではない。
    除外前は ``deferred`` を 1 件でも抱えたまま 3 ラウンド以上回る PR が**毎回**
    ``escalate: yes`` を出し、本物の無進捗（是正が 3 ラウンド連続で効いていない）が
    偽陽性に紛れて見落とされる状態になっていた。
    """
```

#### `_saturated_groups` docstring

```python
    """「同種の再試行がもう ``append`` できない」アプローチを列挙する（K-09：判定の一本化）。

    **``append`` のゲートとまったく同じ判定関数を使う**（:func:`similarity.find_hits` ＋
    :func:`similarity.is_saturated`）。違うのは主語だけで、``append`` の主語が「これから
    書き込もうとしている 1 件」であるのに対し、ここでは「**既に書かれた Attempt k と
    同じ宣言（root_cause / change_kind / targets）を繰り返す仮想の新規試行**」を主語に
    置く。したがって表示の意味は 1 つに定まる——

        ここに挙がったアプローチと**同種**の ``append`` は必ず ``EXIT_SATURATED`` になる。

    是正前は表示側だけが :func:`similarity.cluster`（union-find の連結成分）を使っており、
    推移律で広がるクラスタとゲートの pairwise 件数が食い違っていた。例えば
    A1(rc=x, logic, T1) と A2(rc=x, logic, T2) は change_kind 経由で 1 つの連結成分になる
    一方、A3(rc=x, interface, T2) は A2 とのみ類似（hits=1）なので ``append`` は通る
    ——「``render`` が飽和と言った直後に ``append`` が成功する」＝後工程が誤読した（K-09）。
    現在はどちらも同じ pairwise 判定なので、A1/A2 と同種の再試行だけが拒否対象として
    表示され、A3 のような別アプローチは表示にも現れないし拒否もされない。

    仮想の新規試行には実測 ``touched`` を持たせない（``append`` は修正の**前**に走るため
    新規側に実測値は存在しない）。比較相手の過去 Attempt 側には ``close-attempt`` で
    取り込んだ実測値を載せる——ここも ``append`` と同じ扱い。

    **比較相手（priors）も ``append`` と同じ集合にする**——すなわち候補ごとに
    :func:`_priors_for` で「その候補が対象とする**未解消** finding を共有する Attempt」へ
    絞る。以前はここだけが「未解消 finding をどれか共有する全 Attempt」を priors に使って
    おり、判定関数が 1 つでも**入力集合が 2 通り**あったため表示とゲートが再び食い違った：
    未解消 finding が 2 件あり Attempt を finding ごとに分けると、finding B の Attempt は
    finding A の Attempt 群まで priors に数えられて**飽和表示されるのに ``append`` は通る**
    （過大報告）。逆向き（``append`` は拒否するのに表示に出ない＝過少報告）も同じ穴の裏側。
    判定関数だけでなく**入力も一本化**して初めて K-09 の「表示＝ゲート」が成立する。

    戻り値は ``(candidate_number, members, hits, candidate_view)`` の列。
    ``members`` は「その再試行が衝突する Attempt 番号」（自分自身を含む）で、同じ
    ``members`` を持つ候補は先に現れた 1 件に畳む（同一グループを重複表示しない）。
    """
```

#### `cmd_render` docstring

```python
    """カルテの現在状態を**そのまま注入できる本文**として出力する（K-14）。

    SubagentStart フック（matcher ``issue-fixer``）がこれを実行し、標準出力を
    ``hookSpecificOutput.additionalContext`` として是正エージェントへ自動注入する。
    「是正エージェントに ``render`` を引かせる」設計だと、呼び忘れたら過去の試行を
    知らないまま修正に入る——本件（同じ失敗の繰り返し）で直そうとしている失敗そのものが
    残るため、注入側に寄せた。

    したがって出力は**自己完結**させる:
      * 何の本文か・受け手が何をすべきかを冒頭で述べる（前後の文脈に依存しない）。
      * 過去 Attempt 一覧（実測 touched と Result を含む）／未解消 finding 一覧／
        飽和したアプローチの転換指令を、この 1 通で完結させる。
      * 端末装飾（色・カーソル制御）や対話前提の文言（「上記の…」「続けますか」）を混ぜない。

    ``--issue`` は進行ポインタから補完できる（フックは dispatch prompt を読めない）。
    カルテ未作成は :data:`EXIT_NOT_FOUND` のまま（ガード違反＝EXIT_ERROR と区別する）。
    """
```

#### `_status_payload` docstring

```python
    """verdict とエスカレーション材料を機械判定する（Issue #495 でゲートを追加）。

    verdict は**未解消件数ではなく「clean を妨げる未解消 finding」**で決める。
    ``harm: real`` の finding に限り、``disposition: deferred``（別 Issue へ申し送り）と
    ``waived``（オーナーが明示的に処置不要を許可）は ``status: open`` のまま台帳に残しつつ、
    verdict の上でだけ clean を妨げない（:attr:`model.Finding.needs_remediation`——
    ``check`` の診断網羅要求・無進捗検知と**同じ単一の述語**・Issue #503）。逆に
    ``harm: real`` で disposition が**未決定**のものは、``scope`` が ``out``（スコープ外の
    申告）でも clean を妨げる——「スコープ外」と書くだけで実害判定・記録・ゲートを迂回できた
    のが Issue #495 の欠陥そのものだから、その迂回を機械側で塞ぐ。

    ``harm: none`` には解除力を与えない（:data:`model.CLEARING_HARM`・オーナー確定
    2026-09-07）。実害なしの未解消だけが残る状態は ``no-harm-only`` のままオーナーへ
    打ち上げる対象であり、``disposition`` を 2 行書いて ``clean`` へ変えられてはならない。

    ``harmful_open``（``status --json``）は**台帳上の未解消かつ ``harm: real``** の全件で、
    ``deferred``/``waived`` と決まったものも含む。したがって ``harmful_open`` は verdict の
    説明にはならない——**「clean を妨げる実害あり」＝ ``blocking_findings`` ∩ ``harmful_open``**
    であり、これを ``blocking_harmful`` として payload へ直接出す（PR #496 F-495-06）。
    消費者に積を取らせない：積の取り方を各消費者に委ねると、F-495-05 と同型の
    「verdict と内訳の意味の取り違え」が消費者側で再発する。

    3 つの集合は ``undecided_disposition`` ⊆ ``blocking_harmful`` ⊆ ``harmful_open``
    という包含関係にある。``blocking_harmful`` と ``undecided_disposition`` の差は
    ``disposition: fix-here``（当該 PR で直すと決めたが未修正）の分であり、
    ``verdict == "harmful-open"`` を説明するのは ``blocking_harmful`` の方
    （``undecided_disposition`` が空でも ``fix-here`` が残れば ``harmful-open`` になる）。
    """
```

#### `cmd_status` docstring

```python
    """エスカレーション条件を機械判定し、**そのまま注入できる本文**として出力する（K-15）。

    **手動実行（``python3 -m karte status``）は常に全件を出力する**——フックの既読管理
    （後述）が及ぶのは通知経路だけで、この verb 自体の出力は変えていない
    （Issue #512 Acceptance criteria）。

    K-15 は当初「PostToolUse フック（matcher ``Task``）が ``pr-reviewer`` 呼び出し完了直後に
    これを実行し、判定結果をコンテキストへ自動注入する」設計を構想したが未配線のまま、
    Issue #512 が対応 AC を移譲して**別の設計**で実装した。実際に配線されたのは
    :mod:`karte_notify`（``.claude/hooks/karte-notify.sh``・PostToolUse matcher ``Bash|ctx_execute|ctx_batch_execute``）で、
    トリガーは ``pr-reviewer`` 呼び出し後ではなく ``karte ingest-review``/``close-attempt``
    実行直後、届け先は AI のコンテキスト（``additionalContext``）ではなく**オーナーの
    チャット**（``systemMessage``）にした。AI のコンテキストへ注入するだけでは
    「機械判定が AI の要約を経て歪む」経路を防げないため（実例＝PR #509／Issue #431：
    ``escalate: yes`` を主文脈が「原因が分かっているから問題ない」と独自解釈して丸めた）。
    ``karte_notify`` はこの verb の ``--json`` 出力を読むだけの外部消費者であり、finding ID
    単位の既読管理（``resolved`` 済みで通知済みの finding を再表示しない等）は
    ``karte_notify.notify`` 側の責務としてここには持ち込まない。

    **PostToolUse はツール呼び出しをブロックできない**（公式ドキュメント：the tool already
    ran／blocking does not undo the tool call）ため、この verb の役割は「判定を必ず実行し
    可視化する」までであり、「判定に反した行動（実害あり残存のまま merge する等）を止める」
    のは別途 PreToolUse で merge 操作を捕まえるゲートが担う（Issue #293／#298・本 verb の対象外）。

    ``--issue`` は進行ポインタ（``tmp/_karte/active.json``）から補完できる（K-13/K-14 と
    同じ扱い）。既定出力（非 ``--json``）は残存 finding とその harm 判定・verdict・
    エスカレーション条件のどれに該当するかを 1 通で完結させる（端末装飾・対話前提の
    文言は混ぜない）。機械可読が要るときは ``--json`` を使う（挙動は変えない）。

    本文出力は ``blocking_findings`` / ``blocking_harmful`` / ``undecided_disposition`` の
    3 集合を**包含関係の順に**行として出す（PR #496 F-495-07）。``--json`` にだけ
    ``blocking_harmful`` を出して本文では読み手に積を取らせる、という非対称を残さないため。
    """
```

#### `cmd_status` コメント（移設前 892–897 行）

```python
        # Issue #495: clean の定義は「未解消 0 件」ではなく「clean を妨げる未解消 0 件」。
        # `harm: real` の `deferred`/`waived` は `status: open` のまま残るが verdict を妨げない。
        # PR #496 F-495-05: `no-harm-only` は「台帳の未解消が全件実害なし」ではない——
        # 申し送り／処置不要と決めた `harm: real` が別に残りうる（下の「実害あり」行に出る）。
        # ラベルを「全件実害なし」のままにすると、同じ出力の中で自己矛盾し、
        # オーナーへ偽の前提で打ち上げることになる。
```

#### `cmd_status` コメント（移設前 924–928 行）

```python
    # PR #496 F-495-07: 機械向け（``--json`` の ``blocking_harmful``）だけが積を取らずに済み、
    # 人間の読み手は上の「clean を妨げる未解消」行と「実害あり」行の積を自分で取る、という
    # 非対称を残さない。この行以下の 3 行は包含関係の順
    # （clean を妨げる未解消 ⊇ clean を妨げる実害あり ⊇ 実害あり・disposition 未決定）に並べ、
    # 3 つの集合の関係を読み手が取り違えないようにする。
```

## K-04 分割計画（#749）

Issue #749（親 #745・K-04・下段 #806＝K-03）の設計。**この節は実装前の設計であり、実装は後続の是正ラウンドで行う**。設計者＝Claude Code (AI)。K-01〜K-03 の節は変更しない。

### 着手時点の実測（L3 head 5a03714b 上）
- `python3 -m maintainability_lint check`: `violations=0 accepted_debt=59`（全体）。
- `karte/cli.py` の登録は `module-over-100-lines`（621行）の1件のみ（コメント違反は K-03 で 0）。Issue #749 本文の「初期基準5件」は K-03 前の値で、現在値と食い違う。
- karte 関連で他に残る登録: `karte/similarity.py`（241行）・`karte/touched.py`（105行）・`karte_notify/hook.py`（175行）・`karte_notify/notify.py`（270行）。いずれも `module-over-100-lines` のみ。K-05（#750）・K-06（#751）の対象で、**本 stack では扱わない**。#683 の本文が変更対象に挙げているのは `karte/cli.py` と `karte/model.py` だけなので、これら4ファイルは #683 の変更対象外の見込み（#683 の実装中に触る必要が生じたら報告する）。
- `cli.py` の構成（行数）: モジュール docstring 91、import・再エクスポート 約30、`_read_report` 26、`_resolve_close_attempt_number` 43、`_prepare_ingest`＋`cmd_ingest_review` 25、`cmd_render` 8、`cmd_append` 61、`cmd_close_attempt` 77、`_validate_outcome` 5、`cmd_check` 96、`cmd_status` 10、`build_parser` 91、`main` 5。
- **`decide` verb は `cli.py` の外にある**（`owner_cli.py`・`reviewer_cli.py` が `extra_registrars` として `python3 -m karte` の `__main__.py` から登録される）。K-04 の対象は `cli.py` に残る verb（ingest-review・render・append・close-attempt・check・status）と引数解析で、`owner_cli`/`reviewer_cli` は動かさない。

### 方針
- 各 verb 関数は**同一の関数オブジェクトのまま**移す（`@fail_close(locked=..., prepare=...)` の宣言を verb の定義側に残す）。`cli.cmd_*` を `cli.py` で再エクスポートすれば、`tests/unit/test_karte_verb_boundary.py`（`cmd_*.__doc__` が空でないこと・`locked` 属性）・`test_karte_cli*.py`（`cli.cmd_*` の直接呼び出し）は無変更で通る。**docstring は空にしない**（`verb_boundary` のテストが `__doc__` の存在を要求する）。長い docstring は本節の下へ逐語移設し、verb 側には1〜3行の要約を残す。
- 文言・出力順・終了コード・書込順・例外の種類とメッセージは1文字も変えない（#745 C01）。**#721（argparse の usage error の終了コード）は本 Issue で扱わない**。現行の終了コード・usage error の挙動を維持し、#728 の断定（L0・PR #795 で処置済み）がそのまま通ることを確認する。#683 の動作変更は入れない。
- 引数定義と `cmd_*` の対応（`set_defaults(func=...)`）は動かさない。`argparse` の `help`・`required`・`choices`・`nargs`・`default` を移設時に変えない。

### 新規モジュール（各100行以内・依存は上から下の一方向）
| 順 | モジュール | 移す内容（移設元 `karte/cli.py`） |
|---|---|---|
| 1 | `report_source.py` | `STDIN_SOURCE`、`_read_report`（→`read_report`） |
| 1 | `close_attempt_target.py` | `_resolve_close_attempt_number`（→`resolve_close_attempt_number`）、`_validate_outcome`（→`validate_outcome`） |
| 2 | `verb_ingest_review.py` | `_prepare_ingest`（→`prepare_ingest`）、`cmd_ingest_review` |
| 2 | `verb_append.py` | `cmd_append` |
| 2 | `close_attempt_report.py` | `cmd_close_attempt` が出力する本文（`=== close-attempt` から `カルテ:` まで）と、飽和注意の出力（`print` の順序を保つ） |
| 3 | `verb_close_attempt.py` | `cmd_close_attempt`（検証・実測 diff・追記。出力は `close_attempt_report` に委ねる） |
| 2 | `verb_check.py` | `cmd_check`（docstring は要約のみ） |
| 2 | `verb_show.py` | `cmd_render`、`cmd_status`（K-03 後の薄い入口） |
| 2 | `parser_ingest_args.py` | `ingest-review` の引数定義 |
| 2 | `parser_attempt_args.py` | `append`・`close-attempt` の引数定義 |
| 2 | `parser_inspect_args.py` | `render`・`check`・`status` の引数定義 |
| 4 | `parser_core.py` | `build_parser`（`add_issue`・各 `parser_*_args` の呼び出し・`extra_registrars`・`require_declared`） |
| 5 | `cli.py`（入口） | 要約 docstring・再エクスポート・`main` |

- 依存の向き: `report_source`/`close_attempt_target` → `verb_*` → `parser_*_args` → `parser_core` → `cli`。**どのモジュールも `karte.cli` を import しない**（循環を作らない）。`verb_*` は `pointer_completion`・`karte_loader`・`model`・`paths`・`similarity`・`touched`・`saturation_groups` など既存モジュールにだけ依存する。
- 各モジュールが100行に収まらない場合は、責務で更に分ける（行数のために任意の位置で切らない）。`dataclass` は作らない。連続4行以上の行コメントは作らない。
- `verb_close_attempt.py` と `close_attempt_report.py` の境界は、「書込（`paths.append_text`）までを `verb_close_attempt`、`print` 群を `close_attempt_report`」を基本とする。**`print` と書込の順序は変えない**（書込後に `parse` し直して飽和を判定する現行の順序を保つ）。

### `cli.py` に残す公開名と再エクスポート（漏れ防止）
着手時の `vars(karte.cli)` の実測（`_` 始まりを含む、`__` 始まりを除く）は次のとおり。実装時に**同じ手順で機械的に列挙して照合**する（K-03 では `_group_directive` の再エクスポート漏れが指摘された）。
- 関数・型・定数: `EXIT_ERROR EXIT_OK EXIT_SATURATED KarteUsageError STALL_ROUNDS STDIN_SOURCE build_parser cmd_append cmd_check cmd_close_attempt cmd_ingest_review cmd_render cmd_status main`
- 非公開名（互換のため維持）: `_group_directive _prepare_ingest _priors_for _read_report _resolve_close_attempt_number _saturated_groups _stalled_ids _status_payload _validate_outcome`
- モジュール属性（`from . import x` された名）: `active_pointer argparse fail_close ingest_review int_args json karte_loader model paths pointer_completion read_stream_text render_lines repo_roots require_declared similarity status_lines sys touched_mod`
- 既存テストが `cli.<name>` として使う名（実測）: `EXIT_OK EXIT_ERROR cmd_status cmd_ingest_review cmd_check cmd_render build_parser main model cmd_close_attempt cmd_append _saturated_groups _status_payload _stalled_ids _priors_for __file__`。`cli.__file__` は `test_karte_cli_split_exclusion.py` が `karte/` ディレクトリの特定に使うので、`cli.py` が `karte/` 直下に残ることが前提。
- モジュール属性（`model` 以外）は、外部から `cli.<module>` で参照されないことを grep で確認できれば再エクスポートしなくてよい（現時点の実測では `cli.model` のみ）。確認できなければ維持する。`mock.patch` の対象文字列に `karte.cli.<name>` を使うテストは無い（`repo_roots._PACKAGE_ROOT`・`sys.stdin` など他モジュールの属性のみ）。実装時に再確認する。
- `main(argv=None, extra_registrars=())` は `cli.py` に残す。`karte/__init__.py` と `karte/__main__.py` は `from .cli import main`。**`python3 -m karte` の入口（`__main__.py`）・`.claude/hooks`・`agent-command-gate.sh` の許可 verb 一覧は変えない**。`build_parser` を `main` 内で `cli` の名前空間から引くので、`cli.build_parser` の差し替えは従来どおり効く。
- 外部 import 元（実測）: `karte/__init__.py`・`karte/__main__.py`、tests の `test_karte_*.py`（`from karte import cli`）、`tests/unit/karte_support.py`。`karte_notify`・`issue_start`・`.claude/hooks` は `karte.cli` を import しない（`python3 -m karte_notify.hook` は別系統）。docstring が `karte/cli.py::...` を名指しする箇所（`karte/README.md`・`karte/pointer_completion.py`・`karte_notify/*`・`karte/similarity.py`）は、移設後も名前自体は再エクスポートで残る。参照の更新は本 PR のスコープ外とし、必要なら別 Issue で申し送る（K-05（#750）が `similarity.py` を、K-06（#751）が `karte_notify` を扱うので、そこでの更新が自然）。`karte/README.md` と `karte/pointer_completion.py` は「verb の一覧・補完の規約は `karte.cli` の docstring」と指すので、**入口 docstring に verb 一覧と補完規約の要約と、全文の所在（本ファイル）を残す**。

### 同値性・安全性の検証（足りない回帰検出力）
既存 `tests/unit/test_karte_cli.py` 等（#720・#728 で強化済み）は**一切書き換えない**。K-03 の `cli_render_status_golden.json` は render/status しか固定しない。足りない部分を、**分割前のコードで先に記録**してから分割する（K-01〜K-03 と同じ手順）。
1. `tests/unit/test_karte_cli_verbs_compat.py` と `tests/fixtures/karte/cli_verbs_golden.json` を追加。全 verb（ingest-review・append・close-attempt・check と、`python3 -m karte` 経由の `decide` 等の登録 verb）について、同一入力の stdout/stderr 全文・終了コードを記録する。
2. **書込副作用**: 各ケースの前後で `tmp/_karte/` 配下（台帳・`active.json`・`.writer.lock`）のファイル一覧と内容の sha256 を比較する。拒否ケース（検証失敗・飽和・未知 ID・空 diff・空の stdin）は**台帳とポインタが1バイトも変わらない**こと（拒否時無副作用）。ロック内で拒否する ingest は `tmp/_karte/` と `.writer.lock` を残す（台帳・ポインタは書かない）という現行契約も固定する。
3. **引数・利用エラー**: `argparse` の拒否（必須欠落・不正な choices・未知の verb・`--from` 欠落）の stderr 全文と終了コードを記録する。**現状の終了コードをそのまま固定**し、#721 の挙動変更を取り込まない。`build_parser()` の全 verb の `format_help()` 全文の sha256 も固定する（`help`・`choices`・`nargs`・`required`・`default` の変更検出）。
4. **未検出の終了コード**: カルテ未作成（`EXIT_NOT_FOUND` 相当）・ガード違反（`EXIT_ERROR`）・`fail_close` が変換する例外種別ごとの終了コード。
5. **ロック契約**: `locked=True` の verb（ingest-review・append・close-attempt）と `locked=False` の verb（render・check・status）の宣言が移設後も同一であること（`require_declared` と `verb.locked` を verb ごとに固定）。同時実行（ロック競合時の拒否）が既存テストで固定されているかを実装 PR で確認し、無ければ追加する。
6. **identity**: `cli.cmd_*` が各 `verb_*` モジュールの同一オブジェクトであること、`@fail_close` の宣言（`locked`・`prepare`）が保たれること。
7. 変異検出の確認（実装 PR で実測して記す）: `cmd_append` の飽和判定の削除、`cmd_close_attempt` の書込と `parse` の順序入れ替え、`cmd_check` の `pending` 判定の削除、`build_parser` の1つの `required` の変更、`cmd_close_attempt` の再エクスポート削除が、いずれもこのテスト群で検出されること。

### baseline の手順と K-04 完了後に残る登録
- baseline は手で編集しない。`python3 -m maintainability_lint baseline` の出力で `maintainability_lint/baseline.json` を更新する。fixer は契約上更新できないため、主文脈が機械的に実行する（K-02・K-03 と同じ）。
- 予定差分: `karte/cli.py` の登録削除のみ（`module-over-100-lines` の1件）。**`accepted_debt` は 59→58 の見込み**。新規モジュール13件（上表）に違反が出ないこと。新規免除・対象除外は追加しない。
- K-04 完了後に baseline に残る karte 関連登録（K-05・K-06 の対象。本 stack では扱わない）: `karte/similarity.py`（241行）、`karte/touched.py`（105行）、`karte_notify/hook.py`（175行）、`karte_notify/notify.py`（270行）。いずれも `module-over-100-lines`。`karte/cli.py`・`karte/model.py` の登録は 0 になり、#683 本体の PR で baseline.json を触らずに済む。

### docstring の移設（100行制約の要点）
- `cli.py` のモジュール docstring（91行）、`cmd_ingest_review`・`cmd_check`・`_resolve_close_attempt_number`・`build_parser` の長い docstring は、実装者が移設前に本節の下へ**逐語で**追記してから短くする（PR8 区分1：経緯は削除せず rationale へ移す）。本節は設計であり、逐語の移設は実装 PR で行う。
- 入口 `cli.py` の見込み行数（実測の根拠）: 要約 docstring 約15行＋`from __future__`・再エクスポート約45行（1行に複数名を並べ、`from . import x` は使う名だけに絞る）＋`main` 約8行＝約70行。100行を超えそうな場合は、まず再エクスポートする互換名を「テスト・外部が実際に参照する名」へ絞る（上の grep 結果で不要と確認できたモジュール属性を落とす）。それでも超える場合の対処（再エクスポート専用モジュールの新設等）は、PR7 の様式で選択肢と推奨を添えて主文脈へ報告して判断を仰ぐ。`import *` は使わない。

### 未確認事項（実装時に確認）
- 各新規モジュールが100行に収まるか（`verb_close_attempt.py`・`verb_check.py` が最有力の超過候補）。
- `tests/unit/test_karte_cli.py` が、`cli` の docstring・ソースの文字列（`inspect.getsource` 等）に依存していないこと。
- `agent-command-gate.sh`・`.codex/hooks/agent-command-gate.sh` が verb 名の許可一覧を持つので、verb 名・登録経路を変えていないこと。
