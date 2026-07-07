---
name: schema-design
description: 読み手起点で構造化 config/criteria ファイルスキーマを設計する。読者列挙、frontmatter と body の二層分離、属性配置、サンプルによる曖昧性解消を扱う。外部設定/基準ファイル形式が必要な時に使う。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

# スキーマ設計（読み手から決める）

構造化ファイル（基準/設定）のスキーマを、読み手起点で決める。
原則：[spec-principles](../spec-principles/SKILL.md)（PR2 2軸）。

## 手順
1. **読み手を列挙**（人／プログラム／LLM 等）し、各々の欲しい形を出す。
2. **二層構成**：フロントマター（機械可読・ルーティング）＋本文（人＆LLM 共用）。
3. **属性を2軸で振り分け**（PR2）：順序ある属性＝機械が自動ゲート／事実性・妥当性＝人が確認。対応モード等の写像は別ファイル（責務分離）。
4. 継承/上書きは「具体が勝つ」機構＋権威は別レイヤ（方向ゲート）。
5. **サンプルで曖昧さを潰す**（境界条件＝多段継承・ロック・本文差し替え）。

## done
- 機械判定と運用ルールが混ざっていないか。
- サンプルで境界条件が検証できているか。

## ノード著作（SCM / CFG）

**フロントマター定義**

```yaml
---
id: SCM-1             # 型 prefix + 連番（下表）。採番後は変更禁止
type: SCM             # 型値（下表から選ぶ。自由記述不可）
labels: []            # 任意タグ（post-mvp / experimental 等）。分類用・RULE 判定に影響なし
scheduled: ""         # 空 = 現フェーズ対象。値あり = 後フェーズ予定（全 RULE がサイレント）
suppress: []          # RULE 抑制リスト。inline comment に理由必須。RULE-007 は抑制不可
---
```

| 型 | id PREFIX | 例 |
|---|---|---|
| SCM | `SCM-` | `SCM-1` |
| CFG | `CFG-` | `CFG-1` |

**共通手順**
1. テンプレ複製：`docs/doc-system/templates/design-static/<type>.md`
2. id 採番：上表の PREFIX + 連番（既存最大 +1）。採番後は変更禁止
3. 必須 edges を追加（下表）。`to` が実在する id か確認（RULE-007: always_error）
4. status: pending から始め、反映確認後に done
5. ref_version（x.y）を参照先バッジの現在 x.y に合わせる（バッジは x.y.z・z は伝播判定に不問）
6. 受け入れ条件を確認（下表）

| 型 | 必須辺 |
|---|---|
| SCM | → SPEC (refines)、→ TERM (see-also) |
| CFG | → SCM (instantiates)、→ SPEC (refines) |

**本文フォーマット**

```
# SCM
[スキーマの目的・対象ファイル形式]
**フロントマター（機械）**: [機械可読・ルーティング属性]
**本文（人/LLM）**: [人間・LLM が読む部分の構造]

# CFG
[このコンフィグが設定する対象・用途]
```

**辺方向の注意**
- `SCM → TERM` の kind は **see-also**（refines ではない）
- see-also 辺の `status` は **`n/a`** 固定（RULE-014）

**受け入れ条件**
- [ ] id 一意、type 一致、edges の to がすべて実在（RULE-007）
- [ ] 接続マトリクス ✅ の辺がすべて存在（RULE-006）
- [ ] see-also 辺の status が `n/a`（RULE-014）
- [ ] ref_version が参照先の現在バージョンと一致（RULE-003/004）
