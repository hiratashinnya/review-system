---
id: TD-issue-start-452-f29-r21-c2ddf57
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f29-r21-c2ddf57.txt
---

# F-452-29検証結果

## 対象

- 実装: `issue_start/codex_launch_intent.py` のhandoff候補tokenize/normalize
- 回帰: `tests/unit/test_issue_start_gate.py` のIssue/karte×両role variant
- commits: `abcb87c`, `c2ddf57`

## 結果

- focused: 46 PASS
- related: 247 PASS、skip 13
- asset parity: 39 assets、MISSING 0、staleness 13（informational）
- coverage full: 1877 PASS、skip 9
- coverage: TOTAL 85%（9422 statements / 1412 missed）
- coverage HTML: `htmlcov/index.html`生成済み（未commit）

通常fullの2件FAILとcoverage依存取得の環境FAILは別FAIL TRへ保持し、PASSへ読み替えていない。

## F-452-29受入

両roleのIssue/karte snapshotで、`tmp/_handoff/./attacker.yaml`、`..`、重複separator、
filename-only single/double quote・backtick・HTML entity表記を候補としてfail-closeした。
canonical/別role/attacker既存負例、reserved placeholder、F-452-25〜28のfacts/path契約は維持した。
bare directory prose、directory-only `./`/`//`、一般placeholder、通常コード断片は許可し、
host-derived canonical handoff pathはfinal promptでexact 1回を維持した。
