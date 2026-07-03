要求層ノード（VAL / SR / FR / NFR）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・本文4項目・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/requirements-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の VAL/SR/FR/NFR を、type 値（VAL|SR|FR|NFR・自由記述不可）・id PREFIX（`VAL-`/`SR-`/`FR-`/`NFR-`・既存最大+1）・必須依存辺方向（SR→VAL・FR→SR・NFR→SR の無名依存辺）・本文4項目フォーマット・RULE チェックリスト（RULE-005/006/017/018）を**プロンプト内に閉じて**提供し、外部参照なしに著作させる（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親ノード ID）／`parent_body`（親の本文・YAML）／`sprint`（current_phase）／`context`（関連ノード）／`error`（再試行時の差し戻し）。記載内容（I-9）＝各型の本文4項目（VAL＝便益1文・SR＝ステークホルダー欲求・FR＝機能1文・NFR＝制約）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown（フロントマター YAML＋本文）を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない（reconciliation 専権）。
**注意事項**: 辺は無名依存辺（kind/status を書かない・to は単数・ref_version 必須）。`scheduled: ""`（空文字のみ・将来フェーズは labels に post-mvp 等）。suppress 使用時は inline comment に理由必須（RULE-007 は抑制不可）。NFR の検証証跡辺は verification 発火のため requirements では沈黙（suppress 不要）。
