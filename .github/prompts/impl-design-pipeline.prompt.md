---
mode: 'agent'
description: 'Orchestrate the implementation-design phase into a pre-implementation FREEZE SET — architecture-design → orchestration-design → prompt-design, recording design decisions (DD#) and running a spec-inspector total-check. Run only when explicitly invoked (the spec → impl-design bridge). Downstream of spec-pipeline.'
---

# 実装設計パイプライン（spec → 実装の橋渡し・凍結セット化）

> 仕様（spec-pipeline）の下流。**論理 DFD＋ドメインモデルが確定**してから、実装前に固める設計物を**順に・チェックポイント付き**で回す。
> 8（判断ログ DD#）と 9（凍結セット総点検）は手法でなく**規律**＝[CLAUDE.md](../../../CLAUDE.md) の「実装設計フェーズ」節に従って各段で実施。
> 原則：[spec-principles](../spec-principles/SKILL.md)。

## 前提（ゲート）
- structured-analysis（論理 DFD・状態）と domain-model（型）が確定。schema-design（外部形式）が要るなら先に。
- **新規資産を作るなら着手前に asset-auditor**（[A14](../../../docs/methods/method-inventory.md)）。

## 段（各段の後にチェックポイント）
1. **凍結セット索引を立てる**：固める項目（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）を1枚に。依存順を宣言。
2. **architecture-design**：モジュール/依存・外部IF・プロトコル・永続（ports & adapters の境界）。
3. **orchestration-design**：制御フロー（スイムレーン）・fail-close・ログ/版。
4. **prompt-design**：LLM 雛形・役割制約・注入対策（出力スキーマは schema-design）。
5. **テスト戦略**：[test-strategy](../test-strategy/SKILL.md)（テーラリング済）を適用し証跡の置き場を決める。
6. **総点検（9）**：**spec-inspector** に設計ドキュメント群を点検させ、G# を出して反映（孤児/穴/分割違反/矛盾）。
7. **判断ログ（8）**：各段で**仕様で一意に決まらない点**を `DD#`（原案→比較→理由付き推奨→暫定決定→影響範囲）で記録。

## 判断の仰ぎ方（フェーズ規律・[CLAUDE.md](../../../CLAUDE.md)）
- **実装設計フェーズ＝暫定で進めてよい**：迷いは推奨案で暫定決定し DD# に記録して前進。
- **矛盾・オーナー判断必須は止める**——ただし**空で止めない**：原案・比較・理由付き推奨/非推奨を必ず添える。
- **他の決められるところは進める**。一通り終えたら**整理して提示**。

## 点検観点（done）
- 凍結セットの全項目が成果物に対応（索引で✅）。
- 各段が前段の確定物に接続（依存順を守る）。
- DD# に未決/暫定が記録され、影響範囲が明記。
- spec-inspector の G# が反映済み（矛盾は打ち上げ）。

## 成果物
- 設計索引（凍結セット）＋ architecture/orchestration/prompt 各設計 ＋ 判断ログ（DD#）。
- 同期更新：[method-inventory](../../../docs/methods/method-inventory.md)・[asset-plan](../../../docs/methods/asset-plan.md)・[CLAUDE.md](../../../CLAUDE.md)。
</content>
