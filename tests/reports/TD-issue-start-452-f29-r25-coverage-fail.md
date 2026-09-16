---
id: TD-issue-start-452-f29-r25-coverage-fail
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f29-r25-coverage-fail.txt
---

# F-452-29 round 25 coverage FAIL TR

coverage 実行はテスト開始前に環境要因で停止した。既定 uv cache は
read-only のため lock 作成不可、専用 `/tmp` cache はネットワーク/DNS
不可のため `coverage` wheel を取得できなかった。pip による導入や既存
環境の変更はしていない。機能テストの PASS を coverage PASS へ読み替えず、
HTML report も未生成として記録する。
