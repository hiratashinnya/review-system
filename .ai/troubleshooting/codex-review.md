# codex-review — 回復手順

## cyber フィルタで最終応答が置き換わった

症状は `review.txt` の末尾が `ERROR: This content was flagged for possible cybersecurity risk...` になること。`> review.txt 2>&1` の捕捉失敗や Claude の session limit と決めつけない。これはセキュリティ判定による正しい拒否であり、[silent-failure-diagnosis](../skills/silent-failure-diagnosis/SKILL.md) の D0 に該当する。

**再提出しない。** 同じセッションでの言い換えも、新規セッションでの流し直し（防御レビュー形式へ書き換えたプロンプトでの流し直しを含む）も、flag 後の再提出であり迂回に当たる。防御レビュー形式は flag 後の回復手段ではなく、最初の提出から使う観点プロンプトの書き方である（`.claude/skills/codex-review/SKILL.md` の標準手順1）。

flag 後に行ってよいのは次の2つだけである。

1. **自分の実行の rollout 1ファイルから所見を回収する。**
   - `review.txt` の冒頭に出力された `session id:` の値を、今回の実行の `thread_id` とする。
   - `~/.codex/sessions/YYYY/MM/DD/` 配下で、ファイル名がその `thread_id` で終わる `rollout-*-<thread_id>.jsonl` の1ファイルだけを読み、中間発話から所見を回収する。
   - `review.txt` から `thread_id` を読めない場合、または該当ファイルがちょうど1つに定まらない場合は、回収を試さず2へ進む。「直近の日付ディレクトリ」「最新の rollout」のように実行に束縛されない指定で探さない。同日の別セッションの所見を、当該レビューの所見として取り込むおそれがあるため。
2. **停止して報告する。** flag の事実と、回収できなかった範囲（未レビューの範囲）を明示する。

回収できた所見は Claude 側レビューと統合し、Codex 由来であることと rollout からの回収であることを明示して報告する。

**D0 の例外としての承認記録**：上記1の rollout 回収は、`silent-failure-diagnosis` の D0 の例外である。承認者はオーナー、承認日は 2026-07-28、範囲は自分の `thread_id` に束縛された1ファイルに限る。flag 後の再提出はこの例外に含まれない。本手順書への記載は、PR #615 の F-605-06 に対するオーナー判断（2026-10-12）による。

Trusted Access for Cyber の登録は無課金方針とオーナー認可が必要なため、認可がない限り選択しない。

## CLI または認証が利用できない

`which codex` と `codex exec --help` で CLI の存在を確認する。クラウド／ヘッドレスで CLI や ChatGPT login が使えない場合は実行を試さず、環境制約と未実施理由を報告する。`~/.codex/sessions` が利用できない場合も rollout 回収を試さず STOP とする。

repo supervisor経路ではcanonical `~/.codex/sessions`を直接共有せず、main worktreeの
`tmp/_codex_sessions/<task-key>/sessions`を同じmount先へtask単位でbindする。initial/resumeでmarkerが
継続しない場合は、このsourceの欠落・symlink・modeとouter commandの`--bind`を確認し、fresh threadへ置換しない。
clean hostではsupervisorが非symlinkの`~/.codex/sessions` targetを作成するため、未存在を手作業で事前作成せず、
作成失敗reasonとHOMEの所有権を確認する。workspace shellからtask markerを書換できた場合は隔離失敗として停止する。
