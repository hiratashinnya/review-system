---
id: TD-issue-start-452-f29-full-fail
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f29-full-fail.txt
---

# F-452-29 full unittest FAIL TR

変更後のfull unittestは1877件中2件FAIL（skip13）だった。失敗は変更対象外の
`tests/unit/test_codex_rate_limit_api.py` watcher parser 2件で、`OK REACHED=1 ...`を期待したが
`FALLBACK`になったもの。F-452-29のfocused/関連テストは別PASS evidenceとして扱い、この失敗を
成功へ読み替えない。
