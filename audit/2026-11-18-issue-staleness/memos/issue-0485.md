# Issue #485「issue-pipeline ① に Issue 構成の妥当性検査（分割漏れ・集約漏れ）を追加する」

- URL: https://github.com/hiratashinnya/review-system/issues/485
- 状態: closed（2026-11-18取得）
- 本文: 3612文字/ 74行。全文: `../raw/issues-2026-09.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #482, #370, #483, #376, #445, #368
- PR参照: #483
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 該当箇所 | ### 集約漏れの実害は既に別 Issue として認識されている | ### 分割漏れの実害も観測されている | ### 判定に使う概念は #482 が定める | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `.ai/skills/issue-pipeline/SKILL.md` の「① 処置順の原案 → オーナー承認」は、オープン Issue の本文・依存（`depends on` / `blocked by`）・相互参照・同一ファイル群の競合を確認し、依存グラフから**処置順**を決める工程である。見ているのは**順序**だけで、**Issue そのものの構成**（1 Issue が何個の成果を抱えているか、1つの設計判断の材料が何個の Issue に散っ
- 1. オープン Issue の本文、依存（`depends on` / `blocked by`）、相互参照、同一ファイル群の競合を確認する。
- - **#482（起票先の判断規則を `gh-create-issue` skill へ明文化）：blocked by。** 本 Issue の検査基準を定める。#482 の merge 後に着手する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
