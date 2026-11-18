# Issue #468「issue-pipeline の Copilot / Codex 向け写しが正本から乖離している（staleness 3.9x / 2.3x・PR #465 の②-a 追記が未反映）」

- URL: https://github.com/hiratashinnya/review-system/issues/468
- 状態: closed（2026-11-18取得）
- 本文: 2907文字/ 43行。全文: `../raw/issues-2026-09.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #465, #460, #538, #603, #371, #368, #467, #391, #155
- PR参照: #465
- 主見出し: ## 目的・背景 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 本 Issue の当初の対象は、正本 `.ai/skills/issue-pipeline/SKILL.md` と Copilot / Codex 向けの写しとの乖離だった。当初の staleness 値（Copilot 3.9x / Codex 2.3x）と PR #465 の②-a追記漏れは、起票時点の観測として保持する。現在の作業範囲・完了条件は、後続の方針変更を反映して以下のとおり更新する。
- 起票時の直接の契約差分は、PR #465 が正本の②-aへ加えた Project Status の `In progress` / `Ready` 遷移だった。共通工程を正本から参照する現行構成で、その指示が現在も共通本文に存在するか、Copilot wrapper が参照・固有制約と矛盾していないかを着手時に再確認する。
- - 維持対象の `.github/skills/issue-pipeline/SKILL.md` を、現在の共通本文および #371 の新工程に照らして確認・更新する。
- - [ ] 現行の Copilot wrapper が共通本文を明示的に参照し、現在の工程と規範を適用する入口になっている。
- - #467：asset-parity の CI paths 修正。現在は `.ai/**` 変更時も検査が起動する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
