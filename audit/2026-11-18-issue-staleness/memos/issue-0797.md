# Issue #797「[申告 scope 原本] 待機の取消後に旧 ingest-review で round 1 を書くと、主文脈の scope がレビューア原本より先に台帳へ入る（#375 / PR #697 レビュー由来）」

- URL: https://github.com/hiratashinnya/review-system/issues/797
- 状態: closed（2026-11-18取得）
- 本文: 8481文字/ 119行。全文: `../raw/issues-2026-11.jsonl`
- AC: 9件（未チェック: 0）
- Issue参照: #697, #375, #523, #792, #793, #531, #129, #800, #803, #696
- PR参照: #697
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 読解で確認できたこと | ### オーナー報告（カルテ F-375-21）の最終形の記述 | ### 読解で食い違いを見つけた点（着手時に現物で確認する） | ### 設計上のトレードオフ | ## 再現手順（未実行・着手時に実測する） | ## Scope | ## Out of scope | ## 型別の補足（improvement） | ## Acceptance criteria | ## 対象 harness
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 内容は、レビューアが申告した `scope` の原本が「台帳に入る最初の書き手」にならない経路が、待機の取り消しによって開くこと。元 Issue #375 の追加 AC（第4の観測・#523 のブロッカー要件）は、レビューアの申告 `scope` を主文脈の手を経ずに改変不能な一次記録として残し、round 1 から保護することである。PR #697 の最終形はこの経路だけ、その AC を厳密には満たさない。現状は、後続のレビューア申告による置換を検出して
- - 上記 1 と 2 は、本起票では HEAD のコードで確認し切れていない。`karte/scope_ledger.py` の `arm` の docstring は「`activate` がレビューア初回の前に空の原本を用意する（Issue #375 F-375-03）」と述べ、`.ai/rationale/pr-reviewer.md` も同じ趣旨（「`activate` が空の原本を先に作って保護を前倒しし」）を述べている。一方 `karte/sc
- - 影響: #523 が `scope` の覆しに `override_ref` を要求する前提（round 1 の覆しを機械検出できる）を、この経路では満たせない。検出は事後で、台帳へ先に入った値は取り込み結果の注記を読まない限り見えない。
- - (D) 現状維持（検出と文書化のみ）。
- ## 【2026-11-11・オーナー合意】#523 の前提としての扱い
- - 前提: 対象コード（`karte/ingest_review.py`・`karte/reviewer_policy.py`・`karte/review_expectation.py`・`karte/scope_ledger.py` ほか）は PR #697 とその下段 #696 の stack にあり、main へ統合されるまで着手できない。PR は GitHub の blocked-by の対象外のため、native relation は設定せず、前
- - Blocked by: #800（PR #697 の正規 reviewer trusted ingest が main に統合されてから本 Issue を処置する。native relation は別途設定）。
- - Blocker for: #523（scope 原本の round 1 検出と override_ref の前提。GitHub native relation は別途設定）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
