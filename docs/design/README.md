# 設計フェーズ index — 実装前の「凍結セット」

> 実装着手の前に固める設計物の一覧と状態。出典の合意は [dashboard](../dashboard.md)。
> データ辞書/クラス設計（[00](00-data-dictionary.md)/[01](01-class-design.md)）の上に、**実装の足場**を8項目で固める。

## 凍結セット（8項目）と着手順

依存：**A（モジュール）→ B/②（IF）→ C（永続）→ ①（流れ）→ ③（プロンプト）→ D＋④（ログ/テスト）**。

| # | 項目 | 成果物 | 状態 |
|---|---|---|---|
| A | モジュール／パッケージ構成と依存方向 | [02-module-architecture](02-module-architecture.md) | ✅ |
| ② | 外部アクタ IF のシグネチャ（User/Reviewer/Maintainer） | [03-external-interfaces](03-external-interfaces.md) | ✅ |
| B | PF 駆動プロトコル＋公開ツールのシグネチャ（PF＝外部） | [04-platform-protocol](04-platform-protocol.md) | ✅ |
| C | 永続層（DS1–DS5）設計・内部 git ワークスペース（S4 実体） | [05-persistence](05-persistence.md) | ✅ |
| ① | オーケストレーション（**スイムレーン付きフローチャート**） | [06-orchestration](06-orchestration.md) | ✅ |
| ③ | システムプロンプト設計（何をどこに・どう合成） | [07-system-prompts](07-system-prompts.md) | ✅ |
| D | ロギング／バージョニング規約（stdout ダンプ・版スタンプ） | [08-logging-and-versioning](08-logging-and-versioning.md) | ✅ |
| ④ | テスト戦略（資産化＝`/test-strategy` をテーラリング） | `.claude/skills/test-strategy/`（テーラリング済）＋ `tests/`（証跡） | ✅ 戦略確定 |

> ① は**スイムレーン付きフローチャート**（Mermaid `flowchart` の `subgraph` をレーンに）で表現する（シーケンス図は使わない＝分岐/繰返しが見づらい）。
> E（非決定ステップを決定化するテスト用シーム＝Fake アダプタ）は ④ に内包。
> **設計判断ログ**＝[decisions.md](decisions.md)（DD1–DD9）。仕様で一意に決まらなかった点の暫定決定と影響範囲。
> **次**：実装フェーズ（`tests/` 証跡の生成は実装と同時）。[01 クラス設計](01-class-design.md) へ `ExecutionId` 追加が要る（[DD6](decisions.md#dd6--executionid-の定義)）。

## 横断の約束（凍結セット全体に効く）
- **依存は内向き**（[02](02-module-architecture.md)）：`domain ← core(ports) ← adapters/persistence/cli`。コアは PF/IO を知らない。
- **失敗は型**（[S3](../requirements/13-stabilization.md)）：各段は `StageOutcome`（Result）を返し fail-close を強制（[01 §5](01-class-design.md)）。
- **状態は永続層に隔離**（[C](05-persistence.md)）：DS1–DS5。導出物は frozen。
- **資産のテーラリング運用**（[tailoring-registry](../../.claude/tailoring-registry.md)）：標準は `.claude/standards/`、テーラリング済は `.claude/skills/`。
</content>
