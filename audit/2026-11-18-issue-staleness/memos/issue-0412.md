# Issue #412「pr_merge_gate/blocker_gate: 正当なPRのmergeをMESSAGE_SOURCE_INCOMPLETEで誤ブロック・gh allowlist漏れによる過検知」

- URL: https://github.com/hiratashinnya/review-system/issues/412
- 状態: closed（2026-11-18取得）
- 本文: 4972文字/ 83行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #348, #354, #402
- PR参照: #402
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 1. `gh pr merge` が正当な PR でも `MESSAGE_SOURCE_INCOMPLETE` で拒否される | ### 2. `pr_merge_gate` の classifier が merge と無関係な `gh` サブコマンドまで一律ブロックする | ## Scope | ## Out of scope | ## Acceptance criteria | ## bug: 再現手順・期待結果・実際結果・環境・影響・root cause 仮説 | ## Dependencies / Related issues | ## Project fields（実行環境の制約により自動設定できず・要手動設定）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - リダイレクト・パイプを含む複合コマンドの扱いを見直し、merge と無関係なコマンドまで一律 `CLASSIFIER_UNKNOWN` にしない設計にする（現状の `_split_shell_commands` の `<>(){}` 一律拒否の妥当性を再検討する）。
- - 本 Issue とは別に、PR #402 は本バグの回避策（オーナー自身が GitHub UI 等 Bash 経由の `gh` 以外の経路でマージ）で個別に解消済み・解消予定であり、本 Issue の修正の前提ではない。
- - 再現手順：上記「現状と根拠」の1・2参照。
- - root cause 仮説：上記「現状と根拠」参照（GraphQL/REST 突き合わせの不一致処理、および `gh` サブコマンド allowlist の網羅漏れ）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
