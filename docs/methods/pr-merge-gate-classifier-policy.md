---
policy_id: pr-merge-gate-classifier
classifier_version: "1.16"
status: frozen
authority: issue-431
---

# PR-merge gate classifier policy

- 対象: `pr_merge_gate/classifier.py`（`classify_pre_use` / `_split_shell_commands` 他）。
  managed merge tool の pre-use hook が Bash・REST・connector の各 tool_input を
  `merge` / `block` / `error` の3種へ分類する closed classifier の挙動契約を定める。
- 正本: 本ファイル ＋ `pr_merge_gate/classifier.py` の docstring。判定ロジックの一次実装は
  常にコードであり、本ファイルは実装済み挙動を人・LLM 向けに文書化するものである
  （`.claude/rules/07-project-structure.md`「依存仕様の参照原則」）。
- `pr_merge_gate` は `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」
  における「どちらのシステムにも含有されない汎用ハーネス」区分（`blocker_gate` と同区分）に属し、
  改修は Issue 運用（本ファイルの改訂も同様、doc-system-v2 ノード起票の対象ではない）。

## 1. 分類の骨格

`classify_pre_use` は tool_name に応じて次の経路へ分岐する。

- managed connector 名（`_CONNECTOR_MERGE` / `_CONNECTOR_AUTO`）→ 直接 `merge` / `block` に束縛。
- `Bash` / `bash` 以外の tool → `None`（gate 対象外）。
- `Bash` → `tool_input.command` を `_split_shell_commands()` で quote-aware にleaf分割し、
  各 leaf を既知の安全形状（`git` builtin・`gh` サブコマンド・`_SAFE_DATA_EXECUTABLES` 等）と
  照合する。分割・照合のどこかで構造を証明できなければ `error/CLASSIFIER_UNKNOWN`
  （fail-close。「merge かどうか分からない入力は merge 扱いに倒す」設計）。

## 2. `_split_shell_commands()` が許可する構文

quote-aware に単一文字列を「`;` `&` `|` `\n` `\r` で連結した linear list」として分割する。
各 leaf に対して次を許可する。

- 単純/二重引用符・バックスラッシュエスケープ（quote 内の `{}()` は常に許可＝リテラル扱い）。
- 単純な file/fd redirection（`>` `>>` `<` `>|` `<>` `>&word` `<&word` `&>` `&>>`。
  Issue #428）。redirect先はdata sinkとして leaf から除去し、除去後の leaf を返す。
- **unquoted の単純パラメータ展開 `${...}`**（本節、Issue #431。詳細は3節）。
- 先頭 leaf に限った `cd <literal-path>` の非展開 operand（Issue #435。`_literal_cd_leaf`）。

次は無条件で `None`（未対応構造・fail-close）とする。

- 裸の（`${` 以外の文脈の）`{` `}`、および `(` `)` すべて（subshell・brace group・
  process substitution の入口）。
- command substitution（`$(...)` ・バックティック）。quote 内外を問わない。
- heredoc / herestring（`<<` `<<<`）。
- 制御構文の予約語（`if` `while` `for` `case` `function` 等）が leaf 先頭に unquoted で
  現れる形。

## 3. `${...}` 単純パラメータ展開の許可範囲（Issue #431・classifier_version 1.16）

### 3.1 背景

1.15 以前は unquoted の `(` `)` `{` `}` のいずれかを検出した時点で leaf 全体を `None` に
していた。`$(...)` ・バックティック（command substitution）はこの判定より前段の独立した
チェックで既に検出・拒否されているため、`${VAR}` 形式の**単純パラメータ展開**まで一律に
拒否する必要はなく、`echo ${VALUE}` のような実運用で頻出する非merge commandまで誤ブロック
していた（`cd` は本節の緩和と別の経路——`_literal_cd_leaf` が operand 中の `$` を無条件拒否
するため、`cd ${REPO}` は1.16後も CLASSIFIER_UNKNOWN のままである。2節の「先頭 leaf に限った
`cd <literal-path>` の**非展開** operand」と整合する）。1.16 でこの過剰拒否だけを緩和する。

### 3.2 許可する形

- `${` の出現ごとにネスト深度カウンタを +1、対応する `}` で -1 する。
- 深度 > 0 の間は、次のいずれかの文字だけを許可対象として1文字ずつ消費する。
  - 深度を増やす新たな `${`（ネスト。`${VAR:-${OTHER}}` はこの再帰で成立する）。
  - 深度を減らす `}`。
  - `_PARAM_EXPANSION_BODY_CHAR` に一致する文字
    （`[A-Za-z0-9_:=+?#%/!.,^*@-]`。変数名・`:-` `:=` `:+` `:?` `#` `##` `%` `%%` `/` 等の
    パラメータ展開演算子記号を許容する範囲）。
  - **例外**：直前の文字が `\` でエスケープされた1文字は、`_split_shell_commands()` の
    escape 処理がこの深度追跡ブロックより前段で消費するため、`_PARAM_EXPANSION_BODY_CHAR`
    の判定を経ずに通過する（`${VAR:-\x}` の `x` は許可文字集合の外でも通る）。bash 自身も
    `\` でメタ文字を無効化するため classifier の受理内容と bash の実際の解釈は一致しており、
    fail-open ではない意図的な挙動（詳細は3.3）。
- 上記以外の文字（quote・redirect開始・leaf区切り・空白・裸の `(`・裸の `{` 等）が
  深度 > 0 の間に現れた場合は、その時点で `None`（fail-close）とする。
- 入力全体を読み終えた時点で深度が 0 に戻っていなければ `None`（`${` が閉じていない）。

### 3.3 許可しない形（引き続き拒否）

- 裸の `{`（`${` 以外の文脈で現れる `{`）・裸の `}`（深度0での出現）・`(` `)`。
- `${...}` の内部に現れる `$(...)` ・バックティック・quote（`'` `"`）。深度追跡の判定は
  quote-open判定より**前段**に置いてあり、深度 > 0 の間はこの判定が全文字を横取りする。
  `_PARAM_EXPANSION_BODY_CHAR` は `$` ・バックティック・quote文字のいずれも含まないため、
  これらは許可文字集合による拒否（`return None`）でそのまま fail-close される
  （既存の独立した command substitution 検出はこの判定より後段にあるが、深度 > 0 の間は
  出番がない——判定順序ではなく許可文字集合の狭さが安全性の根拠になる）。
- 未対応文字（redirect・leaf区切り・空白等）が深度 > 0 の間に出現する形全般。これにより
  「`${` を開いたまま `;` で leaf を分割し、深度カウンタが別の leaf へ状態を持ち越す」余地を
  構造的に排除している——深度 > 0 のまま許可しない文字に遭遇した時点で即座に `None` を返すため、
  leaf 分割そのものが起こらない。
- **例外**：3.2 で述べたとおり `\` でエスケープされた1文字だけは、上記の許可文字集合判定を
  経ずに通過する。escape 処理は深度追跡ブロックより前段にあるため。これは fail-open ではない
  ——bash 自身も `\` の直後の1文字をメタ文字として評価しないため、classifier が受理する内容と
  bash が実際に解釈する内容は一致したままである。

### 3.4 redirect target との併用は不可

`${...}` の許可は**引数位置**（3.2）に限られ、redirect target（`_scan_redirection_target()`）
には及ばない。`_scan_redirection_target()` は `{` に到達すると target 走査を打ち切り
（未対応構造として `break`）、本体ループの裸の `(){}` 一律拒否（3.3）に落ちる。したがって
`> ${LOGFILE}` のように redirect target 内に `${...}` を書いた形は、1.16 以降も
`CLASSIFIER_UNKNOWN` のまま拒否される。

### 3.5 実行語位置での扱いは変えていない

`${VAR}` を**実行語（コマンド名）の位置**で使う形（例: `${CMD} merge 1 --squash`）は、
`_split_shell_commands()` を通過した後も `_dynamic_executable()` が別途検出し、
従来どおり `error/CLASSIFIER_UNKNOWN` にする。3節が緩和するのは
「非展開の引数位置での `${VAR}` が leaf 分割の時点で一律拒否される」過剰拒否だけであり、
動的な実行実体の解決を許可する変更ではない。

### 3.6 `gh pr merge` の title/message引数もparameter expansionを拒否する

3.2 の緩和により、以前は `_split_shell_commands()` の一律拒否で `gh pr merge` コマンド
自体が leaf 分割の時点で `CLASSIFIER_UNKNOWN` になっていた
`gh pr merge 1 --squash --body ${B}`（unquoted）のような形が、leaf 分割を通過して
`_cli_operation()` まで到達するようになった。`_cli_operation()` は title（`--subject`/`-s`）・
message（`--body`/`-b`）の値を `commit_title`/`commit_message` としてそのまま
`MergeOperation` へ束縛するため、`gh api` 経路（`_has_active_parameter_expansion` による
`subcommand[0] == "api"` の検査）と同様のガードが無いと、パラメータ展開を含む値が
未解決のまま merge 操作として受理されてしまう。これを閉じるため、`_cli_operation()` は
title/message の値取得時点で `_has_active_parameter_expansion()` を適用し、有効な
`$` を含む値は `error/CLASSIFIER_UNKNOWN` にする（quote の有無を問わない——`--body ${B}`・
`--body "${B}"` のどちらも shlex による dequote 後は同一の値になるため、同じ判定になる）。

### 3.7 回避パターンの再確認

サブシェル（`( ... )`）・ブレースグループ（`{ ...; }`）・command substitution
（`$(...)` ・バックティック）を使って merge 操作を隠す既知の回避パターンは、3.3 のとおり
引き続きすべて `None`（fail-close）である。3.2 の許可は `${` に厳密に限定されており、
これらの構造を通過させる経路を新設しない（回帰テスト:
`tests/unit/test_pr_merge_classifier.py` の `${}` 関連ケース、
`tests/fixtures/pr_merge_classifier_shell_v1.json` の `redirected-brace-group-merge` /
`redirected-subshell-merge` / `double-quoted-command-substitution` /
`backtick-command-substitution` 等の既存 frozen ケース）。

## 4. 版の扱い

`classifier_version`（本ファイル frontmatter）は `pr_merge_gate/classifier.py` の
`CLASSIFIER_VERSION` 定数、`tests/fixtures/pr_merge_classifier_shell_v1.json` および
`tests/fixtures/pr_merge_actual_fire_v1.json` の `classifier_version` フィールドと
常に完全一致させる。`_split_shell_commands()` / `classify_pre_use()` の入出力（許可・拒否
される構文の集合、束縛される operation の形）を変える改修は、このファイルの版と
上記3箇所を同一 PR で bump する。文言修正のみで判定を変えない改訂は bump 不要
（`.ai/guidance/common.md`「正本・実装規約」の一般則）。

**機械検査が及ぶ範囲は上記4箇所のうち3箇所（コード定数＋fixture2箇所）に限る**：
`tests/unit/test_pr_merge_classifier.py` は `pr_merge_classifier_shell_v1.json`
（`fixture["classifier_version"]`）・`pr_merge_actual_fire_v1.json`
（`fixture["expected_audit"]["classifier_version"]`）の双方を `CLASSIFIER_VERSION` と
突き合わせる `assertEqual` を持つが、**本ファイル frontmatter 自体を比較する機械検査は無い**。
frontmatter は手動同期であり、drift しても CI では検知できない（改訂時は本節の手順に従って
手動で合わせる）。
