# unittest discovery 回帰確認（#318）

確認日: 2026-10-19。branch `fix/test-discovery-issue318`、remote PR #666 head `d00e5d69192140339f4db9589cc2ad0d30392bc7` を基点に確認。

## 実行結果

| コマンド | 結果 |
|---|---|
| `python3 -m unittest discover tests` | exit 0; 2270 tests, skip 0; 1236.422秒; `OK` |
| `python3 -m unittest discover -s tests/unit -p 'test_feedback*.py'` | exit 0; 123 tests; `OK` |
| `python3 -m unittest discover -s tests/unit -p 'test_issue_start_gate.py'` | exit 0; 65 tests; `OK` |
| `python3 -m maintainability_lint check` | exit 0; violations 0、accepted debt 81件 |

full実行前に独立processで `tests`（2270 tests、loader error 0）と `tests/unit`（2248 tests、loader error 0）を収集した。root discovery と従来の `-s tests/unit` discovery でunit test ID 2248件が `unit.` prefix正規化後に一致した（missing 0、extra 0）。root discoveryにはenvelope tests 22件が追加される。名前を変更したenvelope test 8ファイルの内容はすべて保持されている。

workflowは `python3 -m unittest discover tests` を1回実行し、重複するenvelope専用stepを削除した。time-fixtureとJevのsuiteは個別実行を維持した。focused workflow assertionでコマンドの追加・削除を確認した。

full実行はこの成績書を追加する前に行った。以降、test codeとapplication sourceに変更はない。`maintainability_lint/baseline.json` は未変更（SHA-256 `4ed181bc97774215c91a7fdbc8dbc648222ef5e41b3fcd38828ce303a4643809`）。
