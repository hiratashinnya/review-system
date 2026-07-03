SPEC ノードの著作支援プロンプト。外部ファイル参照なしに type 値・id 枝番パターン・必須辺方向・本文3項目・分割／RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/spec-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親 SPEC または FR 配下の子 SPEC を、type 値（SPEC・自由記述不可）・id 枝番（`親ID-N`・数字のみ・`-a/-b` 禁止）・必須依存辺方向（子→親 SPEC の無名依存辺・FR を直接参照しない）・本文3項目（前提条件／入力・トリガ／期待動作）・分割基準（1 SPEC=1 検証アサーション。複数 RULE・複数期待結果・複数トリガなら分割）・RULE チェックリスト（RULE-007/016/019）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親 SPEC/FR の ID）／`parent_body`／`sprint`／`context`（上流 FR・隣接 SPEC）／`error`。記載内容（I-9）＝各子 SPEC の3項目本文＋`condition`（normal|boundary|empty|failure|error・RULE-016 ERROR）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子 SPEC 群＋更新後の親 YAML を Write する＝tmp ノード草案（D-8）。既存ファイルは上書き（再試行も同様）。本ファイルへは書かない。
**注意事項**: 親→子の辺は持たない（階層は ID パターン `X-N` で表現）。辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。`scheduled: ""` 固定（`verification`/`sprint-N` 禁止）。全子に `condition` 属性必須。SPEC←TD 被依存辺は verification 発火のため沈黙（ノード suppress を付けない）。
