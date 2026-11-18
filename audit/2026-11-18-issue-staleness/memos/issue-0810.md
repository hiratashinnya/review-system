# Issue #810「[reviewer 取り込み経路の実害指摘3件] Write 検査の相対パス解決・karte 拒否文の誤誘導・申告原本の再試行時の食い違い（#375 / PR #697 再レビュー由来）」

- URL: https://github.com/hiratashinnya/review-system/issues/810
- 状態: open（2026-11-18取得）
- 本文: 8684文字/ 121行。全文: `../raw/issues-2026-11.jsonl`
- AC: 12件（未チェック: 12）
- Issue参照: #697, #375, #792, #801, #802, #803, #797, #129, #696, #800
- PR参照: #697
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### (1) F-375-43: Write フックの `file_path` 検査が相対パスをメイン worktree 基準で解決する | ### (2) F-375-44: `karte` verb 拒否文が `issue-fixer` と `pr-reviewer` で共通になり、`pr-reviewer` を誤誘導する | ### (3) F-375-48: 保護モードの `ingest-reviewer` で、台帳書込みが失敗した再試行で申告原本が台帳と食い違いうる | ## Scope | ### (1) F-375-43 | ### (2) F-375-44 | ### (3) F-375-48 | ## Out of scope | ## 型別の補足（improvement） | ## Acceptance criteria
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 実害が小さい可能性: Write ツールの入力は絶対パス前提で、`.claude/agents/pr-reviewer.md` も handoff を絶対パスで書かせる。`pr-reviewer` は隔離なしの共有作業面で動く（`.claude/hooks/agent-command-gate.sh` の `GH_SUBCOMMANDS_BY_ROLE` コメント「this role shares the primary worktree」）ので、cw
- - 意図的設計である点: 「原本を台帳より先に書く」順序は、`karte/README.md`（`ingest-reviewer` / `decide` / `activate` 節）の「申告の原本は台帳より先に追記する」と、上記コードコメントに記録された意図的な設計である。本 Issue はこの順序を覆す前提ではない。論点は**再試行時に報告内容が変わったときの扱い**だけである。順序を入れ替える案を採るなら、覆す根拠（現行の根拠を否定する新たな根拠）を
- - (1-A) 相対パスを拒否する（絶対パスだけ受け付ける）。利点: Write は絶対パス前提で、`.claude/agents/pr-reviewer.md` とも整合し、基準の取り違えが構造的に消える。欠点: 相対パスで書く既存の呼び出しがあれば拒否される（確認が要る）。
- - 実測で「相対パスでの実害が無い」と分かった場合の（1-C）現状維持と、その根拠の記録も選択肢に含める。ただし AI が単独で「対応不要」と決めない（オーナー判断）。
- - (3-D) 現状維持とし、残余の窓として `karte/README.md` に明記する。
- - #803 項目 (3)（Write パス制限の hook 依存＝フック自体が fail-open になる点）。本 Issue (1) は判定に到達した後のパス解決の食い違いであり、別の論点。
- - 前提: 対象コード（`issue_start/phase_tool_gate.py`・`karte/ingest_review.py`・`karte/handoff_path.py`・`karte/scope_ledger.py` ほか）は PR #697 とその下段 #696 の stack にあり、main へ統合されるまで着手できない。PR #697 は #800 を Closes するため、#800 を blocked-by として設定する（#

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
