# プロセス設計 01 — DFD Level 1（STS 分割）

コンテキストの単一プロセスを **STS（Source 入力整形 → Transform 中心変換 → Sink 出力）** で割る。
レビュー本線（P1〜P5）＋育成・ガバナンスのループ（P6）。各層 4〜6 プロセス上限 → L1 は 6。

## Level 1 図

```mermaid
flowchart TB
  User[利用者]
  Reviewer[レビュアー]
  Maintainer[基準メンテナ・org]
  PF[PF・LLM]

  DS1[(基準/ポリシーファイル)]
  DS2[(矛盾チェックキャッシュ)]
  DS3[(finding-commit ワークスペース)]
  DS4[(警告レジャー)]
  DS5[(フィードバック蓄積)]

  P1((P1 受付・正規化))
  P2((P2 基準合成))
  P3((P3 評価))
  P4((P4 検証・仕分け))
  P5((P5 適用・レポート))
  P6((P6 育成・ガバナンス))

  User -->|文書群・参照・型上書き| P1
  P1 -->|型判定依頼| PF
  PF -->|型候補| P1
  P1 -->|対象集合・参照集合・型・scope| P2
  P1 -->|対象・参照| P3
  DS1 --> P2
  P2 -->|照合・更新| DS2
  P2 -->|本文矛盾の判定依頼| PF
  P2 -->|観点パック+メタ表| P3
  P2 -->|観点パック| P4
  P3 -->|プロンプト| PF
  PF -->|findings/unmatched| P3
  P3 -->|findings/unmatched| P4
  P4 -->|🤖/✋/💬/❓ 仕分け済| P5
  User -->|revert要求| P5
  P5 -->|適用・コミット・復元| DS3
  P5 -->|評価レポート・適用結果| User
  P5 -->|要承認diff・要判断原案| Reviewer
  Reviewer -->|判断・対象外フラグ| P6
  P6 --> DS5
  P6 -->|既出判定| DS4
  P6 -->|草案依頼| PF
  P6 -->|観点FB提案・ひな形・警告| Maintainer
  Maintainer -->|編集| DS1
```

## STS の割り当て

| 区分 | プロセス | 役割 |
|---|---|---|
| Source（afferent・入力整形） | P1 受付・正規化 / P2 基準合成 | 生入力を「評価できる形」に整える |
| Transform（central・中心変換） | P3 評価 / P4 検証・仕分け | 観点違反を見つけ、機械的に仕分ける |
| Sink（efferent・出力） | P5 適用・レポート | 自動修正の適用とレポート生成 |
| ループ（育成・ガバナンス） | P6 育成・ガバナンス | フィードバックを基準に還流させる |

## データストア（＝状態）一覧（詳細は [03-state-inventory](03-state-inventory.md)）

| ID | ストア | 内容 | MVP |
|---|---|---|---|
| DS1 | 基準/ポリシーファイル | 観点・メタ・ポリシー（Maintainer が編集） | ○ |
| DS2 | 矛盾チェックキャッシュ | 本文矛盾判定の結果を `content_hash` キーで保持（Q15） | ○ |
| DS3 | finding-commit ワークスペース | 自動適用を finding 単位コミットで保持・revert 源（Q3・内部 git） | ○ |
| DS4 | 警告レジャー | 既出警告の `{rule_id, content_hash, first_seen}`（Q9） | ○ |
| DS5 | フィードバック蓄積 | 却下・対象外・傾向。観点FB提案(O-12)の素材 | △（MVP は最小） |

## プロセス責務（1行）と単一責務性

| P | 責務（1行） | 単一責務か |
|---|---|---|
| P1 | 提出物を「対象集合・参照集合・型・scope」に正規化する | ✕ → L2 分解 |
| P2 | doc_type×scope から観点パック+メタ表を毎回合成する | ✕ → L2 分解 |
| P3 | 観点パックと対象から findings/unmatched を得る | ✕ → L2 分解 |
| P4 | findings を検証・除外し 🤖/✋/💬/❓ に仕分ける | ✕ → L2 分解 |
| P5 | 🤖 を適用し、レポートを組み、revert に応じる | ✕ → L2 分解 |
| P6 | フィードバックを集め、基準変更・ひな形・警告を扱う | ✕ → L2 分解 |

すべて複数責務 → [02-decomposition](02-decomposition.md) で単一責務まで割る。
