---
doc_type: minutes
scope: org
extends: null
version: 1
rules:
  - id: typo
    title: 誤字・表記ゆれ
    category: clarity
    severity: info
    determinism: deterministic
    enabled: true
    override: open
  - id: action-item-format
    title: アクションアイテムの体裁
    category: structure
    severity: warning
    determinism: tradeoff
    enabled: true
    override: tighten-only
  - id: decision-clarity
    title: 決定事項の明確さ
    category: completeness
    severity: warning
    determinism: judgment
    enabled: true
    override: tighten-only
  - id: missing-owner
    title: 担当者・期限の欠落
    category: completeness
    severity: error
    determinism: judgment
    enabled: true
    override: tighten-only
---

# 議事録評価基準（全社デフォルト）

会議の議事録に共通で適用する基準。決定事項・アクションの追跡可能性を重視する。

## typo — 誤字・表記ゆれ

明らかな誤字脱字や、同一語の表記ゆれ（例：「サーバー」「サーバ」混在）がないかを評価する。

**チェック観点**
- 変換ミス・脱字がないか
- 用語の表記が文書内で統一されているか

**良い例**
- 「データベース」で統一されている。

**悪い例**
- 同じ文書内で「データベース」「DB」「データーベース」が混在。

## action-item-format — アクションアイテムの体裁

アクションアイテムが、後から追える形式（誰が・何を・いつまでに）で書かれているかを評価する。

**チェック観点**
- リスト形式で抽出しやすいか
- 「検討する」など主語・期限が曖昧な表現になっていないか

**良い例**
- `[ ] 山田：API 仕様書を 6/10 までにレビュー`

**悪い例**
- 「API のことは追って対応」

## decision-clarity — 決定事項の明確さ

会議で何が決まったのかが、読み手に一意に伝わる形で書かれているかを評価する。

**チェック観点**
- 「決定事項」が本文から識別できるか（見出し/ラベル）
- 決まったこと・保留したことの区別がつくか

**良い例**
- 「【決定】認証は OAuth2 を採用。【保留】MFA の要否は次回」

**悪い例**
- 「OAuth2 が良さそうという話になった」（決定なのか議論段階なのか不明）

## missing-owner — 担当者・期限の欠落

アクションアイテムに担当者または期限が欠けていないかを評価する。欠落は追跡漏れに直結するため error。補完案は AI が出すが確定は人間。

**チェック観点**
- 各アクションに担当者が割り当てられているか
- 期限（少なくとも目安）があるか

**良い例**
- `[ ] 佐藤：見積もり提出（6/12）`

**悪い例**
- `[ ] 見積もりを出す`（担当・期限なし）
