設計層ノード（ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/design-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の設計層10型を、type 値（自由記述不可）・id PREFIX（`MOD-`/`PORT-`/`PRS-`/`DS-`/`ORC-`/`DM-`/`TERM-`/`SCM-`/`CFG-`/`PROMPT-`）・必須依存辺方向（MOD→P|D・PORT→MOD・PRS→DS・DS→P・ORC→E・DM→TERM/MOD・TERM→SPEC・SCM→SPEC・CFG→SCM/SPEC・PROMPT→SPEC）・各型本文フォーマット・RULE チェックリスト（RULE-006/007）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型本文（MOD＝責務1文+公開I/F+依存、PORT＝抽象化する副作用、PRS/DS＝保存対象・理由・ライフサイクル、ORC＝制御フロー+失敗経路、DM＝定義+型+不変条件、SCM＝目的+フォーマット+必須フィールド、CFG＝用途+ファイルパス、PROMPT＝目的+版+入力変数、TERM＝定義）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない。
**注意事項**: 辺は無名依存辺（旧 kind refines/instantiates/uses/see-also は廃止・to は単数・ref_version 必須）。SCM/CFG/PROMPT の階層は -N 採番で表現（自己辺ルールが無いため親子辺は張らない）。`scheduled: ""` 固定。RULE-007 は抑制不可。
