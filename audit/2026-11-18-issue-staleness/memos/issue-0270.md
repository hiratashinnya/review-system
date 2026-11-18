# Issue #270「settings.json のフック登録で ${CLAUDE_PROJECT_DIR} が未引用（両フック・fail-open 経路）」

- URL: https://github.com/hiratashinnya/review-system/issues/270
- 状態: closed（2026-11-18取得）
- 本文: 2624文字/ 72行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #273, #259, #260, #268
- PR参照: #259
- 主見出し: ## 概要（指摘 259-1・深刻度 BLOCKER／実発火なし） | ## 対象箇所（確認済み・2026-07-29 時点） | ## 折込原因 | ## なぜ今回の PR で直さず Issue に分離したか | ## 処置方針（採用＝対案 c：両フックまとめて修正） | ### 検証（done 条件） | ## 対案とメリデメ（不採用） | ## 参考
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- **検査されないまま素通り**する＝fail-open。両フックとも「必ず通る」ことが前提の安全機構なので、起動経路の失敗は最も致命的な壊れ方になる。
- - [ ] `.claude/settings.json` が妥当な JSON である（`python3 -c "import json;json.load(open('.claude/settings.json'))"`）。
- | (b) 既存フックに合わせて放置 | 一貫性は保たれる | fail-open の穴が残る。修正コストがほぼゼロなのに放置する合理性が薄い |
- - Claude Code のフック契約：**exit code 2 のみがツールをブロックする**。その他の非0終了はブロックしない（fail-open）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
