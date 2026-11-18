# Issue #721「karte: argparse の usage error も終了コード 2 になり EXIT_NOT_FOUND と衝突する。README の終了コード契約が usage error を含まず事実と異なる」

- URL: https://github.com/hiratashinnya/review-system/issues/721
- 状態: open（2026-11-18取得）
- 本文: 2820文字/ 56行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #696, #719, #720
- PR参照: #696
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ## 提案挙動（選択肢と推奨） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- karte の終了コードは `karte/exit_codes.py` で `0` OK／`2` EXIT_NOT_FOUND（未検出）／`3` 類似飽和／`4` 前提違反と定義され、「`dsv2` に合わせる」とある。一方 argparse は引数の usage error で終了コード `2` を返す。結果として「`2` は未検出」と読んだ利用者・フックが、実際は引数エラーだったと誤診する余地がある。契約の曖昧さを解消する。
-   - `issue_start/subagent_hooks.py:79` は `karte check` の終了コードを「0=OK / 2=未検出 / 4=前提違反」と依存仕様に記載している。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
