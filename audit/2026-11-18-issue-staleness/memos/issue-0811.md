# Issue #811「coverage-html スキルの共通本文が計測対象を「review_system のみ」と書いており、.coveragerc の実際の source と食い違う」

- URL: https://github.com/hiratashinnya/review-system/issues/811
- 状態: closed（2026-11-18取得）
- 本文: 6239文字/ 105行。全文: `../raw/issues-2026-11.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #697, #375, #800, #172, #655, #634, #847, #829, #846, #801, #816
- PR参照: #697, #847, #846, #816
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象 harness | ## Dependencies / Related issues | ## 追記：2026-11-17 JST 現行実装・Open PR 競合調査 | ### 確認事実 | ### 競合リスク評価（推定） | ### 推奨する残作業
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `/coverage-html` スキルの共通本文は、カバレッジの計測対象を「`review_system` のみ」と説明している。一方、実体の `.coveragerc` は `review_system` 以外のパッケージも `source` に指定している。利用者（人・AI）が共通本文を読んで計測対象を取り違え、`issue_start` など汎用ハーネス側の計測の有無を誤って前提にする状態を解消する。
- - parent / sub-issues / blocked-by / blocking: なし。
- - 関連 #655（open）: 同じ `.ai/skills/coverage-html/SKILL.md` の手順・出力先・description・done 条件を編集する（Scope 5）。本 Issue が扱う計測対象の記述は別の事実であり、設計判断は互いに影響しない。ただし L3 など同じ行を触りうるため、後から merge する側が先行側へ追従する前提で進める。実行順の依存ではないので blocked-by は設定しない。
- ## 追記：2026-11-17 JST 現行実装・Open PR 競合調査
- > この節は起票時の本文を変更せず、後日確認した事実・評価・推奨を追記するもの。上の「#655（open）」および旧行番号・旧文言は**起票時点のスナップショット**であり、現状を表さない。
- - 現行 `.ai/skills/coverage-html/SKILL.md` に、起票時に指摘した「`review_system` のみ」という文字列は**存在しない**。現在の本文は作業面外の coverage 出力・テストの parity 比較を説明する構成へ変わっている。
- - 2026-11-17 JST に確認した Open PR は以下の3件で、各 PR の**変更ファイル一覧**に `.ai/skills/coverage-html/SKILL.md` および `.coveragerc` は含まれない。
-   - [PR #846「draft: review round 0件記録の基盤を追加する (#801)」](https://github.com/hiratashinnya/review-system/pull/846)：56ファイル
- **着手順の判断：** Open PR の統合待ちは不要。現行 main を起点に小さな独立 PR として実装することを推奨する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
