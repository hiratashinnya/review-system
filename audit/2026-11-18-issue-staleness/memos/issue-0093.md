# Issue #93「carrier フィールドの enum 化を検討（値集合の確定と機械強制）— #85/#91 派生」

- URL: https://github.com/hiratashinnya/review-system/issues/93
- 状態: closed（2026-11-18取得）
- 本文: 791文字/ 18行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #85, #91, #88
- PR参照: #85, #91
- 主見出し: ## 背景 | ## 論点 | ## 選択肢 | ## 推奨 | ## 出自
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `carrier`（設計要素の実現担体）は `doc-system-v2/schema/sidecar.schema.json` で **enum 無しの free string**。現状の実使用値は `skill`（05-static 相当の設計ノード）のみだが、description は「将来 code/module 等を想定」とある。
- 1. **free string 維持＋SoT 明示**（現状・暫定）：値集合が未確定のうちは柔軟。ただし機械担保なし。
- 値集合の確定はドメイン判断のため**オーナー確定が前提**。確定でき次第 **選択肢2（enum 化）** を推奨。それまでは選択肢1で運用（CLAUDE.md「機械担保されない閉じ語彙を独断で閉じない」）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
