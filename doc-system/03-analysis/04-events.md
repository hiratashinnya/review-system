# イベント

> **型**: E ／ **必須上流**: SPEC（依存辺 ✅）・ACTOR（刺激元 ✅・DD-020）
> 依存方向（DD-017）：トリガ関係は **P→E**（P 側に辺）。E は P へ辺を張らない。
> 系内の定期実行など「アクタなし事象」は事象ではなく FR で表現する。

---

## E-1: 点検要求

<details><summary>⬡ E-1 · v0.5.0</summary>

```yaml
id: E-1
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3.0"
  - to: ACTOR-1
    ref_version: "0.1.0"
  - to: I-1
    ref_version: "0.1.0"
  - to: FND-11
    ref_version: "0.1.0"
  - to: DD-4
    ref_version: "0.1.0"
  - to: FND-92
    ref_version: "0.1.0"
```
</details>

**イベント名**: 点検要求
**入力**: I-1（ノードファイル群）——仕様著者（ACTOR-1）または CI が spec-inspector にノードファイル群を渡してイベントを起こす
**スティミュラス**: 仕様著者（ACTOR-1）またはCIが spec-inspector にノードファイル群（I-1）を渡して点検を起動する（E→ACTOR-1）
**アクション**: P-5（設定読み込み）・P-6（in-graph集合決定）を先行実行し、P-1（パース）→ P-2（RULE検査）・P-3（カバレッジ点検）→ P-4（レポート生成）を順次実行する（各 P が P→E-1 でこの事象に依存）。さらにフラグ選択モード（`--coverage`＝P-3-2 と同様）として、`--export-graph` 指定時は P-8（依存グラフ出力処理）、`--complexity` 指定時は P-9（参照関係複雑度計算処理）を追加実行する（P-8/P-9 が P→E-1 でこの事象に依存・post-mvp）
**レスポンス**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）。`--export-graph` 時は O-4（依存グラフ出力ファイル）、`--complexity` 時は O-5（参照関係複雑度メトリクスレポート）を追加出力する（post-mvp）
**アフェクト**: 人手レビュー前に整合性違反と網羅性穴を機械的に可視化できる

---

## E-2: 著作要求

<details><summary>⬡ E-2 · v0.3.0</summary>

```yaml
id: E-2
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-26
    ref_version: "0.3.0"
  - to: ACTOR-1
    ref_version: "0.1.0"
  - to: FND-3
    ref_version: "0.1.0"
  - to: I-7
    ref_version: "0.1.0"
  - to: FND-7
    ref_version: "0.1.0"
  - to: DD-4
    ref_version: "0.1.0"
```
</details>

**イベント名**: 著作要求
**入力**: I-7（テンプレートファイル群）——仕様著者（ACTOR-1）が著作仕様（型・親ID・辺）とともにテンプレートを参照してイベントを起こす
**スティミュラス**: 仕様著者（ACTOR-1）がノード著作（新規作成または既存改訂）を決定し、著作プロセス（P-7）を起動する（E→ACTOR-1）
**アクション**: P-7 がテンプレート（I-7）を参照しノードを著作する（P-7→E-2 でこの事象に依存）
**レスポンス**: O-3（著作済みノードファイル）——仕様著者（ACTOR-1）が著作成果物として受け取る
**アフェクト**: 型・ID PREFIX・辺・本文フォーマット・RULE チェックリストが揃った状態で著作でき、規約逸脱を構造的に防止できる
