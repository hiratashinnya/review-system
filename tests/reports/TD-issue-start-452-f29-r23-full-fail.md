---
id: TD-issue-start-452-f29-r23-full-fail
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f29-r23-full-fail.txt
---

# F-452-29 round 23 full unittest FAIL TR

変更後の通常 full unittest は1878件中2件FAIL（skip13）だった。失敗は変更対象外の
`tests/unit/test_codex_rate_limit_api.py` watcher parser 2件で、期待する `OK REACHED`/
`OK EPOCH` 行ではなく `FALLBACK` になったもの。F-452-29のfocused/関連テストと
coverage fullの結果は別証跡として記録し、この失敗を成功へ読み替えない。
