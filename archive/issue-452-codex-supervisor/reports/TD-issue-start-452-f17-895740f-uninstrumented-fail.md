---
id: TD-issue-start-452-f17
version: 1
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f17-895740f-uninstrumented-fail.txt
---

# 実測

- 実装commit: 895740f
- command: `python3 -m unittest discover -s tests/unit`
- 結果: 1807 tests、failure 2、skip 13
- 失敗対象: `test_codex_rate_limit_api.BashQueryParsingTests.test_watcher_parses_reached`、`test_codex_rate_limit_api.BashQueryParsingTests.test_watcher_parses_reached_past_epoch`
- 根本原因・対処: 今回のF-452-24変更外のrate-limit watcherが、canned queryに対して`FALLBACK`を返した。失敗は隠蔽せず保持し、coverage付き同一full discovery（1807 PASS、skip 9）とF-452-24関連スイート（172 PASS、skip 4）で再確認した。
