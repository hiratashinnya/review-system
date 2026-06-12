# 資産テーラリング台帳（tailoring-registry）

> 資産の**汎用標準**と**プロジェクト・テーラリング済み版**の対応を管理する単一ソース。
> プロセスはスキル等で実現するため、**テーラリングの実体は `.claude/` 配下**に置く（docs ではない）。
> 関連：[asset-plan](../docs/methods/asset-plan.md)・[method-inventory A16](../docs/methods/method-inventory.md)・原則 [PR2](skills/spec-principles/SKILL.md)（機構/デフォルト）・[PR8](skills/spec-principles/SKILL.md)（消さず残す）。

## 配置ルール
| 区分 | 置き場 | auto-load | 役割 |
|---|---|---|---|
| 汎用標準（非活性） | `.claude/standards/<name>/SKILL.md` | されない | プロジェクト非依存の不変条件＋ノブ一覧。参照ベースライン |
| テーラリング済み（active） | `.claude/skills/<name>/SKILL.md` | される | ノブを埋めた本番運用版 |
| 台帳 | `.claude/tailoring-registry.md` | — | 標準⇄テーラリングの対応・実体パス・差分 |

## テーラリング手順（標準 → active）
1. 標準を棚卸し（不変条件は継承・ノブを洗い出す）。
2. **既存の active 汎用版があれば** `git mv .claude/skills/<n> .claude/standards/<n>`（非活性化・消さない＝PR8）。
   ※ 本PJのように標準を**新規 author** する場合は、標準を `standards/` に、テーラリング版を `skills/` に直接置く（extract-then-generalize）。
3. ノブを埋めた `SKILL.md` を `.claude/skills/<n>/` に置く（active）。
4. **本台帳に追記**（下表）。

## 台帳

| 資産 | 標準源 | 実体（active） | テーラリング内容（要点） | 由来PJ |
|---|---|---|---|---|
| test-strategy | `standards/test-strategy/SKILL.md` | `skills/test-strategy/SKILL.md` | 全 public 関数を unittest／非決定（LLM）は `FakePlatformAdapter`(record-replay) で決定化＝アダプタ境界＝テスト境界／e2e＝Claude Code エージェント×`io/cli` stdout 駆動／log＝stdout ダンプ(`tee`)／dirs＝`tests/{unit,cases,reports,logs}`／版＝ケース版＋commit id＋雛形版＋基準content_hash(S6)／runner＝`python -m unittest` | review-system |

> その他の既存スキル（align・io-event-ledger・value-trace・mvp-scope・schema-design・domain-model・spec-pipeline・asset-pipeline・**asset-lateral-deploy**／
> **実装設計：architecture-design・orchestration-design・prompt-design・impl-design-pipeline**）と
> エージェント（spec-inspector・structured-analysis・asset-auditor）は**未テーラリング＝汎用メソッドのまま active**。
> ※ 実装設計スキルは**汎用メソッド**（本PJ固有の選択＝ヘキサゴナル/内部git/stdout プロトコルは成果物 docs 側）。テーラリングが要る場合のみ本表へ起票する。
> ※ `asset-lateral-deploy` は Issue #3 で新規追加（汎用メソッド・テーラリング対象外）。
</content>
