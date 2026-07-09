分析層ノード（ACTOR / I / O / D / P / E）の著作支援プロンプト。外部ファイル参照なしに v2 slug id・path 由来 type・必須辺方向・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/analysis-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の ACTOR/I/O/D/P/E を、v2 slug id（`slugify(title)`・連番 prefix なし）・path 由来 type・必須依存辺方向（依存方向に統一・DD-017＝ACTOR→SR・I→SPEC・O→SPEC/P/ACTOR・D→SPEC/P・P→SPEC（・I/D/E 該当時）・E→SPEC/ACTOR）・各型本文フォーマット（E は5要素必須）・RULE チェックリスト（RULE-005/006）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型の本文（I/O＝もの・発生源/受け手・形式・タイミング、P＝単一責務1文＋入出力/トリガ辺、E＝スティミュラス/アクション/レスポンス/アフェクト/イベント名の5要素）。
**出力形式**: `tmp/<sprint>/<parent-id>/nodes/03-analysis/...` に corpus ミラーレイアウトで出力する。分析層は body_policy=required のため、各ノードは `{slug}.yaml` と同名 `{slug}.md` を持つ。本文に YAML/frontmatter/バッジは書かず、本ファイルへは書かない。
**注意事項**: 辺方向は依存方向（O→P・P→E・O/E→ACTOR）。プロセス間中間データは D 型で必ず起票（O→ACTOR を持たない・DD-7）し価値経路（PR6）を連続させる。辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。E は刺激元 `→ACTOR` 必須（DD-020）。`scheduled: ""` 固定。
