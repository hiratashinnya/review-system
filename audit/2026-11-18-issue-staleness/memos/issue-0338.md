# Issue #338「dsv2-lookup.md の手順に統制下で必ず deny される python3 -c 例が残っている（FND 起票して是正）」

- URL: https://github.com/hiratashinnya/review-system/issues/338
- 状態: closed（2026-11-18取得）
- 本文: 2571文字/ 75行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #335, #224, #304, #227
- PR参照: #335
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `.claude/agents/dsv2-lookup.md` の作業手順に、**現在の統制下では必ず deny されるコマンド例**が
- 28:   - 例：`python3 -c "import json,sys; m=json.load(open('doc-system-v2/meta.json')); ..."`
- - `verification-author` へ委譲して **FND ノードを起票**する（`doc-system-v2/nodes/04-verification/fnd/open/`）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
