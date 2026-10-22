# codex-review — 設計経緯・制約（rationale・非規範）

> **これは規範ではない。** 正本は `.claude/skills/codex-review/SKILL.md` であり、本文はこの Claude 専用 skill の設計背景を保管する。

この skill は in-repo の Claude review を置き換えるものではなく、別モデルファミリの第二意見を追加で得るための入口として設計した。`pr-reviewer` は in-repo の review／コメント／merge を担い、`agy-delegate` は agy 直接実行ラッパー経由の委譲を担うため、`codex-review` は `codex exec` を使う OpenAI CLI 経路に限定している。

別プロセスで実行するため、Claude の token/session limit に影響しない追加のレビュー経路になる。ただし `codex` CLI、ChatGPT login、ローカル rollout 保存先に依存するため、クラウドやヘッドレス実行へ移植しない。この配置・非移植判断は `.ai/Individually-managed-lists.md` にも記録されている。

## cyber フィルタ flag 時の回復手順の改訂（2026-10-12）

旧手順は、flag 後に新規セッションで防御レビュー形式へ言い換えて再提出し、なお最終応答が得られなければ「直近の日付ディレクトリ」の `rollout-*.jsonl` を読む、としていた。これは 2026-07-28 のオーナー確定（rollout 回収は自分の `thread_id` に束縛された1ファイルに限る・flag 後の再提出は同一セッションの言い換えも新規セッションでの流し直しも迂回）と食い違っていた。また「直近の日付ディレクトリ」は実行に束縛されないため、同日の別セッションの所見を当該レビューの所見として報告しうる。

PR #615（Issue #605）で `silent-failure-diagnosis` の D0 が「ツール資産側に D0 の例外としての承認記録がある回復手順だけを、記載の範囲で実行する」と確定したのを受け、F-605-06 に対するオーナー判断（2026-10-12）により、同 PR で `.ai/troubleshooting/codex-review.md` の当該節を D0 と 2026-07-28 の確定に合わせた。防御レビュー形式は flag 後の回復手段から、最初の提出時の観点プロンプトの書き方へ位置づけを移した。PR #260 が含んでいた `codex-review` の安全実行契約の再実装は Issue #575 の Out of scope であり、この改訂でも行っていない。範囲は旧手順と D0・2026-07-28 の確定との食い違いの解消に限る。

## rollout 回収手順の前提の実機確認（2026-10-12）

`.ai/troubleshooting/codex-review.md` の回収手順は、次の2点を前提にしている。(a) `codex exec` の出力冒頭に `session id:` が出力され、その値が当該実行の `thread_id` になる。(b) `~/.codex/sessions/YYYY/MM/DD/` に作られる `rollout-*.jsonl` のファイル名の末尾が `thread_id` と一致する。これを PR #615（Issue #605）のレビュー F-605-16 を受け、主文脈が実機で確認した。

| 項目 | 確認結果 |
|---|---|
| 確認日 | 2026-10-12（確認者は主文脈。Claude Code (AI)） |
| 版 | codex-cli 0.157.0・model gpt-6-luna |
| 実行 | `codex exec --sandbox read-only` に固定プロンプトを1回だけ渡した |
| 出力冒頭 | `session id: 01a12ddc-8930-7a21-bd99-de886c5d8bec` |
| 作られた rollout | `~/.codex/sessions/2026/10/12/rollout-2026-10-12T11-06-30-01a12ddc-8930-7a21-bd99-de886c5d8bec.jsonl` の1ファイルだけ。ファイル名の末尾が `session id` の値と一致した |

確認できたのは上記の版・1回の実行における前提 (a)(b) と「当該実行に対応する rollout がちょうど1つ作られること」までである。cyber フィルタが実際に flag したときの `review.txt` の形、およびその rollout に中間発話が含まれて所見を回収できることは、この確認の対象に含まれない。`codex-cli` の版が変わった場合は、`session id:` の出力位置とファイル名の規則を再確認する。手順書側は前提が崩れたとき（`thread_id` を読めない、または該当ファイルがちょうど1つに定まらない）に回収を試さず停止する形になっている。


履歴: #606 より前の agy-delegate は agy MCP 経由で Gemini へ委譲していた。現行経路は直接実行ラッパーである。
