---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-96c904d-related-fail.txt
---

# 目的

Issue #452改訂契約について、native single-file aliasを含むpermission profileとsupervisorの
関連回帰テストを実装後のhost境界で検証する。

# 前提

- production commandはnative executableを`/run/issue-supervised/codex`へ単一read-only bindする。
- child PATHは`/usr/bin:/bin`のままとし、Node・元install tree・auth/runtime・networkを公開しない。
- Claude、外部AI、model APIは使用しない。

# 手順と期待結果

1. `test_codex_supervisor_shrink`と`test_codex_supervisor`をhost境界で実行する。
2. synthetic active-probe fixtureもproductionの`/run` aliasとprivate `/tmp`を表現する。
3. すべての関連テストがPASSする。

## 実測

- ヘッダ: TD version 6 / implementation commit `96c904dc91f7f76971ab199d3a5b1dc86c0e82f6` / prompt template version: repository revision / baseline content hash: repository revision / 2026-09-10 / Linux host boundary, Python 3.12.3
- ログ: `tests/logs/TD-issue-start-452-96c904d-related-fail.txt`
- 結果: 95件中1件FAIL。fixtureに`/run`と`/tmp`の2つのprivate tmpfsが必要になった一方、旧assertionが全`--tmpfs`数を1と期待していた。
- 根本原因: production-shaped fixtureへの横展開時に、alias用`/run` tmpfsを追加した後の構造的期待値を更新しきれていなかった。
- 対処: `/run`と`/tmp`が各1回であることを独立にassertし、production設定は変更しない。これはFAIL履歴でありPASS証拠へ転用しない。
