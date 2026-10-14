| コマンド | 終了コード | 標準エラー |
|---|---:|---|
| `curl -sI -m 8 https://example.com` | 取得不可（実行前に拒否） | プロセス未起動のためなし。PreToolUse hook の `agent-command-gate` が `curl` を禁止コマンドとして拒否 |
| `getent hosts example.com` | `2` | なし |
| Python の接続確認 | `1` | `PermissionError: [Errno 1] Operation not permitted` |

Python はソケット生成時に失敗し、`NET_OK` は出力されませんでした。ファイル変更はありません。