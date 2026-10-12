# codex-review — 設計経緯・制約（rationale・非規範）

> **これは規範ではない。** 正本は `.claude/skills/codex-review/SKILL.md` であり、本文はこの Claude 専用 skill の設計背景を保管する。

この skill は in-repo の Claude review を置き換えるものではなく、別モデルファミリの第二意見を追加で得るための入口として設計した。`pr-reviewer` は in-repo の review／コメント／merge を担い、`agy-delegate` は agy MCP 経由の Gemini 委譲を担うため、`codex-review` は `codex exec` を使う OpenAI CLI 経路に限定している。

別プロセスで実行するため、Claude の token/session limit に影響しない追加のレビュー経路になる。ただし `codex` CLI、ChatGPT login、ローカル rollout 保存先に依存するため、クラウドやヘッドレス実行へ移植しない。この配置・非移植判断は `.ai/Individually-managed-lists.md` にも記録されている。

## cyber フィルタ flag 時の回復手順の改訂（2026-10-12）

旧手順は、flag 後に新規セッションで防御レビュー形式へ言い換えて再提出し、なお最終応答が得られなければ「直近の日付ディレクトリ」の `rollout-*.jsonl` を読む、としていた。これは 2026-07-28 のオーナー確定（rollout 回収は自分の `thread_id` に束縛された1ファイルに限る・flag 後の再提出は同一セッションの言い換えも新規セッションでの流し直しも迂回）と食い違っていた。また「直近の日付ディレクトリ」は実行に束縛されないため、同日の別セッションの所見を当該レビューの所見として報告しうる。

PR #615（Issue #605）で `silent-failure-diagnosis` の D0 が「ツール資産側に D0 の例外としての承認記録がある回復手順だけを、記載の範囲で実行する」と確定したのを受け、F-605-06 に対するオーナー判断（2026-10-12）により、同 PR で `.ai/troubleshooting/codex-review.md` の当該節を D0 と 2026-07-28 の確定に合わせた。防御レビュー形式は flag 後の回復手段から、最初の提出時の観点プロンプトの書き方へ位置づけを移した。PR #260 が含んでいた `codex-review` の安全実行契約の再実装は Issue #575 の Out of scope であり、この改訂でも行っていない。範囲は旧手順と D0・2026-07-28 の確定との食い違いの解消に限る。

