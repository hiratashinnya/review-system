---
id: TD-issue-start-452-f29-r23-coverage
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f29-r23-coverage.txt
---

# F-452-29 round 23 coverage結果

最終コミット `adc5f6d` で `uv run --with coverage coverage run -m unittest discover -s tests -p
'test_*.py'` を実行し、1878 PASS、skip 9となった。TOTALは9460 statements、1407 missed、
85%。`uv run --with coverage coverage html` で `htmlcov/index.html` を生成した。HTML生成物は
`.gitignore`対象でcommitしていない。通常 full のrate-limit watcher 2件FAILは別TRに保持し、
coverage PASSへ読み替えていない。
