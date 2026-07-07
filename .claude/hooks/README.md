# レートリミット自動再開フック

レートリミット(`StopFailure` / `error_type: rate_limit`)を検知し、**WSL 環境でのみ**
リセット後に対話セッションを自動再開する仕組み。**クラウド(スマホ版)では無害な no-op**。

## 構成

| ファイル | 役割 |
|---|---|
| `on-rate-limit.sh` | `StopFailure(rate_limit)` フックハンドラ。WSL を積極検知したときだけ watcher を切り離し起動。非WSL は no-op。 |
| `resume-watcher.sh` | リセット時刻まで待機し、tmux ペインへ継続メッセージ + Enter を送出して再開。**状態認識ガード**(前景が claude でなければ注入しない/稼働中は注入しない。アイドルなら注入。制限バナー有無は情報ログのみ)・多重起動防止つき。 |

## Codex CLI 版

Codex CLI には Claude Code の `StopFailure(rate_limit)` と同等のフックを前提にしないため、
tmux ペインを常時監視するラッパー方式を追加した。

| ファイル | 役割 |
|---|---|
| `codex-with-rate-limit-recovery.sh` | 現在の tmux ペイン向け watcher を起動してから `codex "$@"` に `exec` するラッパー。 |
| `codex-rate-limit-watcher.sh` | Codex のレートリミット表示を検知し、リセット後にアイドルな Codex ペインへ `continue` + Enter を送出する。 |
| `CODEX_RATE_LIMIT_RECOVERY.md` | Codex 版の利用方法・環境変数・ログ場所。 |

利用例:

```bash
tmux new -s codex '/home/hiras/ws_claude/review-system/.claude/hooks/codex-with-rate-limit-recovery.sh'
```

`.codex/` ディレクトリはこの環境では読み取り専用だったため、実体は既存 hook 群と同じ
`.claude/hooks/` 配下に置いている。

## 設計上の前提(公式仕様)

- `StopFailure` は **出力・終了コードが無視される**ため、フック自身は再開/リトライを
  制御できない。再開は「フックが裏で起動した別プロセス」が担う(二段構え)。
- フック stdin の JSON にリセット時刻は**含まれない**。`resume-watcher.sh` が tmux ペインの
  「resets H:MMam/pm」表記から抽出する。**取り逃したら短間隔で再取得をリトライ**する
  (watcher がバナー描画より先に起動する競合対策)。最後まで時刻を取れず制限バナーだけ
  観測できた場合は、**当てずっぽうの時刻発火はせずバナー消滅(=リセット発生)を待って**注入する。
  バナーを一度も観測できなければ注入しない(誤発火防止)。旧「既定15分の盲目待機で早撃ち」は撤去。
- matcher のリスト区切りは **`|`**(`,` はリテラル扱い)。

## 環境ごとの挙動

- **WSL サーバ**: `WSL_DISTRO_NAME` か `/proc/version` の `microsoft|wsl` で検知 → 有効。
  ただし **claude を tmux 内で起動している場合のみ**注入が動く(`TMUX_PANE` を使用)。
  tmux 外なら何もせず abort(ログのみ)。
- **クラウド(スマホ版)**: WSL 検知が外れるため自動的に no-op。常駐プロセスを一切起動しない。

## 再開判定の安全設計(稼働中セッションへの割り込み防止)

注入は同じペインへ `tmux send-keys` で送るため、**再開後に動いている Claude へ二度目を撃つと作業を割り込んで壊す**。これを防ぐため watcher は **状態認識** で動く:

- **大原則**: リセット待機後、ペインが**アイドル(作業中でない)なら注入して再開する**。
- **前景コマンドガード（最優先）**: 注入先ペインが**生存し、かつ前景コマンドが `claude`(=node)系**のときだけ注入する。ペインが閉じている/シェル等に戻っている場合は `続けて` をシェルへ誤送出しないよう**注入せず終了**。`is_working` はペインが消えると capture 空で「アイドル」と誤判定するため、可否は前景コマンド(`pane_current_command`)で確定させる（許可パターンは `CLAUDE_RL_PANE_CMD_RE` で調整可）。
- **稼働中ガード**: ペイン末尾(入力欄フッタ付近・末尾8行)に中断ヒント(`esc to interrupt` 等)が見えたら「もう再開して動いている」とみなし**注入しない**（稼働中セッションへの割り込み防止）。
- **制限バナーは注入の必須条件にしない（情報ログのみ）**: リセット後は制限バナーが消えるため、「バナーが見える時だけ注入」にすると**注入すべきタイミングで必ず弾かれ、自動再開が機能しない**（2026-07-01 の実機不調の真因）。バナー有無は末尾15行で情報として記録するだけ。
- **誤爆対策**: 稼働中判定はスクロールバック全体でなく**末尾8行のみ**を見る（フッタは最下部に出るため）。これにより、再開後の Claude が "rate limit" 等の語を含むファイルを編集・表示しても誤って再注入しない。
- **既定は単発**(`MAX_ATTEMPTS=1`): リセット時刻に1回だけ注入して終了（注入メッセージは送出済みなので、`is_working` が未確認でも再開自体は成立する）。`MAX_ATTEMPTS>1` で効かない場合の再試行。
- 注入後に**作業中になった**ことを確認したら `exit 0`。watcher はデーモンではなく使い捨てプロセス。

## 利用方法(WSL)

1. tmux 内で Claude Code を起動する: `tmux new -s cc 'claude'` など。
2. レートリミットに当たると `on-rate-limit.sh` が発火し、watcher が起動。
3. リセット時刻 + マージン後、**前景が claude かつ非稼働中(アイドル)**を確認してから継続メッセージを送りセッションが再開する（制限バナーの有無は問わない）。

## 調整(環境変数)

| 変数 | 既定 | 説明 |
|---|---|---|
| `CLAUDE_RL_CONTINUE_MSG` | `続けて` | 送出する継続メッセージ |
| `CLAUDE_RL_RESET_POLL_INTERVAL` | `15` | リセット時刻の再取得ポーリング間隔秒(取り逃し対策) |
| `CLAUDE_RL_RESET_POLL_MAX` | `40` | 再取得の最大試行回数(既定 15s×40=10分) |
| `CLAUDE_RL_BANNER_POLL_INTERVAL` | `30` | 時刻不明時にバナー消滅(=リセット)を待つポーリング間隔秒 |
| `CLAUDE_RL_BANNER_POLL_MAX` | `720` | 同上限(既定 30s×720=6時間の安全上限) |
| `CLAUDE_RL_MARGIN` | `30` | リセット時刻に足すマージン秒 |
| `CLAUDE_RL_MAX_ATTEMPTS` | `1` | 注入試行上限(既定1=単発。`>1` で「注入後もアイドルのまま(=効いていない)」のときだけ早撃ち救済リトライ) |
| `CLAUDE_RL_RETRY_BACKOFF` | `300` | 再注入バックオフ基本間隔秒(`MAX_ATTEMPTS>1` 時) |
| `CLAUDE_RL_VERIFY_WAIT` | `20` | 注入後に状態を再確認するまでの待機秒 |
| `CLAUDE_RL_PANE_CMD_RE` | <code>^(claude&#124;node)$</code> | 注入を許可する前景コマンドの正規表現(拡張正規表現・完全一致)。これに一致しない(シェル等に戻った/ペインが閉じた)ときは注入せず終了。native `claude` バイナリや `bun` 等の変則環境では実値を（例 <code>^(claude&#124;node&#124;bun)$</code>）で上書きする |

## ログ

`~/.claude/rate-limit-recovery/hook.log` と `watcher.log`。
実発火時の生 stdin は `~/.claude/rate-limit-recovery/last-payload.json` に保存される(ペイロード形の確認用)。

## 実機検証で判明したこと(2026-06-30)

- **`StopFailure` フックは実レートリミットで発火した**(hook.log に `fired ... session='…'` を確認)。
  matcher は error type で発火を絞るため、発火した時点でその停止は rate_limit と分類されている。
- **ところが stdin の `error_type` が空(`''`)で届いた**(`session_id` は取れるのに `error_type` だけ空)。
  旧 `on-rate-limit.sh` は保険として `error_type != rate_limit` を再チェックしており、
  **空ゆえに skip → watcher を一度も起動しなかった**(＝自動再開が効かなかった真因)。
- **修正**: 発火の絞り込みは matcher に委ね、スクリプトは `error_type` を必須にしない
  (空/不明なら matcher を信頼して継続。明示的に rate_limit 以外のときだけ skip)。
  併せて生 stdin を `last-payload.json` に保存し、次回実発火で正しいフィールド名へ厳密化できるようにした。

## 実機検証で判明したこと(2026-07-01)

- 上記修正により **フック発火 → watcher 起動 → リセット時刻(`resets 10:50pm`)を正しく解析 → その時刻まで待機**、までは成功した(`last-payload.json` は実際の形＝`"error":"rate_limit"`／`"last_assistant_message":"You've hit your session limit · resets 10:50pm"` を採取。フィールド名は `error_type` ではなく **`error`** だった＝matcher を信頼する修正が正解だったことも裏付け)。
- **しかしリセット時刻に到達した瞬間、注入前ガード `is_limit_screen` が false を返し注入せず終了した**(`limit screen NOT confirmed (cleared / already resumed); NOT injecting; exit`)。
  - 真因: リセット後は制限バナーが消える／入力欄より上に出るため、**「バナーが見える時だけ注入」ガードが、注入すべきタイミングでほぼ必ず弾く**。ペインは「アイドルで再開待ち」なのに「再開済み」と誤認していた。
- **修正(本回)**: `is_limit_screen` を注入の必須条件から外し、**アイドル(`is_working`=false)なら注入**へ変更。稼働中への割り込みは `is_working` ガードで防止(不変)。`is_limit_screen` は情報ログ化＋窓を 8→15 行に拡大。ダミーペインで「アイドル→注入／稼働中→非注入」を検証済み。

## 残検証(実機 WSL)

- 次回実発火で **リセット後に実際に `続けて` が注入され対話が再開する**ことを確認する(本回修正の実機確認)。
- サブスクの「5時間枠上限」が `rate_limit` 以外の error type で来る場合、matcher を `rate_limit|...` に広げる要否を確認(現状 `"error":"rate_limit"` を確認済み)。
- tmux ペインのリセット時刻表記が想定フォーマットか(`resets 3:45pm` / `resets 10:50pm` 等・実機で `10:50pm` 解析成功)。
