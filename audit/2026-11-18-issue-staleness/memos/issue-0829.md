# Issue #829「Codex／agy への作業委譲を既定化し、委譲先レートリミット時の Claude 切替を規範へ定める（設計・レビューは Claude 固定）」

- URL: https://github.com/hiratashinnya/review-system/issues/829
- 状態: open（2026-11-18取得）
- 本文: 4243文字/ 67行。全文: `../raw/issues-2026-11.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #606, #652, #569, #628, #321, #565, #325, #831, #368, #538
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 対象 harness | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- 6. 旧規定の書換え（「現状」の全箇所と全文検索の追加分）。失う経緯（#321 の発端・オーナー逐語）は先に `.ai/rationale/` へ移す（PR8 区分1）。層表へ issue-fixer の行を足す。
- - Parent／blocked-by／blocking：なし。
- - Related：#831（工程外作業の経路）、#606、#652（検証 Issue は blocked-by にしない＝`.ai/skills/issue-pipeline/SKILL.md`「3a/3bと運用検証」）、#565（2026-10-07 のオーナー決定で、`common.md` の降格禁止文を rules 03 へ移す方針。着手順が衝突するので先行側の結果を取り込む）、#368（親にするかはオーナー判断）、#538、#321、#569、#

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
