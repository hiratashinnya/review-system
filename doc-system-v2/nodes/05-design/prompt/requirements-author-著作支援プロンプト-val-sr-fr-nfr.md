要求層ノード（VAL / SR / FR / NFR）の著作支援プロンプト。外部ファイル参照なしに v2 slug id・path 由来 type・必須辺方向・本文4項目・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/requirements-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の VAL/SR/FR/NFR を、v2 slug id（`slugify(title)`・連番 prefix なし）・path 由来 type・必須依存辺方向（SR→VAL・FR→SR・NFR→SR の無名依存辺）・本文4項目フォーマット・RULE チェックリスト（RULE-005/006/017/018）を**プロンプト内に閉じて**提供し、外部参照なしに著作させる（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親ノード ID）／`parent_body`（親の本文・YAML）／`sprint`（current_phase）／`context`（関連ノード）／`error`（再試行時の差し戻し）。記載内容（I-9）＝各型の本文4項目（VAL＝便益1文・SR＝ステークホルダー欲求・FR＝機能1文・NFR＝制約）。
**出力形式**: `tmp/<sprint>/<parent-id>/nodes/...` に corpus ミラーレイアウトで出力する。要求層は body_policy=required のため、各ノードは `{slug}.yaml` と同名 `{slug}.md` を持つ。本文に YAML/frontmatter/バッジは書かず、本ファイルへは書かない（reconciliation 専権）。
**注意事項**: 辺は無名依存辺（kind/status を書かない・to は単数・ref_version 必須）。`scheduled: ""`（空文字のみ・将来フェーズは labels に post-mvp 等）。`suppress` / `suppress_reason` は issue #118 で廃止済みのため出力しない。RULE-007 は always_error として常時 ERROR 発火する。NFR の検証証跡辺は verification 発火のため requirements では沈黙する。
