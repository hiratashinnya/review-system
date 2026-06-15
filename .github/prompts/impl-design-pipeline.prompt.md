---
description: 'Orchestrate the implementation-design freeze set: architecture → orchestration → prompt-design → test-strategy → spec-inspector total-check. Run only when explicitly invoked after spec-pipeline.'
agent: agent
---

# 実装設計パイプライン（spec → 実装の橋渡し・凍結セット化）

仕様（spec-pipeline）の下流。論理 DFD＋ドメインモデルが確定してから、実装前に固める設計物を順に・チェックポイント付きで回す。

原則：spec-principles（PR7 矛盾は停止・PR10 認識合わせ先行）。

## 前提（ゲート）

- structured-analysis（論理 DFD・状態）と domain-model（型）が確定。
- schema-design（外部形式）が要るなら先に。
- 新規資産を作るなら着手前に asset-auditor（A14）。

## 段（各段の後にチェックポイント）

1. **凍結セット索引を立てる**：固める項目（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）を1枚に。依存順を宣言。
2. **architecture-design**：モジュール/依存・外部IF・プロトコル・永続（ports & adapters の境界）。
3. **orchestration-design**：制御フロー（スイムレーン）・fail-close・ログ/版。
4. **prompt-design**：LLM 雛形・役割制約・注入対策。
5. **テスト戦略**：test-strategy（テーラリング済）を適用し証跡の置き場を決める。
6. **総点検**：spec-inspector に設計ドキュメント群を点検させ、G# を出して反映（孤児/穴/分割違反/矛盾）。
7. **判断ログ（DD#）**：各段で仕様で一意に決まらない点を `DD#`（原案→比較→推奨→暫定決定→影響範囲）で記録。

## 判断の仰ぎ方

- **実装設計フェーズ＝暫定で進めてよい**：迷いは推奨案で暫定決定し DD# に記録して前進。
- **矛盾・オーナー判断必須は止める**——ただし空で止めない：原案・比較・理由付き推奨を必ず添える。

## 点検観点（done）

- 凍結セットの全項目が成果物に対応（索引で✅）。
- 各段が前段の確定物に接続（依存順を守る）。
- DD# に未決/暫定が記録され、影響範囲が明記。
- spec-inspector の G# が反映済み（矛盾は打ち上げ）。
