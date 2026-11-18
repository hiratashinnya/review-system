# Issue #833「gh-create-issue の SubagentStop フックが receipt を書かない（6 dispatch で 0 件）原因の是正と、fallback 提示契約の見直し」

- URL: https://github.com/hiratashinnya/review-system/issues/833
- 状態: open（2026-11-18取得）
- 本文: 5679文字/ 93行。全文: `../raw/issues-2026-11.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #632, #694, #812, #227, #269
- PR参照: なし
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ### 成果 A の root cause 仮説（いずれも未検証） | ## 再現手順・期待・実際（成果 A） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 調査記録（2026-11-16）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- Claude Code（`.claude/settings.json` の SubagentStop 登録、`.claude/hooks/subagent-draft-display.sh`、`draft_display/`、`.claude/skills/gh-create-issue/SKILL.md`、`.claude/agents/gh-create-issue.md`）。Codex／GitHub Copilot へは移植していないロールなので対象
- - 成果 B: fallback 時の提示を、全文ではなく「オーナーが決める事項」中心にする契約へ改める。A が直っても、handoff が hook 出力上限（9,000 serialized chars）を超えれば同じ fallback になる【コード確認: `draft_display/stop.py` L13・L22・L51】。数百行の handoff が実際に上限を超えるかは【未確認・推測】。
- - 6 回 dispatch（draft 3＋作り直し 3）で handoff `.md` は書かれたが `.receipt.json` は 0 件。SubagentStop によるチャット表示も無かった。
- - `.claude/settings.json` L81-90: matcher `gh-create-issue` → `subagent-draft-display.sh` → `python3 -m draft_display stop`。
- - `draft_display/stop.py` L39-40: `agent_type` 不一致は無言で return（stderr も receipt も無し）。L41-44: `last_assistant_message` に `HANDOFF: tmp/_handoff/gh-create-issue--<key>.md` 行が無いと stderr に `NO_HANDOFF_LINE` を出すだけで receipt を書かない。
- - `draft_display/handoff.py` `_open_handoff_dir`: `tmp` と `_handoff` を `O_NOFOLLOW` で開く。`write_receipt` は `O_EXCL` で作成し、失敗は全て False を返すだけ。
- - 読んだ範囲の `tests/unit/test_draft_display.py`（冒頭80行）はモジュール直呼びで、バックグラウンド／SubagentHandback 経由の実 payload を使う検査は確認していない。
- - 成果 B の現行契約: `.claude/skills/gh-create-issue/SKILL.md` §2 は receipt が無い／読めない／`fallback_required` なら handoff を Read して全文をそのまま提示し、表示済みでも確認できないとオーナーが述べたときは要約で代替しないと定める。`.claude/agents/gh-create-issue.md` の handoff 節順では「オーナー確認事項」は5番目
- - (e) フック起動・例外（`python3` 不在、`CLAUDE_PROJECT_DIR` 未設定で `subagent-draft-display.sh` L12 が cwd 依存の `git rev-parse` に戻る＝#694 項目7と同形）。`draft_display/__main__.py` は例外を stderr のみに出す。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
