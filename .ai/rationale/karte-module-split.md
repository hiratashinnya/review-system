# karte / karte_notify の責務分割で移設した設計理由（PR #696）

`karte/cli.py` と `karte_notify/notify.py` から責務ごとに新モジュールへ切り出した際、連続コメント3行以内の規約（Issue #539）に合わせて縮めたコード側の説明を、移設元の文言のまま保管する。コード側は各モジュール冒頭から本ファイルへ1行で辿れる。

## `karte_notify/trigger.py`：tool 呼び出しの検出（移設元：`karte_notify/notify.py`・Issue #512）

### 検出の対象は `-m karte` 経由の起動だけ（`TRIGGER_RE`）
`karte ingest-review` / `karte close-attempt` の実行を検出する（Issue #512 Scope 1）。`-m karte` 経由の module 起動だけを見る（`karte` package の CLI 契約そのものなので、エイリアス・別実行形は対象外＝取りこぼしても fail-open で実害が小さい方に倒す）。

### 検出対象の tool_name と `ctx_execute_file` の除外（`SUPPORTED_TOOL_NAMES`）
本フックが検出対象とする tool_name（Issue #512 是正・F-512-02）。`Bash` に加え、`.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」で issue-implementer / issue-fixer / pr-reviewer / 主文脈 / dsv2-lookup に付与済みの実行系 MCP ツール（`ctx_execute`/`ctx_batch_execute`）経由の `karte ingest-review`/`close-attempt` 実行も同じ通知対象にする。`ctx_execute_file` は既存方針で全ロール未付与のため対象に含めない（`.claude/rules/05-skills-agents.md` 同節）。

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
