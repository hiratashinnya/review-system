# レートリミット自動再開フック

レートリミット(`StopFailure` / `error_type: rate_limit`)を検知し、**WSL 環境でのみ**
リセット後に対話セッションを自動再開する仕組み。**クラウド(スマホ版)では無害な no-op**。

## 構成

| ファイル | 役割 |
|---|---|
| `on-rate-limit.sh` | `StopFailure(rate_limit)` フックハンドラ。WSL を積極検知したときだけ watcher を切り離し起動。非WSL は no-op。 |
| `resume-watcher.sh` | リセット時刻まで待機し、tmux ペインへ継続メッセージ + Enter を送出して再開。多重起動防止・バックオフ付き。 |

## 設計上の前提(公式仕様)

- `StopFailure` は **出力・終了コードが無視される**ため、フック自身は再開/リトライを
  制御できない。再開は「フックが裏で起動した別プロセス」が担う(二段構え)。
- フック stdin の JSON にリセット時刻は**含まれない**。`resume-watcher.sh` が tmux ペインの
  「resets H:MMam/pm」表記から best-effort で抽出し、取れなければ既定待機(15分)にフォールバック。
- matcher のリスト区切りは **`|`**(`,` はリテラル扱い)。

## 環境ごとの挙動

- **WSL サーバ**: `WSL_DISTRO_NAME` か `/proc/version` の `microsoft|wsl` で検知 → 有効。
  ただし **claude を tmux 内で起動している場合のみ**注入が動く(`TMUX_PANE` を使用)。
  tmux 外なら何もせず abort(ログのみ)。
- **クラウド(スマホ版)**: WSL 検知が外れるため自動的に no-op。常駐プロセスを一切起動しない。

## 利用方法(WSL)

1. tmux 内で Claude Code を起動する: `tmux new -s cc 'claude'` など。
2. レートリミットに当たると `on-rate-limit.sh` が発火し、watcher が起動。
3. リセット時刻 + マージン後、ペインへ継続メッセージが送られセッションが再開する。

## 調整(環境変数)

| 変数 | 既定 | 説明 |
|---|---|---|
| `CLAUDE_RL_CONTINUE_MSG` | `続けて` | 送出する継続メッセージ |
| `CLAUDE_RL_DEFAULT_WAIT` | `900` | リセット時刻不明時の待機秒 |
| `CLAUDE_RL_MARGIN` | `30` | リセット時刻に足すマージン秒 |
| `CLAUDE_RL_MAX_ATTEMPTS` | `6` | 注入リトライ上限 |
| `CLAUDE_RL_RETRY_BACKOFF` | `300` | 再注入バックオフ基本間隔秒 |

## ログ

`~/.claude/rate-limit-recovery/hook.log` と `watcher.log`。

## 要検証(実機 WSL)

- `StopFailure(rate_limit)` がサブスクの「セッション上限(5時間枠)」でも発火するか
  (API 429 系のみの可能性)。1回踏ませて `hook.log` を確認すること。
- tmux ペインのリセット時刻表記が想定フォーマットか(`resets 3:45pm` 等)。
