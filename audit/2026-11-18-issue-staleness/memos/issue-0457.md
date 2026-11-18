# Issue #457「improvement(pr-merge-gate): ブロック時メッセージが単一定型文でreason codeごとの状況が伝わらない」

- URL: https://github.com/hiratashinnya/review-system/issues/457
- 状態: closed（2026-11-18取得）
- 本文: 4756文字/ 53行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #434, #456, #428, #431, #412
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠（メッセージ出力処理の棚卸し） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（メッセージ出力処理の棚卸し）
-    - **BLOCK群**（実際にマージ操作と分類され、ポリシー上ブロックされた）: `OPEN_BLOCKER`, `CLOSURE_OPEN_DESCENDANT`, `TARGET_ISSUE_NOT_OPEN`, `PR_NOT_OPEN`, `PR_DRAFT`, `AUTO_MERGE_DENIED`。ここでは「元のmerge操作は送信しません」は事実として正しいが、`reason` コードが何を意味するかがメッセージ内で説明されていない。
- 3. **`_rotate_audit()` 内の stderr 診断（162-169行付近）— `AUDIT_ROTATION_SKIPPED/<code>`・`AUDIT_ROTATED removed=<n>`**。これらは block を伴わない運用診断であり、現状の簡潔な形でも実害は小さいと考えられるが、棚卸しの対象として含める（要否は Acceptance criteria で判断）。
- 関連（判定ロジック自体の issue、本Issueとは別軸）：#428（closed）、#431（open）、#412（closed）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
