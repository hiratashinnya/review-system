# Issue #714「issue_start／karte 周りの記述がコードと食い違っている箇所を是正する（入れ子委譲・bind・GATED_ROLES・karte check）」

- URL: https://github.com/hiratashinnya/review-system/issues/714
- 状態: open（2026-11-18取得）
- 本文: 7713文字/ 115行。全文: `../raw/issues-2026-11.jsonl`
- AC: 12件（未チェック: 12）
- Issue参照: #706, #712, #517, #519, #516, #338, #423, #425, #6, #614
- PR参照: #712, #516, #425
- 主見出し: ## 目的・背景 | ## 対象 harness | ## 現状と根拠 | ### (1) 入れ子委譲の説明がコードと逆（実害あり・優先） | ### (2) `.ai/Individually-managed-lists.md` #6 の記述（軽微） | ### (3) `issue_start/gated_roles.py` docstring（実害なし） | ### (4) `karte check` の未クローズ Attempt 検査と文書のずれ（実害あり・軽微・関連） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（実行環境の制約により自動設定できず・要手動設定）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- 同じ前提（入れ子委譲待ち）を置いている他の箇所（`入れ子` の grep で出現。直すか残すかは未判断）:
- - 実体: `issue_start/subagent_hooks.py` `run_bind`（L357–）は worktree を新規に割り当てない。起動済みの dispatch の worktree を `resolve_worktree_for_agent` で解決し、所有台帳の `open` エントリへ束縛して `running` にする（docstring「起動した dispatch の worktree を所有台帳へ束縛する（`open` →
- - 同 docstring の L5・L12 は Task/Agent dispatch の呼び出し元判定を `issue_start/gate.py` としているが、現在の判定は `issue_start/gate_dispatch.py`（`gate.py` は `GATED_ROLES` を import するのみ）。併せて確認する。
- - (1) 上記の記述をコード（`gate_dispatch.py` の拒否）に合わせる。入れ子委譲を前提にした他の記述は、直す／残す（理由付き）を1件ずつ判断する。保留（`running` 維持）の説明が今も有効な経路かを再確認し、結論を記録する。入れ子委譲を許していた時期の経緯（#423／#425／#517）は削除せず `.ai/rationale/` へ移す案を検討する（`.claude/rules/01-principles.md`「PR8「消さな
- - [ ] (1) 入れ子委譲を前提にした他の記述（上記の出現箇所）について、直す／残す（理由付き）の判断が記録されている。
- - [ ] (2) `.ai/Individually-managed-lists.md` #6 の概要が `run_bind` の実体（所有台帳の `open` エントリへ束縛して `running` にする）と一致している。
- - 関連（open・参照のみ）: #614（`karte check` の診断対象 finding の範囲。(4) とは別部位）
- - parent / sub-issue / blocked-by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
