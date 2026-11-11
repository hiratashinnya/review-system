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
    時点で 2 要素へ静かに割れる**。:func:`is_same_finding` は正規化した要約が完全一致しない場合に locus の交差と類似度で判定するため、
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
