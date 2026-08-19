# レートリミット自動再開フック

レートリミット(`StopFailure` / `error_type: rate_limit`)を検知し、**WSL 環境でのみ**
リセット後に対話セッションを自動再開する仕組み。**クラウド(スマホ版)では無害な no-op**。

## 構成

| ファイル | 役割 |
|---|---|
| `on-rate-limit.sh` | `StopFailure(rate_limit)` フックハンドラ。WSL を積極検知したときだけ watcher を切り離し起動。非WSL は no-op。**検知時刻を状態ファイルへ記録し、tmux の status-bar へ一瞬フラッシュ**(入力欄には触れない=out-of-band)。 |
| `resume-watcher.sh` | リセット時刻まで待機し、tmux ペインへ継続メッセージ + Enter を送出して再開。**状態認識ガード**(前景が claude でなければ注入しない/稼働中は注入しない。アイドルなら注入。制限バナー有無は情報ログのみ)・多重起動防止つき。**継続メッセージには①の検知時刻・解除時刻・現在時刻・解除済みである旨を自動で埋め込む**(検知時刻を LLM の文脈にも届ける)。 |
| `lib-pane-guard.sh` | 上記2スクリプトが `source` する共有ライブラリ。状態ディレクトリ(`RL_STATE_DIR`)・ペイン前景判定(`rl_is_claude_pane`)・デフォルト正規表現(`RL_PANE_CMD_RE`)・tmux の timeout ラッパ(`rl_tmux`)・ペインID正規化(`rl_pane_slug`)・検知時刻ファイルのパス(`rl_hit_file`)を1箇所に集約(二重実装の drift 防止)。 |

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

## レートリミット認識の取りこぼし対策(2026-07-18)

LLM が「さっきレートリミットに当たったから」と誤って未解除のまま思い込み、サブエージェント
利用等の通常プロセスから逸脱してしまう事象への対策として、以下の2点を追加した。

- **①検知時刻の表示**: `on-rate-limit.sh` が発火した瞬間、tmux ペインへ検知時刻を
  ドラフト表示する(`CLAUDE_RL_ANNOUNCE_HIT=0` で無効化可)。Enter は送らない
  (まだ解除前に新規ターンを送信して即座に再度レートリミットへ突入するのを防ぐため)。
- **②再開プロンプトへの解除時刻・解除済みの旨の明記**: `resume-watcher.sh` が注入する
  継続メッセージを、単なる「続けて」から「レートリミットは解除されました(解除時刻 …
  ／現在時刻 …)。制限は解除済みです。サブエージェント利用などの通常プロセスに戻って
  続けてください。」という明示的な文言に変更した。`CLAUDE_RL_CONTINUE_MSG` を明示指定
  した場合はそのまま使う(時刻注記は付かない)。

### レビュー指摘の是正(同日)

サブエージェントによるコードレビューで①②の実装に以下の欠陥が見つかり、同日中に是正した:

- **ドラフトと継続メッセージの連結防止**: ①のドラフト注入・②の継続メッセージ注入の
  いずれも、注入直前に `tmux send-keys ... C-u` で入力欄をクリアするようにした。
  クリアしないと①のドラフト(未送信)が残ったまま②のメッセージが打ち込まれ、
  1行に連結された壊れた文がそのまま Enter で送信されてしまう。
- **①注入前のペイン検証ガード追加**: `resume-watcher.sh` の `is_claude_pane` と同じ
  考え方で、対象ペインの前景コマンドが `claude` 系であることを確認してから①を注入する
  ようにした(`CLAUDE_RL_PANE_CMD_RE` で調整可)。従来は `$TMUX`/`$TMUX_PANE` が
  非空なことしか見ておらず、前景がシェル等に戻っていても無条件に注入していた。
- **①の tmux 呼び出しに timeout を付与**: `StopFailure` フックの15秒タイムアウト内で
  本来の役目(watcher 起動)まで確実に到達できるよう、①の `tmux display-message`/
  `send-keys` を `timeout 3` で打ち切るようにした。
- **解除時刻不明時の重複表示を解消**: バナー消滅待ちにフォールバックして `reset_epoch`
  を取得できなかった場合、`build_continue_msg()` が「解除時刻」に現在時刻をそのまま
  埋めて重複表示していたのをやめ、その場合は「解除時刻」節ごと省いて
  「(現在時刻 …)。制限は解除済みです。…」の文言にフォールバックするようにした。

### 再レビュー指摘の是正(共有ライブラリ化・マーカー識別クリア・同日2回目)

1回目の是正に対する再レビューで、C-u による無差別クリアや timeout の抜け等が見つかり、
以下のとおり設計を一段深くして是正した:

- **共有ライブラリ `lib-pane-guard.sh` を新設**: `rl_is_claude_pane`・`RL_PANE_CMD_RE`・
  tmux の timeout ラッパ `rl_tmux`・`RL_DRAFT_MARKER` を両スクリプトで共有し、ペイン
  判定ロジックとデフォルト正規表現の二重実装(片方だけ更新して不整合になる drift)を解消。
- **無差別 C-u をやめ「マーカー識別クリア」に変更**: `resume-watcher.sh` は①が付けた
  マーカー(`RL_DRAFT_MARKER`)が入力欄付近(末尾6行)に見えるときだけ C-u でクリアする。
  マーカーが無い(=ユーザーが手打ちした別テキスト)ときはクリアせず注入し、手打ちを
  巻き込んで消さない。前回の「注入前に無条件 C-u」はユーザー入力を黙って全消去する
  副作用があったため撤回。
- **C-u+本文を単一 `send-keys` でアトミック送出**: クリアと本文送出を別呼び出しにすると
  片方だけ失敗して「空行のまま」や「未クリア連結」が起きるため、`send-keys C-u "$msg"` の
  1呼び出しにまとめた(①も単一呼び出しでドラフトを送る)。
- **`resume-watcher.sh` の全 tmux 呼び出しを `rl_tmux`(timeout)経由に**: tmux ハング時に
  取得済みの flock を永久保持し、以後そのペインの自動再開を殺すのを防ぐ。
- **①注入に非ブロッキング flock を追加**: 同一ペインへの二重発火で2プロセスの送出が
  交互に混ざって壊れるのを防止(取得できなければ別発火が処理中とみなしスキップ)。
- **既知の限界**: C-u は行頭までの消去(unix-line-discard)のため、複数行入力の以前の行は
  残り得る(①のドラフトは単一行なので通常は完全に消える=最善努力)。

### out-of-band 方式へ再設計(根本対応・同日3回目)

さらに再レビューを重ねた結果、**「①が tmux 入力欄へドラフトを打つ」設計そのものがバグの源**で
あり、かつ**①の検知時刻は実は LLM に届いていない**(Enter を送らないため送信されず、②の C-u で
消去され、`build_continue_msg` にも含まれていなかった)ことが判明した。マーカー/C-u/flock は
すべて「共有された入力欄という所有者不在のリソース」を複数プロセスで調整するための対症療法で
あり、ラウンドごとに増え続けていた。そこで**入力欄を一切共有しない out-of-band 方式へ再設計**した:

- **①は入力欄に書き込まない**: 検知時刻を状態ファイル(`rl_hit_file`＝`hit-time.<slug>`)へ
  アトミックに記録し、人間向けには tmux の **status-bar へ一瞬フラッシュ**(`display-message`)
  するだけにした。入力欄に触れないため、マーカー・行クリア(C-u)・注入ロックがすべて不要になった。
- **②が検知時刻を送信メッセージへ折り込む**: `resume-watcher.sh` が状態ファイルを
  「読み取り即削除」で消費し、継続メッセージへ **`(検知 … ／解除 … ／現在 …)`** を埋め込む。
  これは Enter で実際に送信されるため、**検知時刻が LLM の文脈に入る**(従来はドラフトが
  送信されず LLM に届いていなかった=①本来の目的が果たせていなかったのを是正)。
- **注入前クリアを撤廃**: 入力欄に我々の書き込みが無くなったため、②は C-u せず継続メッセージ
  のみを送る(元の設計に一致)。ユーザーが手打ち中のテキストを消す副作用が原理的に消えた。
- **継続メッセージは `send-keys -l`(リテラル)で送出**: `CLAUDE_RL_CONTINUE_MSG` に
  `Enter`/`C-c` 等のキー名が入ってもキーとして誤解釈せず文字列として打つ。
- **lib 読み込み失敗は fail-loud**: `source` に失敗したら誤動作せず FATAL ログして即 `exit`。
- **ペインID正規化を共有ヘルパ化**: `rl_pane_slug` を lib に集約し、`hit-time.<slug>` と
  `lock.<slug>` の生成を一本化(二重実装の解消)。
- 併せて `RL_DRAFT_MARKER`/`CLAUDE_RL_DRAFT_MARKER`・①注入用 flock は不要になり撤去した。

### フレッシュ再レビューの是正(A群・実バグ)

履歴を伏せた初見レビューで、out-of-band 実装に入った実バグを是正した:

- **継続メッセージ送出を `send-keys -l -- "$msg"` に**: `--` でオプション終端を明示し、
  `CLAUDE_RL_CONTINUE_MSG` が `-` 始まりでも tmux にフラグ誤認されないようにした。さらに
  **Enter は本文送出が成功したときだけ送る**(失敗時に Enter を撃つと入力欄の既存内容を
  誤送信するため)。
- **検知時刻ファイルの消費を watcher 起動直後(待機前)へ移動**: リセット待機は数時間に
  及び得るため、待機後に読むと、その間に発生した別エピソードの①がファイルを上書きして
  検知時刻を取り違える。起動時に読み取り即削除することで、自エピソードの値を確定させ、
  早期 exit 経路でも古い値を後続へ持ち越さないようにした。
- **`rl_tmux` の `timeout` に `-k 5` を付与**: SIGTERM を無視/処理が遅い tmux クライアントを
  +5 秒後に SIGKILL で強制終了し、「timeout したのに実際は返らず flock を保持し続ける」
  事態を防ぐ。
- **`resume-watcher.sh` の状態パスを `RL_STATE_DIR` に一元化**: 状態ディレクトリの literal
  再定義と mkdir 重複をやめ、lib の定義を使う(二重定義の drift 防止)。

> 同レビューで挙がった **元のフックに元々あった潜在バグ(B群)** は Issue #240 で対応済み:
> **バナー検出窓の 15/40 不一致(B1)**＝走査窓を `BANNER_SCAN_LINES`(既定40)へ一元化・
> **`resets at 3pm`/`resets at Mon` 取りこぼし(B2)**＝正規表現に任意の `at ` を許容・
> **翌日ロールオーバで約24時間 sleep(B3)**＝過去 `ROLLOVER_GRACE` 秒以内は直近リセット扱い・
> **flock フォールバック(B4)**＝fd オープン失敗と lock 取得失敗を区別・
> **前景コマンド固定(B5)**＝既定パターンに `bun`/`deno` を追加。
> 併せて整理(C群: 未使用 `transcript` 引数の削除・ガード対/`log()` の共有化)・
> **hit-file への session_id 併記による stale 破棄(D1)**・**bash 純関数の Python unittest 化(D2・
> `tests/unit/test_rate_limit_hook.py`)** も実施した。
> 一方 **設計課題(A5: status-bar 表示の恒久性／A6: アイドル入力中への継続メッセージ連結)** は
> クリーンな低リスク修正が無く、**オーナー判断により「今後も対処不要」＝wontfix 確定**(判断者=
> オーナー・2026-07-20・Issue #240 コメントに記録)。A6 は既知トレードオフとして現状維持。

## 再開判定の安全設計(稼働中セッションへの割り込み防止)

注入は同じペインへ `tmux send-keys` で送るため、**再開後に動いている Claude へ二度目を撃つと作業を割り込んで壊す**。これを防ぐため watcher は **状態認識** で動く:

- **大原則**: リセット待機後、ペインが**アイドル(作業中でない)なら注入して再開する**。
- **前景コマンドガード（最優先）**: 注入先ペインが**生存し、かつ前景コマンドが `claude` 系（既定 `claude`/`node`/`bun`/`deno`・B5）**のときだけ注入する。ペインが閉じている/シェル等に戻っている場合は `続けて` をシェルへ誤送出しないよう**注入せず終了**。`is_working` はペインが消えると capture 空で「アイドル」と誤判定するため、可否は前景コマンド(`pane_current_command`)で確定させる（許可パターンは `CLAUDE_RL_PANE_CMD_RE` で調整可）。
- **稼働中ガード**: ペイン末尾(入力欄フッタ付近・末尾8行)に中断ヒント(`esc to interrupt` 等)が見えたら「もう再開して動いている」とみなし**注入しない**（稼働中セッションへの割り込み防止）。
- **制限バナーは注入の必須条件にしない（情報ログのみ）**: リセット後は制限バナーが消えるため、「バナーが見える時だけ注入」にすると**注入すべきタイミングで必ず弾かれ、自動再開が機能しない**（2026-07-01 の実機不調の真因）。バナー有無は末尾 `BANNER_SCAN_LINES` 行(既定40=検知側の capture 窓と同一)で情報として記録するだけ。
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
| `CLAUDE_RL_CONTINUE_MSG` | (未設定=自動生成) | 送出する継続メッセージを明示指定する場合に設定。未設定なら「検知時刻・解除時刻・現在時刻・解除済みの旨」を自動で組み立てる(②)。明示指定時は `send-keys -l` でリテラル送出される |
| `CLAUDE_RL_ANNOUNCE_HIT` | `1` | `on-rate-limit.sh` が検知時刻を状態ファイルへ記録し status-bar へフラッシュするか(`0` で無効化・①) |
| `CLAUDE_RL_TMUX_TIMEOUT` | `3` | 各 tmux 呼び出しの timeout 秒(ハング対策・`rl_tmux`) |
| `CLAUDE_RL_RESET_POLL_INTERVAL` | `15` | リセット時刻の再取得ポーリング間隔秒(取り逃し対策) |
| `CLAUDE_RL_RESET_POLL_MAX` | `40` | 再取得の最大試行回数(既定 15s×40=10分) |
| `CLAUDE_RL_BANNER_POLL_INTERVAL` | `30` | 時刻不明時にバナー消滅(=リセット)を待つポーリング間隔秒 |
| `CLAUDE_RL_BANNER_POLL_MAX` | `720` | 同上限(既定 30s×720=6時間の安全上限) |
| `CLAUDE_RL_MARGIN` | `30` | リセット時刻に足すマージン秒 |
| `CLAUDE_RL_BANNER_SCAN_LINES` | `40` | 制限バナーを走査するペイン末尾行数。検知(acquire の capture)と解除判定(`is_limit_screen`)で同じ窓を使う(B1) |
| `CLAUDE_RL_ROLLOVER_GRACE` | `900` | 抽出したリセット時刻が過去だったとき、翌日へロールせず「直近リセット」とみなす過去許容秒(B3・リセット直後の約24時間 sleep 退化を防ぐ) |
| `CLAUDE_RL_MAX_ATTEMPTS` | `1` | 注入試行上限(既定1=単発。`>1` で「注入後もアイドルのまま(=効いていない)」のときだけ早撃ち救済リトライ) |
| `CLAUDE_RL_RETRY_BACKOFF` | `300` | 再注入バックオフ基本間隔秒(`MAX_ATTEMPTS>1` 時) |
| `CLAUDE_RL_VERIFY_WAIT` | `20` | 注入後に状態を再確認するまでの待機秒 |
| `CLAUDE_RL_PANE_CMD_RE` | <code>^(claude&#124;node&#124;bun&#124;deno)$</code> | 注入を許可する前景コマンドの正規表現(拡張正規表現・完全一致)。これに一致しない(シェル等に戻った/ペインが閉じた)ときは注入せず終了。既定は `node`/`bun`/`deno` を含む(B5)。独自ラッパ等でさらに変則な前景コマンドになる環境では実値で上書きする |
| `CLAUDE_RL_STATE_DIR` | `~/.claude/rate-limit-recovery` | 状態ファイル(ログ・ロック・hit-time)の置き場。主に Python unittest から一時ディレクトリへ隔離するためのフック(D2) |

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

---

# オーケストレータ委譲ルール注入フック(orchestrator-context.sh)

`SessionStart` イベントのうち **`resume` 以外**(`startup`/`clear`/`compact`)で発火し、主文脈の役割を
「オーケストレーション＋ユーザーとのコミュニケーション」に限定するための委譲ルール
(Orchestrator Task Delegation Rules)をコンテキストへ注入する。目的は、長いセッションでも
品質を落とさず作業できるようにすること、主文脈とサブエージェント間の二重作業(ステップ細部
までの指示→サブエージェント側での再展開)によるトークン浪費を防ぐこと。

## 構成

| ファイル | 役割 |
|---|---|
| `orchestrator-context.sh` | `SessionStart(startup\|clear\|compact)` フックハンドラ。コンテキスト本文を読み込み、`hookSpecificOutput.additionalContext` として JSON で標準出力へ返す。 |
| `orchestrator-context/orchestrator-task-delegation-rules.md` | 注入するコンテキスト本文(要件③によりスクリプトから分離)。内容を変えたい場合はこのファイルのみ編集すればよい。 |

## 発火条件

- `settings.json` の `SessionStart` に `matcher: "startup\|clear\|compact"` のエントリを追加している。
  `resume`(セッション再開)は既存の会話コンテキストを引き継ぐため対象外(要件①)。
  同一イベントの `startup` には `install_pkgs.sh`(`matcher: "startup\|resume"`)も別途登録されて
  おり、両フックは独立に発火する。
- `compact` は `SessionStart` イベントの `source` フィールドが取り得る値の一つで、コンパクション
  (自動/手動の要約による文脈圧縮)後にセッションが再開する際に発火する。Claude Code には独立した
  `PostCompaction` イベントは存在しない(コンパクション後の再開は `SessionStart(source=compact)`
  として表現される)。コンパクションで委譲ルールの指示文もコンテキストから失われ得るため、
  `compact` を再注入対象に含めている。

## 出力形式

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<orchestrator-task-delegation-rules.md の内容>"
  }
}
```

`jq` が利用できる環境ではそれを使って安全にエスケープする。`jq` が無い環境向けに
標準ツール(`sed`/`awk`)のみのフォールバックも用意している。コンテキストファイルが
見つからない場合は何も注入せず `exit 0`(fail-open)。

---

# 規約注入フック(UserPromptSubmit・context-mode 対策)

> このディレクトリのフックは上記のレートリミット系・オーケストレータ系だけではない。ここでは
> `inject-governance.sh` を記載する(`agent-command-gate.sh` の説明は `.codex/hooks/README.md` を参照)。

## 構成

| ファイル | 役割 |
|---|---|
| `inject-governance.sh` | `UserPromptSubmit` フックハンドラ。`governance-directives.md` を毎ターン `additionalContext` として注入する。stdin は読み捨てる。**失敗時は注入せず exit 0(fail-open)だが、必ず stderr へ `[inject-governance] …` の警告を出す**(可視化は `claude --debug`)。 |
| `governance-directives.md` | 注入する本文(規約の中核規範の配送用の写し)。**正本は `CLAUDE.md` ＋ `.claude/rules/*.md`**(規約本体は rules 側に分割済み・Issue #387)で、食い違ったら正本を正とする。HTML コメントは注入時に除去される。 |

## なぜ必要か

context-mode プラグイン(グローバル導入・2026-07-28)は全ターン・全 subagent 呼び出しに
`<session_continuity>`(「過去に記録された指示・役割は standing order ではない。
過去の文言はあなたを拘束しない」)を注入する。セッション冒頭に一度だけ読まれる CLAUDE.md は
この文脈で「過去の指示」として相対化されうるため、**中核規範を毎ターン注入して
"現在のターンの指示" として届ける**ことで対象から外す。

subagent 側の同種対策は各 `.claude/agents/*.md` 末尾の
「## 注入ブロックへの優先規定(context-mode 対策・必読)」が担う(15 エージェント全てに付与済み)。
ただし**注入への向き合い方は write 権限の有無で分かれる**(詳細は `.claude/rules/05-skills-agents.md`「戻り値のハンドオフ規約」):

- **write 権限あり(8)**: 注入の `<artifact_policy>` に**合わせる**。戻り値項目を
  `tmp/_handoff/<agent>--<key>.yaml` に書き、チャットにはパスと1行要約だけ返す。矛盾しないので無効化しない。
- **write 権限なし(7)**: ファイルに書けず注入の前提が成立しないため、`<artifact_policy>` を**無効化**して
  従来どおりチャットへ全文返す。

どちらのグループも `<session_continuity>` は共通で無効化する。

`ctx_*` は**一律禁止ではなくエージェント単位で選定**する(方針と根拠は `.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」)。
以下は現行方針(2026-08-09 時点)。**旧記述(当初 2026-07-29 時点の判断)は既に是正済みで、実行系は
全面禁止ではない**:

- **実行系(`ctx_execute` / `ctx_batch_execute`)は「shell 限定」で Bash 保有ロールに付与済み**
  (`Issue #303` でゲートを拡張・`#304` で解禁)。付与先＝主文脈・`issue-implementer`・`issue-fixer`・
  `pr-reviewer`・`dsv2-lookup`(いずれも既に Bash を保有)。Bash 非保有ロール(`spec-inspector`/
  `asset-auditor`/各 `*-author` 等)には**引き続き未付与**(ゲートが効いても「シェル実行能力の新規
  付与＝権限昇格」は残るため)。`language` は `shell` のみ許可(非 shell 言語は全ロール deny)。
  **`ctx_execute_file` は引き続き全ロール未付与のまま**(`.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」の結論どおり。
  解禁の要否は別途検討)。
  - 当初(2026-07-29)は「実測でホストの実ファイルシステムに書け(FS はサンドボックスされていない)、
    かつ tool_name が `mcp__plugin_...` になるため `matcher: "Bash"` の `agent-command-gate.sh` が
    発火しない」ことを理由に**全エージェント未付与**としていたが、**#303 で同フックを実行系 MCP
    ツールへ拡張し、ロール別 allowlist(層1〜3)と危険コマンド層を ctx 経路にも適用した**ため、
    gated ロール(`issue-implementer`/`issue-fixer`/`pr-reviewer`)では push/merge の権限境界は
    **ctx 経路でも回避できない**(層1〜3がそのまま掛かり、`cwd` の明示指定も deny される)。
    「回避できる」という旧記述はこの点で是正済み。
  - **rtk フック(`matcher: "Bash"`)は ctx 経路では依然発火しない**——ただしこれは
    `agent-command-gate.sh` と違い**統制(セキュリティゲート)ではなくトークン節約プロキシ**なので、
    上記の解禁可否そのものには影響しない。ctx 経由ではその節約(トークン圧縮)が効かないことだけ
    認識して使う(統制フックとトークン節約プロキシは別事実として書き分ける)。
- **検索系(`ctx_search` / `ctx_index`)は「リポジトリを変更しない」ので、多数ファイルを読むロールに付与する**
  (`dsv2-lookup` / `spec-inspector` / `asset-auditor` / `reconciliation-validator` / `pr-reviewer`)。
  リポジトリには書かず KB は `~/.claude/context-mode/` に隔離されるため、validator の fail-close も損なわない。
  **ただし `ctx_index` は read-only ではない**(`readOnlyHint: false` / `idempotentHint: false`＝同じ内容でも
  呼ぶたびに永続 FTS5 ストアへ追記される非冪等な書込)。付与の根拠は「read-only だから」ではなく
  **「リポジトリ(作業ツリー)に書かないから」**。運用上は同じ対象を無駄に再 index しない。

## 設計上の前提(公式仕様)

- `UserPromptSubmit` は stdout の素のテキストも context として扱われるが、他フックの出力と
  混ざったときに意図が曖昧にならないよう **JSON 形式**(`hookSpecificOutput.additionalContext`)で明示する。
- **exit 2 はプロンプト自体を破棄する**。規約注入の失敗が作業全体の停止に化けるのは割に合わないため、
  **どの失敗経路でも何も注入せず exit 0**(fail-open)。対象は規範ファイル欠落だけでなく、
  **python3 の起動失敗・読込失敗・JSON 生成失敗・本文が空**も含む。
- **fail-open でも無音にはしない**: いずれの失敗経路でも `[inject-governance] …` を **stderr へ出す**
  (`warn()` ＋ python 側の詳細メッセージ)。**フックの stderr は通常の対話画面には表示されない**ため、
  気づく手段は **`claude --debug`**(フックログに stderr が出る)。「規約注入が効いていない気がする」ときは
  `claude --debug` で起動して `[inject-governance]` 行の有無を確認する。
- 注入は毎ターンのコストになる。`governance-directives.md` は「独断・逸脱が起きたら実害が大きい」
  項目だけに絞り、**簡潔に保つ**(2026-07-28 時点で約 1,200 文字)。

## 保守

規約(PR7・起票規律・独断禁止・委譲ルール・課金方針・正本の所在)を変更したら、
`governance-directives.md` も合わせて更新する。**この追従漏れは下記のフックが機械的に検知する**。
規約の正本は `CLAUDE.md` 単体ではなく **`CLAUDE.md` ＋ `.claude/rules/*.md`** である
(Issue #387 で規範本文を rules へ分割した)。

---

# 規範の追従漏れ検知フック(PostToolUse・check-governance-drift.sh)

## 構成

| ファイル | 役割 |
|---|---|
| `check-governance-drift.sh` | `PostToolUse(Write\|Edit)` フックハンドラ。編集対象が**正本集合**(`CLAUDE.md` ＋ `.claude/rules/*.md`)のいずれかのときだけ、写し `governance-directives.md` が追従しているかを検査する。 |

## なぜ必要か(実際に起きた事故)

PR #276 で **正本側に「このリポジトリ＝2つのプロジェクトが同居」節(現 `.claude/rules/07-project-structure.md`)が
入ったのに、写しを追従させ忘れた**。その結果「`docs/` は一律非正本」という**誤った規範が毎ターン注入され
続ける**状態になった(Codex 第二意見レビュー指摘 #6 で発覚)。写しの誤りは毎ターン届くため影響が大きい。

「片方直すの忘れました」は再現性のあるミスなので、人の注意力ではなくハーネスで検知する。

**正本を集合として見張る理由(Issue #387)**: 規範本文が `CLAUDE.md` から `.claude/rules/NN-*.md` へ
分割された後も `CLAUDE.md` 単体のハッシュを見張り続けると、**規範の大半を占める rules 側の変更に
フックもテストも一切反応しない**——同じ事故が、今度は「検知機構が空振りする」形で再発する。

## 検知方式(毎回の小言ではなく状態比較)

写しの冒頭に同期マーカーを1行埋める:

```markdown
<!-- synced-from: CLAUDE.md@<sha256 先頭12桁> -->
```

marker が持つのは**正本集合の連結ハッシュ**(先頭12桁)。算出は
「相対パス(utf-8) + NUL + 生バイト + NUL」を `CLAUDE.md` → `.claude/rules/*.md`(相対パス昇順)の順に
連結し `sha256` を取る。**相対パスを混ぜるのは、ファイルの分割・改名・並び替えを内容の移動と
区別するため**(内容の総和が同じでも配置が変われば sha が変わる)。marker 自体は従来どおり1行のまま
——rules ごとに marker を並べれば drift したファイルを特定できるが、写しの構造変更を要し、毎ターン
注入される本文を膨らませるため採らない(Issue #387 オーナー確定)。

フックは現在の連結ハッシュと突き合わせ、**一致していれば何も出力しない**。
食い違っている間だけ警告を出し続け、**写しを直して sha を更新するまで消えない**(fail-safe な向き)。
単純な「正本を触ったら毎回リマインド」にすると小言が常態化して無視されるため採らない。

黙る条件: ①ハッシュ一致 ②編集対象が正本集合のどれでもない ③**写し自身の編集**(追従作業を邪魔しない)
④別プロジェクトの同名ファイル(realpath 一致で判定するため素通し)。

## 設計上の前提

- **常に `exit 0`**(fail-open)。このフックは補助であり作業を止める役ではない。
  payload 破損・python 失敗・ファイル欠落はいずれも `[check-governance-drift] …` を
  **stderr** へ出して継続する(`claude --debug` で拾える)。
- `PostToolUse` は本フックが初出。`asset_parity`(4ツリー間の presence/absence 検出)とは**別物**で、
  あちらは「資産の有無」、こちらは「正本→写しの内容追従」を見る。

## 追従したあとにやること

写しを直したら、マーカーの sha を現在値へ更新する。**`sha256sum CLAUDE.md` では求まらない**
(正本集合の連結ハッシュなので)。期待値はフックの警告文か、下記 CI テストの失敗メッセージが
そのまま出力する:

```bash
python3 -m unittest tests.unit.test_governance_sync   # 期待値と記録値の差分が出る
```

今回の変更が中核規範に無関係だと判断した場合も、同じく sha を更新して警告を解除する
(「見た上で不要と判断した」ことの記録になる)。

## 二層防御(編集時フック + CI テスト・Issue #312/#360)

上記フックだけでは追従漏れを取りこぼす経路が残る。**このフックは常に `exit 0` の fail-open な
nag であり、かつ発火条件が「編集対象の realpath が正本集合(`$CLAUDE_PROJECT_DIR/CLAUDE.md` ＋
`$CLAUDE_PROJECT_DIR/.claude/rules/*.md`)のいずれかに一致すること」のため、linked worktree 側の
正本を編集した場合は沈黙する**(Issue #323 実装時に実測)。結果として
「marker を更新しないまま merge される」経路が編集時フックだけでは塞ぎきれない。

これを補うのが **`tests/unit/test_governance_sync.py`**(CI・fail-close)。正本集合の連結ハッシュ
(先頭12桁)と `governance-directives.md` の `synced-from` marker を突き合わせ、不一致なら
テストを fail させる(`.github/workflows/tests.yml` が全 PR で実行)。ハッシュ算出方式・marker 記法は
本フックの埋め込み python と同一である必要があり、どちらかを変えるときは両方を同時に変える
(依存関係はテストファイル冒頭のコメントに明記済み)。

同テストは併せて **`.claude/rules/*.md` の集合と `CLAUDE.md` の `@` import 行の双方向一致**も
検査する(Issue #387 / F-387-05)。`@` 行の無いルールファイルは**誰にも配送されないまま
何も赤くならない**ため、ハッシュ検査とは別に落とす必要がある(ハッシュは「写しが追従しているか」を
見るだけで、「配送経路に繋がっているか」は見ない)。

- **編集時フック(`check-governance-drift.sh`)**: 即時フィードバック用の**助言**。fail-open・
  linked worktree では沈黙する既知の穴がある(上記)。
- **CI テスト(`test_governance_sync.py`)**: merge 前の**最終防衛線**。fail-close・worktree に依らず
  リポジトリの実ファイルを直接比較するため沈黙しない。

**どちらか片方に依存しない**: フックは早期発見の利便性、テストは取りこぼし防止の保証という
異なる役割を担う二層(両方とも機械判定だが、発火タイミングと保証強度が異なる)。フックが黙っていても
このテストが赤くなるので、追従漏れは merge 前に必ず露見する。

---

# subagent ライフサイクルフック(SubagentStart / SubagentStop・Issue #309 / #354)

`issue-implementer` / `issue-fixer` の dispatch に対して、(a) 是正ループの診断カルテ手順を注入し、
(b) worktree ↔ dispatch の所有関係を**機械可読な台帳**へ記録し、(c) カルテ未更新のまま
`issue-fixer` が停止することを拒否し、(d) 停止した dispatch の worktree を**回収してから解放**する。

> **フック自身は `git worktree remove` を呼ばない。** 実体を消してよいかの判断(台帳の状態・
> パス形状・git 管理下かの検査・回収→検証→解放の段構造)は `gitgate/worktree.py` に集約されており、
> フックはその verb(`python3 -m gitgate collect-worktree`)を起動するだけ(Issue #354・PR-3)。
> こうすると「回収せずに解放する」経路がフック側に**作りようがない**(FR-W2)。

## 構成

| ファイル | 役割 |
|---|---|
| `subagent-karte-inject.sh` | `SubagentStart(issue-fixer)`。`karte-protocol.md` を `additionalContext` として注入する。**失敗時は無出力 exit 0(fail-open)**。 |
| `subagent-worktree-bind.sh` | `SubagentStart(issue-implementer\|issue-fixer)`。起動した dispatch の `.claude/worktrees/agent-<id>` を所有台帳の `open` エントリへ束縛し `running` にする。**常に無出力 exit 0**。 |
| `subagent-stop-gate.sh` | `SubagentStop(issue-implementer\|issue-fixer)`。①`issue-fixer` が `karte check` を通していない停止を `{"decision":"block"}` で拒否(**判定不能も拒否＝fail-close**)し、②通ったら台帳を `running`→`stopped` へ進めて `collect-worktree` で回収・解放する。**①で block したら②へ進まない**。 |
| `karte-protocol.md` | 注入本文(シェルから分離＝`inject-governance.sh` と同作法)。内容を変えたいときはこのファイルだけを編集する。 |
| `issue_start/subagent_hooks.py` | 上記3つの実体(verb 引数で分岐)。`.sh` は `issue-start-gate.sh` と同じ**薄い起動口**。 |
| `issue_start/worktree_ledger.py` | 所有台帳(`tmp/_worktree/ledger.json`)の読み書き・状態遷移・掃引(`sweep_orphans`)・残留 evidence(`residue_report`)。 |
| `gitgate/worktree.py` | 実体の削除経路(`worktree-release` / `collect-worktree` / `worktree-forget`)。**フックからはサブプロセスとして起動する**。 |

## 回収・解放段の fail 方針(`subagent-stop-gate.sh` の②・Issue #354)

**どの失敗経路でも worktree を消さず、台帳を `stale` にして無出力 exit 0 で返す**(＝停止を
ブロックしない)。解放できないことを理由にエージェントを止め続けても解決しない——当人には
`gitgate` の worktree verb が許可されていないからで、制御を主文脈へ返し、
**次 dispatch の gate deny**(下記)で気づかせるのが正しい向き。

| 段 | 失敗したとき |
|---|---|
| 台帳の置き場(main worktree root)を導出できない | 何も書かず何も消さず返す |
| `agent_id` で自分のエントリを引けない | **`running` は掴みにいかない**(他人のものかもしれず、`stale` へ落とすと `WORKTREE_LIVE` の保護が外れる)。同 `agent_type` の最新 `open` だけを `stale` にする |
| `running` → `stopped` の遷移に失敗 | `stale` にせず evidence だけ残す(状態機械を壊さない) |
| 回収対象の handoff を一意に決められない(worktree の `tmp/_handoff/` に2件以上) | 起動せず `stale`(どれが成果物か決められないまま消さない) |
| `collect-worktree` が非0 / 起動不能 / timeout | `stale`(worktree は残る) |

`running` → `stopped` の遷移を**必ず挟む**こと。`collect-worktree` は台帳 status `running` を
`WORKTREE_LIVE` で拒否し `stopped` のみ受理する(安全側の既定・Issue #354 F-354-01)ので、
遷移を落とすと自動解放は一度も成功しない。

## 残留 worktree での次 dispatch を deny する(PreToolUse・`issue-start-gate.sh`・Issue #354)

自動解放が失敗した/フックが発火しなかったときの**最後の砦**。`issue_start/gate.py` の
`assert_no_worktree_residue()` が **全 `Task` dispatch**(managed / unmanaged を問わない)に対して
判定する。#354 が実測した乗っ取りは `pr-reviewer`＝unmanaged 側で起きたため、managed だけを
見張っていては正面から塞げない。

| reason | 条件 | deny 文に載る解消コマンド |
|---|---|---|
| `ISSUE_START_WORKTREE_RESIDUE` | `stale` / `stopped` / `collected` のエントリが1件以上ある | `python3 -m gitgate collect-worktree --entry <entry-id>`(回収不能なら `worktree-forget --entry <entry-id> --reason <text>`) |
| `ISSUE_START_WORKTREE_UNCLAIMED` | ディスク上の `agent-*` が `running` / `stopped` のどれにも紐づかない | `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` |
| `ISSUE_START_WORKTREE_LEDGER_ERROR` | 台帳が読めない/壊れている | (fail-close。台帳を直すまで通さない) |

- **過剰 deny の緩和は deny を弱めることでは行わない**。①deny 文へ必ず解消コマンドを載せる、
  ②`worktree-forget --reason`(理由必須)の逃げ道を残す、の2つで行う。
- **`stopped` は2つの集合に同時に現れる**——`unclaimed` 判定では claimed 側に数えて
  「回収処理中の worktree を孤児と誤診しない」ようにし、residue 判定では検出して
  「回収段が失敗したまま止まっている」ことに気づけるようにする。どちらか片方を落とすと
  それぞれ別の失敗になる。
- **判定前に `sweep_orphans` を1回走らせる**。「占有を主張しているのに worktree が実在しない」
  `running` / `stopped` を `stale` へ落とす状態→状態の照合で、落とす候補が無ければ台帳へ
  書き込まない(正常系は no-op)。`open` は掃引しない——live な dispatch と取り残しを状態だけでは
  区別できず、区別には経過時間が要るため(台帳は TTL 判定を持たない)。
- **PR-1 の fail-open からの変更点**：台帳が壊れているときの dispatch は #309 では ALLOW だったが、
  #354 PR-3 で **deny(fail-close)** に倒した。残留の有無を判定できない状態で通すと統制が空振りするため。
  一方、ALLOW 後の**起票**(`record_open_entry`)は今も fail-open のまま(書けなくても dispatch は通る)。

`.sh` を薄い起動口にして判定ロジックを python モジュールへ置いたのは、`tests/unit/test_subagent_hooks.py`
から**サブプロセスを介さず**注入点(`repo_root` / `now` / `runner`)込みで検証できるようにするため。
フック本体をシェルの heredoc に埋めると、実リポジトリの台帳・カルテを汚さずに検証できない。

## fail 方針の非対称(設計判断・意図的に方向が逆)

| 対象 | 方針 | 判定不能・失敗時の挙動 |
|---|---|---|
| **停止のブロック**(`subagent-stop-gate.sh` の①) | **fail-close** | `active.json` 欠如・破損、`karte check` を起動できない、いずれも **block** する |
| **残留 worktree の deny**(`issue-start-gate.sh`・#354) | **fail-close** | 台帳が読めなければ dispatch を deny する(`ISSUE_START_WORKTREE_LEDGER_ERROR`) |
| **台帳への起票・束縛**(`issue-start-gate.sh` の起票／`subagent-worktree-bind.sh`) | **fail-open** | 台帳へ書けなくても dispatch は ALLOW のまま。束縛できなければ**推測せず**`notes` を1行足すだけ |
| **worktree の削除**(`subagent-stop-gate.sh` の②) | **fail-safe＝「消さない」側** | 判定不能・回収失敗なら削除せず `stale` にする |

**理由**: ブロック・deny の誤りは「余計に止まる」だけで回復可能だが、削除の誤りは成果物を
回復不能に失う。**起票**だけが fail-open なのは、書けなかった記録のために dispatch を止めても
何も守れないから(守るべき判定は読み取り側＝residue deny が担う)。

> **#309(PR-1)時点との差**: 当時は残留判定も fail-open(＝deny しない)だった。これは
> 「観測が正確になったことを実測してから deny を有効化する」という**統制を先に、付与は別 PR**の
> 順序に従った暫定状態で、#354 PR-3 で fail-close へ倒して統制を発効させた。

## 対象外ロールの扱い(matcher と in-script 判定の二重)

`settings.json` の `matcher` で対象ロールを絞ったうえで、**スクリプト内でも `agent_type` を判定して
対象外は無出力 exit 0** にしている(`agent-command-gate.sh` の「対象外ロールは常に許可」不変条件と同型)。
二重にしたのは **`SubagentStart`/`SubagentStop` の `matcher` が `agent_type` 名で効くかが本 repo で未実測**
だから(`PreToolUse` の `matcher` は tool 名で効く)。効かなくても他ロール・主文脈へ副作用が漏れない。

`agent_type` が読めない(綴りが想定と違う・欠落・payload が JSON として読めない)場合も**無出力 exit 0**。
推測して別ロールに統制を掛けない。

## 起動口を `bash <path>` で登録している理由

`settings.json` の登録は `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh`(`issue-start-gate.sh` と同形)。
実行ビットに依存せずに起動できるので、実行ビットが落ちた状態で配布されてもフックが黙って
無効化されない。新規に足す登録行は最初から `"$CLAUDE_PROJECT_DIR"` を**クォートして**書く(Issue #270)。

## 所有台帳(`tmp/_worktree/ledger.json`)

- **置き場**: `<main-worktree>/tmp/_worktree/`。`_handoff`・`_karte` と同格で、
  `dsv2 clean-tmp` の保護名(`PROTECTED_DIRNAMES`)に登録済み＝tmp 掃除で消えない。
- **main worktree への収束**: フックも gate も linked worktree から起動されうるため、
  `.git` ファイルの `gitdir:`→`commondir` を辿って必ず main worktree の台帳へ収束させる
  (`karte/paths.py` の K-01 と同等の導出を `worktree_ledger.py` 内に独立実装。共有モジュール化
  しないのは Issue #318 が `karte/paths.py` を触るためのファイル競合回避＝選択肢 LG-1 案A)。
- **時刻**: `now` は必ず引数で注入し、台帳モジュールは `datetime.now()` を呼ばない。
  **TTL・経過時間による判定を1つも設けない**(判定は状態のみ)ので、時間経過だけでテストが
  赤くなるクラスの問題が構造的に発生しない(`.claude/rules/04-test-data.md`)。
- **エントリは削除しない**(履歴として残す＝`.claude/rules/01-principles.md`「PR8「消さない」の
  適用範囲」区分1)。終端は `released` / `abandoned`。
