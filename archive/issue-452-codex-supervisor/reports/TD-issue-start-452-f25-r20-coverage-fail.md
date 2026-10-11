---
id: TD-issue-start-452-f25
version: 3
condition: failure
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f25-r20-coverage-fail.txt
---

# 目的

coverage依存取得時の環境失敗を保持し、後続の権限付き再計測PASSへ読み替えない。

# 実測

- sandbox内の初回uv coverage runはDNSでpypi.orgを解決できず、テスト開始前にFAILした。
- 失敗ログは削除・上書きせず保持した。
- worktree-local cacheを使う権限付き同一コマンドは1875 PASS、skip 9、TOTAL 85%で完了した。
