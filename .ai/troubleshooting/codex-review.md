# codex-review — 回復手順

## cyber フィルタで最終応答が置き換わった

症状は `review.txt` の末尾が `ERROR: This content was flagged for possible cybersecurity risk...` になること。`> review.txt 2>&1` の捕捉失敗や Claude の session limit と決めつけず、次を行う。

1. 同じセッションで言い換え再提出せず、新規セッションを開始する。
2. プロンプトを防御レビュー形式へ変更する。「攻撃コマンド文字列を再現しない」「`file:line`、欠陥クラス、修正方針で返す」と指定する。
3. 最終応答が得られない場合、直近の日付ディレクトリの `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` を読み、中間発話から所見を回収する。
4. 回収できた所見は Claude 側レビューと統合し、Codex 由来であることを明示して報告する。

Trusted Access for Cyber の登録は無課金方針とオーナー認可が必要なため、認可がない限り選択しない。

## CLI または認証が利用できない

`which codex` と `codex exec --help` で CLI の存在を確認する。クラウド／ヘッドレスで CLI や ChatGPT login が使えない場合は実行を試さず、環境制約と未実施理由を報告する。`~/.codex/sessions` が利用できない場合も rollout 回収を試さず STOP とする。

