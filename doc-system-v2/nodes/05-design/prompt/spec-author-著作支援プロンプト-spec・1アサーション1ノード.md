SPEC ノードの著作支援プロンプト。外部ファイル参照なしに v2 slug id・path 由来 type・必須辺方向・本文3項目・分割／RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/spec-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親 SPEC または FR 配下の子 SPEC を、v2 slug id（`slugify(title)`・階層枝番なし）・path 由来 type・必須依存辺方向（子→親 SPEC の無名依存辺・FR を直接参照しない）・本文3項目（前提条件／入力・トリガ／期待動作）・分割基準（1 SPEC=1 検証アサーション。複数 RULE・複数期待結果・複数トリガなら分割）・RULE チェックリスト（RULE-007/016/019）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親 SPEC/FR の ID）／`parent_body`／`sprint`／`context`（上流 FR・隣接 SPEC）／`error`。記載内容（I-9）＝各子 SPEC の3項目本文＋`condition`（normal|boundary|empty|failure|error・RULE-016 ERROR）。
**出力形式**: `tmp/<sprint>/<parent-id>/nodes/02-what/spec/...` に corpus ミラーレイアウトで出力する。SPEC は body_policy=required のため、各子 SPEC は `{slug}.yaml` と同名 `{slug}.md` を持つ。親更新がある場合も同じ tmp ミラーに置く。既存ファイルは上書き（再試行も同様）。本ファイルへは書かない。
**注意事項**: 親→子の辺は持たない（親子は子→親の同型依存辺で表す）。辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。`scheduled` は非空必須。現行スプリントは `scheduled: "sprint-1"` などで明示し、後送りはオーナー承認済み sprint 値を指定。全子に `condition` 属性必須。`suppress` / `suppress_reason` は issue #118 で廃止済みのため出力しない。SPEC←TD 被依存辺は verification 発火のため SPEC 著作時点では追加しない。
