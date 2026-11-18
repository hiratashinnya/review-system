# Issue #802「[#375 子3] Claude pr-reviewer 実機で finding が欠落なく karte へ取り込まれることを実測する」

- URL: https://github.com/hiratashinnya/review-system/issues/802
- 状態: open（2026-11-18取得）
- 本文: 4320文字/ 64行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #375, #800, #652, #697, #371, #527, #409, #368
- PR参照: #697
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 解く質問・調査境界（spike） | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象 harness | ## 型別の補足（spike） | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - PR #697（draft）本文の記載：Claude `pr-reviewer` 実機で finding が欠落なく取り込まれることの実測は未完了。PR #697 の検証は単体テスト（本文記載で 2,879 件成功）と CI であり、実エージェントでの実測ではない。
- - 依存：**#800 を blocked-by**（#800 の close ＝ PR #697 の統合を待つ。実測は実装が default branch に到達してから行う）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
