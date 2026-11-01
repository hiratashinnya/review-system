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
5. F-696-11 の是正：`prepare`（ロック前）で `ingest_target`（issue→round）→本文の順に検証する（`cli._prepare_ingest`）。引数・ポインタ・本文由来の拒否はロックを取る前に起きるので何も作らず、優先順位も出荷時に戻る。ポインタ由来の値は並行 ingest が先に進めうるので**ロック内で読み直した値だけを使う**（ロック前の値は検証用に捨てる）。このためポインタを2回読む（読取のみ・副作用なし）。**回復できない残余**は、ロック前の検証を通ったあとロック取得までにポインタが変わり、ロック内の読み直しで拒否された競合時にロック用ファイルが残ること（台帳・ポインタは書かない）だけで、通常の拒否では起きない。

### 入力のエンコーディング（F-696-13）
`UnicodeDecodeError`／`UnicodeEncodeError` は `ValueError` 系で、`verb_boundary._REFUSALS` の5種に含まれず終了コード契約 {0,2,3,4} の外へ漏れる（出荷時の origin/main でも同じ漏れ）。読み側は `path_io.read_text`（レポート本文・台帳・進行ポインタ・`--diff-file`）と `utf8_text.read_stream_text`（標準入力）で、書き側は `path_io` の書込み前に `utf8_text.require_utf8_encodable` で、いずれも拒否例外に畳む。C ロケールでは標準入力が `surrogateescape` で読まれて不正バイトが lone surrogate として検証を通り、台帳への書込みで初めて失敗するため、読んだ直後に UTF-8 へ戻せることも確かめる。`git diff` の出力復号は `errors="replace"` で、`.git` の読取も `replace` のため漏れない。

### `prepare` 段の契約
`prepare(args, repo_root)` はロックの外で 1 回だけ呼ばれ、戻り値が `func(args, repo_root, prepared)` の第 3 引数になる。`prepare` を渡さない verb の署名は `func(args, repo_root)` のまま。

### `--round` の補完
`--round` 省略時の補完は `ingest-review`（ポインタ＋1）と `check`（そのまま）で1つの `pointer_completion.resolve_round`（当時は `cli._pointer_round`、F-696-26 までは `pointer_completion.pointer_round`）を共有する。ポインタが `round` を欠く・別 Issue を指す場合は推測せず fail-close（旧 `_resolve_ingest_round`／`_resolve_check_round` は同一ブロックの複製だった）。

### 整数変換の入口一本化（F-696-21・scope out の既存漏れを本 PR で閉じた）
`parse_int` が閉じた `ValueError` 漏れ（非 ASCII 数字・変換上限 4300 桁超）と同型の経路が、`validate_issue`・`_require_int_list`・`resolved_round`・`parse_finding_id`・カルテ見出し（`# Karte: issue-N`／`Attempt N`／`Result N`）に残っていた（origin/main にもある。終了コード契約 {0,2,3,4} の外＝traceback の 1）。変換は `int_args.ascii_int_or_none`（`None` を返す）と `require_ascii_int`（呼び出し側が渡した拒否例外を投げる）に集約し、各所は自分の拒否例外（`KartePathError`／`KarteFormatError`／`KarteUsageError`）を渡して終了コード 4 に収める。オーナー決定で scope out を本 PR で直した（値引き・先送りしない）。

### `--round` 補完の戻り値（F-696-26）
`pointer_round(args, repo_root, issue, no_round_hint: str) -> int` は、エラー文言の断片を呼び出し側から文字列で受け取り、さらに `ingest_target` が「`--round` が明示されたか」の判定を関数の内と外で二重に持っていた。`resolve_round(args, repo_root, issue, missing_hint: MissingRoundHint) -> ResolvedRound`（`karte/round_resolution.py`：案内の列挙と結果の dataclass＝データのみ）に改め、明示/補完の別（`explicit`）を戻り値で一度だけ返す。`ingest_target` は `explicit` だけを見て +1 を決める。上段が再利用するときも、案内は列挙値で選び、文言を組み立てない。
