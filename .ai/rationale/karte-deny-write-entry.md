# karte / feedback 台帳の deny に Write 専用エントリを置かない理由

## 経緯
- Issue #522 レビュー F-522-10 で、`.claude/settings.json` の `permissions.deny` に
  `Write(/tmp/_karte/**)` と `Write(/.ai/feedback/**)` を追加した。`Edit` 1件だけでは
  `Write` による丸ごと上書きが通りうる、という懸念と、パターンの錨・ツール経路の挙動が
  版に依存しうることへの備えが動機だった。
- 同レビューの実測（F-522-04／F-522-11）で、`Edit` エントリのみの状態でも
  メインチェックアウトへの `Write` は "File is in a directory that is denied by your
  permission settings." で拒否されることが分かっていた。つまり `Write` エントリは
  実際には不要だった。
- PR #688（2026-10-31）：Claude Code が "Deny rule Write(...) never matches · use Edit(...)"
  と警告したため、`Write` 専用エントリを削除した。`Edit` 規則が `Write` も覆う。

## 現行の扱い
- deny は `Edit(/tmp/_karte/**)` と `Edit(/.ai/feedback/**)` のみ。
- `tests/unit/test_karte_cli.py` / `test_feedback_ledger.py` は `Write(...)` エントリの
  再混入を `assertNotIn` で防ぐ。
- 「Edit が Write も覆う」こと自体は実測記録と Claude Code の仕様に依拠し、テストでは
  機械検証できない。
