# doc-system-v2 Phase Plan Snapshot

2026-07-08 時点の doc-system-v2 棚卸し結果、Phase 1 の実施結果、後続フェーズの推奨順序を記録する。

## 棚卸しサマリ

- 初回棚卸し時点の GitHub open Issue は 15 件。
- dashboard の判断待ちは open FND 12 / open Q 1 / deferred PEND 1。
- Phase 1 完了後の dsv2 実測は 598 ノード、drift 0。
- Phase 1 完了後の prompt-coverage は欠落 0 件。

## Phase 1 実施結果

- #129: PR #133 で完了。`agent-command-gate.sh` の fail-open / false negative / false positive を修正し、レビュー指摘後に `gh --repo/-R pr merge` 系の抜けも解消。
- #112: PR #134 で完了。`docidx` PROMPT ノードを追加し、SPEC-61 系本文の 13 件表記を 14 件へ整合。
- #114: PR #135 で完了。`prompt_coverage_targets` を `config.yml` 直読みへ変更。
- #115: PR #136 で完了。RULE-032 の PROMPT coverage 判定を `carrier: skill|agent` に拡張。
- dashboard 手動同期: `doc-system-v2/00-dashboard.md` に Phase 1 完了ログ、598 ノード、drift 0、PROMPT coverage 欠落 0 を反映。

## Phase 推奨

### Phase 1

- 完了。#129 → #112 → #114 → #115 → dashboard 手動同期の順で実施済み。

### Phase 2

- #78 と condition / 傘SPEC / open FND を整理する。
- suppress 廃止後続として、分析・設計層の追随を行う。
- #107。

### Phase 3

- #127 / #128。
- #5。
- #6 / #7 / #11。
- #108。

## 主な依存・衝突

- #114 は #115 の前提。
- #78 の前に個別 condition 系 FND を直すと巻き戻る。
- #108 は状態語彙が固まった後がよい。
- #5 の前に #6 / #7 / #11 を個別処理すると再発防止にならない。
