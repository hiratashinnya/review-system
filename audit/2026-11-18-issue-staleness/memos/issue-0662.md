# Issue #662「issue-pipeline の 1a（ac-designer）に、独立レビュー後の是正を同一 branch で継続する契約が無く、是正ラウンドごとに新 branch が作られ旧 branch が残る」

- URL: https://github.com/hiratashinnya/review-system/issues/662
- 状態: open（2026-11-18取得）
- 本文: 4435文字/ 72行。全文: `../raw/issues-2026-10.jsonl`
- AC: 8件（未チェック: 8）
- Issue参照: #655, #409, #371, #652, #537
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 観測（#655） | ### 契約・コード（読取り確認） | ### 未観測の推論 | ### 意図的設計の確認 | ## Scope | ### 設計案の比較と推奨（原案） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 同 :57 は「レビュー後の是正は既存②-c」とするが、`.ai/agents/issue-fixer.md:3` は「pr-reviewer がレビュー指摘を返した後」「既に開いている PR」専用で、SKILL.md:40 は draft PR を 2b の成果とする。1a/1b の plan-reviewer 指摘を②-c の是正者が扱えるかは契約から読み取れない。
- | A2 | issue-fixer を 1a/1b/2a の是正にも拡張する | 既存の `ISSUE_FIX_BINDING_V1`＋adopt-branch を再利用でき、SKILL.md:57 の文言と合う | issue-fixer は PR 前提で karte 診断必須。VD／CP の著作知識と書込権限の拡張が大きく、著作者自身が commit/push する原則と衝突する |
- | A3 | 現状の新 branch 方式（`-rN`）を契約として明文化する（命名・旧 branch の廃棄手順・ledger／receipt の扱い） | 機械側の変更が最小 | 1 Issue に複数 branch が残る運用負債が続き、CP／VD の参照 OID が branch をまたぐ |
- - 正式な parent／sub-issue／blocked-by 関係は設定しない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
