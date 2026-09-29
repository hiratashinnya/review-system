---
id: TD-GITGATE-530-002
version: 1
condition: boundary
---
# 大規模 PR の差分全文取得（Issue #530 受入基準1の実測）

## 目的

`pr-reviewer` が、実在する大規模 PR（PR #529・数千行）の差分全文を、rtk を経由したまま欠落なく取得できることを実測で示す。
rtk の既定圧縮表示が実 PR で欠落を起こすこと（Issue #530 の元の問題）の再現も同じログに含める。

## 前提

- 対象 PR は PR #529（マージ済み）。差分は GitHub API の生 diff（rtk・gh の整形を介さない）を正解データとする。
- 実測はメインのチェックアウトが PR #557 反映後の `origin/main` である状態で行う。
- 実ロールの起動は**読み取り専用**に限る。コメント・review・merge・checkout・push・karte・GitHub への書込みは行わせず、実測の前後で PR の comments／reviews 件数が変わらないことを確認する。
- 実測は rtk の設定・hook を変更せず、rtk の迂回・無効化を行わない。

## 手順

1. 正解データ（T1）：GitHub API の生 diff を取得し、行数・バイト数・`diff --git` 見出し数・SHA-256 を記録する。
2. T2：`rtk gh pr diff 529 --no-compact` の出力が T1 と SHA-256 で一致することを確認する。
3. T3（対照）：`rtk gh pr diff 529`（既定の圧縮表示）の出力の bytes／lines／切り詰め表示の有無を記録し、欠落を確認する。
4. T4：`python3 -m gitgate show-pr-diff 529` の返すマニフェスト（path／bytes／lines／sha256）が保存ファイルの実測と一致し、保存ファイルが T1 と SHA-256 で一致することを確認する。
5. T5：`pr-reviewer` ロールの Bash 入力に対する `agent-command-gate.sh` の判定（`rtk gh pr diff <N> --no-compact` の許可、rtk 無し・`--no-compact` 無し・`command` ラップの拒否）を記録する。
6. T6：実際の `pr-reviewer` ロールを読み取り専用で1回起動し、`rtk gh pr diff 529 --no-compact` の1コマンドで全文を取得・読了できるかを報告させ、報告値（見出し数・最初／最後の見出し・末尾行）と、ハーネスが保存したファイルの SHA-256 を主文脈が正解と照合する。

## 期待結果

- T2・T4 の出力は T1 と SHA-256 で一致する。T3 は切り詰め表示を伴い大きく欠落する（rtk 既定表示の問題の再現）。
- T5：`rtk gh pr diff <N> --no-compact` と `gitgate show-pr-diff <N>` は許可され、それ以外の形は拒否される。
- T6：ロールはゲートに拒否されず、1コマンドで全文を読了でき、報告値が正解と一致し、保存ファイルは T1 とバイト完全一致する。読めなかった場合は契約の自己申告 finding を出す（今回は不要となる想定）。
