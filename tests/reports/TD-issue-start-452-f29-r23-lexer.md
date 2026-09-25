---
id: TD-issue-start-452-f29-r23-lexer
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f29-r23-lexer.txt
---

# F-452-29 round 23検証結果

## 対象

- 実装: `issue_start/codex_launch_intent.py` の deterministic handoff path lexer
- 回帰: `tests/unit/test_issue_start_gate.py` の Issue/karte × implementer/fixer 境界
- 設計記録: `tests/designs/TD-issue-start-452-f25.md` version 5
- changeset: `adc5f6d`

## 結果

- focused/related: 204 PASS、skip 11
- asset parityを含む関連テスト: PASS（既存39 assets、MISSING 0）
- lexer matrix: file 4096通り、directory 1024通り、HTML entity 3通り
- coverage full: 1878 PASS、skip 9
- coverage: TOTAL 85%（9460 statements / 1407 missed）
- coverage HTML: `htmlcov/index.html`生成済み（未commit）

## F-452-29受入

pathの先頭から末尾までを一つの決定的lexerで読み、shell実行・展開を行わずに
quote/backtick・HTML entity、POSIX/Windows separator、root側dot・重複separator、
quoted component内separatorを正規化した。`"tmp"/_handoff/attacker.yaml`、
`tmp/"_handoff/"/attacker.yaml`、各component/filenameのquote組合せを両roleの
source検査でfail-closeできる。途中fragmentのseparatorをterminal扱いせず、
`tmp/_handoff/archive/`等の候補全体がdirectoryで終わる表現、bare directory prose、
一般placeholder、通常コード断片は許可し、F-452-25〜28のcanonical facts/path exact-one
契約を維持した。

通常full unittestのrate-limit watcher 2件FAILは別FAIL TRへ記録し、coverage fullで
PASSになった結果へ読み替えていない。
