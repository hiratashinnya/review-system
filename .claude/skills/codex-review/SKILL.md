---
name: codex-review
description: ユーザーが明示起動する「Codex 公式 CLI (`codex exec`) への第二意見レビュー委譲」の入口。別モデルファミリ(OpenAI)に敵対的/セキュリティレビューを回す標準手順と、cybersecurity フィルタで最終応答が消えるハマりどころ＋rollout フォールバックを規約化する。agy MCP bridge (`mcp__agy__codex_*`) は使わない（→そちらは agy-delegate＝Gemini 用）。in-repo の Claude レビュー→merge は pr-reviewer。
disable-model-invocation: true
---

# Codex 公式 CLI への第二意見レビュー委譲（codex-review）

**別モデルファミリ（OpenAI）の視点**で、PR・実装・設計に敵対的/セキュリティレビューを回すための**ユーザー起動の入口**。
「実装とレビューを別コンテキストに分離」する運用（CLAUDE.md）で、Claude 以外の第二意見が欲しいときに使う。
`codex exec` は別プロセス・別モデルで走り、**Anthropic のトークンも session limit も消費しない**——opus サブエージェントが
session 上限のときの代替レビュー経路にもなる（それが主目的の一つ）。

> 使い分け：**agy MCP bridge (`mcp__agy__codex_*`) は使わない**（オーナー指示・→ agy 経由の委譲は `agy-delegate`＝Gemini 用）。
> **in-repo の Claude 自身によるレビュー→コメント→merge は `pr-reviewer`**。本スキルは「別ファミリの第二意見を取りに行く」専用。

## 呼び方（標準手順）

> 🔐 **成果物は「実行ごとに一意な、gitignore 済みの一時ディレクトリ」にまとめて出す。**
> 観点プロンプト・最終応答・イベントログには**レビュー対象のコード断片や秘密が入りうる**。
> cwd 直下の固定名（`events.jsonl` / `last.txt` 等）に置くと、**未追跡ファイルとして誤 commit される**／
> **前回や別実行の残骸を静かに読む**の両方が起きる。**固定名を使わない。**

1. **実行単位の一時ディレクトリを作る**（`tmp/` は本リポジトリで gitignore 済み）：
   ```bash
   REPO="$(git rev-parse --show-toplevel)"
   mkdir -p "$REPO/tmp/codex-review"
   RUN_DIR="$(mktemp -d "$REPO/tmp/codex-review/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
   chmod 700 "$RUN_DIR"
   ```
   - **アクセス範囲（＝一時成果物の読取りに対する制約）**：**codex の一時成果物として読んでよいのは
     `$RUN_DIR` の中だけ**。**他の run ディレクトリを開かない**（並行実行・過去実行の別対象の所見と秘密が入っている）。
     この制約は**一時成果物にだけ掛かる**もので、次の2つは制約対象外＝許可範囲：
     **①レビュー対象リポジトリ**（cwd はリポジトリのまま・Codex に diff / 対象ファイルを読ませる＝手順 2）、
     **②自分の `thread_id` で一意に束縛した rollout ファイル1件**（フォールバック②。
     `silent-failure-diagnosis` D0 の**承認済み例外**であり、束縛できないなら開かない）。
   - **後処理**：所見を報告へ取り込んだら `rm -rf "$RUN_DIR"`。**`git add` しない**
     （gitignore 済みだが `-f` で足さない・報告やコミットへ生の値を転記しない）。
2. 観点プロンプトを **`$RUN_DIR/prompt.txt`** に書く。cwd はリポジトリのままにして、
   未コミット diff / 対象ファイルを Codex に読ませる。
3. 非対話で実行。**stdout（JSON イベント）と stderr（診断メッセージ）を別ファイルへ分ける**：
   ```bash
   codex exec --json -m <model> --sandbox read-only \
     -o "$RUN_DIR/final.txt" - \
     < "$RUN_DIR/prompt.txt" \
     > "$RUN_DIR/events.jsonl" \
     2> "$RUN_DIR/stderr.log"
   ```
   - stdin に観点プロンプトを流す（`-` が stdin 指定）。`--sandbox read-only` で書き込みをさせない。
   - `model` は**オーナー指定**（例 `gpt-5.6-sol`）。`codex exec review` サブコマンドもある。
   - 🛑 **`2>&1` で stderr を stdout に併合しない。** 警告・進捗が混ざると `events.jsonl` が純粋な JSONL でなくなり、
     `thread.started` の機械抽出が壊れて**不要な停止や誤解析**を招く（＝フォールバック①②の前提が崩れる）。
   - **`--json` を必ず付ける**。理由は下記フォールバックの前提になるため（自分の stdout に全発話が届く）。
     `-o` は最終応答だけを別ファイルに書き出す。
4. **`thread_id` を控える**（純 JSONL になった `events.jsonl` だけを見る）：
   ```bash
   THREAD_ID="$(grep -m1 '"thread\.started"' "$RUN_DIR/events.jsonl" \
     | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["thread_id"])')"
   ```
   取れなければ**推測せず停止して報告**する（フォールバック②の束縛条件が作れないため）。
   このとき `$RUN_DIR/stderr.log` を読んで原因（起動失敗・警告混入等）を確認する。
5. **`$RUN_DIR/final.txt`（最終応答）を読む。** flag されていたら下記フォールバックへ。
   **応答が空・異常なときは `$RUN_DIR/stderr.log` も必ず併せて読む**——CLI 側のエラーはそちらにしか出ない。

## ハマりどころ①：cybersecurity フィルタで最終応答が消える（原因特定済み・2026-07-20）

敵対的バイパス探索のようなプロンプトを流すと、**最終アシスタントメッセージ
（`$RUN_DIR/final.txt` ＝ `$RUN_DIR/events.jsonl` 末尾の `agent_message`）が**
```
ERROR: This content was flagged for possible cybersecurity risk. … https://chatgpt.com/cyber
```
**に差し替わる**ことがある。犯人は **OpenAI サーバー側の cyber リスク分類器**（Trusted Access for Cyber ゲート）で、
**攻撃文字列・bypass 成立条件を集約した最終まとめ**が引っかかる。**CLI の出力取りこぼしではない**
（リダイレクトでの捕捉は正常・**末尾の最終応答が ERROR に差し替わっているだけ**で、
`stderr.log` 側にも CLI エラーは出ない）。Anthropic の session limit とは無関係。

### 回避（プロンプト設計・**実行前の事前設計にのみ適用**）

> 🛑 **ここは「これから流すプロンプトをどう書くか」＝将来の実行に対する事前の防御的設計**であって、
> **flag された後の再試行手順ではない**。`ERROR: … flagged` は**サーバ側のセキュリティ判定**＝
> [silent-failure-diagnosis](../silent-failure-diagnosis/SKILL.md) の **D0 hard block** に当たり、
> **言い換えての再提出は、同一セッションでも新規セッションでも「形を変えた迂回」**として禁止される。
> **flag 後に許されるのは2つだけ**：**承認済み例外＝自セッションに既に書かれた証拠の限定回収**（下記フォールバック①②）と、
> **停止してオーナーへ報告すること**。

- **最初の1回目から防御レビュー形式で書く**：「攻撃コマンド文字列を再現するな。各 finding を
  `file:line ＋ 欠陥クラス ＋ 修正方針` で出せ」。最終集約に生の exploit を集めさせないのが肝。
- **同一セッションでの言い換え再提出は、汚染を引きずり再 flag されやすい**——が、それ以前に
  **flag 後の再提出は新規セッションであっても行わない**（上記 D0）。防御形式は**次に別のレビューを起こすときの
  事前設計**として適用し、flag された当該レビューは**回収＋停止報告で閉じる**。

### フォールバック（所見は失われていない）

critical 候補は**最終集約が flag される前に中間発話として出ている**ので回収できる。**回収元の優先順位を守る**：

**① 自分の stdout（既定・共有ディレクトリを読まない）**
`--json` を付けていれば、中間発話は `{"type":"item.completed","item":{"type":"agent_message","text":…}}`
として**自分が捕捉した `$RUN_DIR/events.jsonl` に既に入っている**。最終集約が flag されても、その手前の
`agent_message` を読めば所見は揃う。**この経路は自プロセスの出力しか触らないため、他セッションを
読む余地が構造的に無い。**
**flag かどうかを判定するときは `$RUN_DIR/events.jsonl`（サーバ由来の ERROR 文言）と
`$RUN_DIR/stderr.log`（CLI 由来のエラー・警告）の両方を見る。** 片方だけだと、
「flag されたのか・CLI が落ちたのか・そもそも起動していないのか」を取り違える。

**② それでも足りないときだけ rollout ファイル（session を明示特定する）**
`~/.codex/sessions/YYYY/MM/DD/rollout-<時刻>-<thread_id>.jsonl` に全 rollout が残る。
**ファイル名に thread_id が埋まっている**ので、**手順 4 で控えた `$THREAD_ID`
（`$RUN_DIR/events.jsonl` の `{"type":"thread.started","thread_id":…}` 由来）と一致するファイルだけを開く**。

> 🛑 **「日付ディレクトリの直近」で探してはならない。** codex は**並行実行できる**——私自身が複数レビューを
> 並列で回すこともあれば、オーナーが対話セッションを同時に使っていることも、別リポジトリの作業が走って
> いることもある（実測：ある1日に15セッションが蓄積）。「直近」は**別セッションのファイルを静かに掴む**。
> 掴んだ結果は「別の対象についての所見を、この対象の所見として報告する」＝**気付けない誤答**であり、
> 同時に**無関係な会話・秘密を読む**ことにもなる。
>
> **制限すべきは並行実行そのものではなく、セッションの特定方法**である。並行して走らせてよい。
> ただし**必ず自分の thread_id で1ファイルに束縛する**。thread_id が取れなかった場合は、
> 探索に降りず**停止して報告する**（推測で他人のファイルを開かない）。

> これは [silent-failure-diagnosis](../silent-failure-diagnosis/SKILL.md) の一般則 **D5「永続ログ・履歴を当たる」** の Codex 版。
> **本スキルは skill であり `skills:` によるプリロードが効かない**ので、Codex が「エラーを出さずに誤答・空応答している」
> 疑いが出たら、**上記リンクを開いて**切り分けの順序（D0→D1→D6→D5→D4→D3→D2→D7/D8）に従うこと。

### 正攻法（当面は使わない）
- OpenAI の Trusted Access for Cyber 登録でセキュリティ作業として通せるが、**無課金方針・オーナー認可が対象**
  （CLAUDE.md コスト方針）。当面は上の「防御形式言い換え＋rollout 回収」で回す。

## ハマりどころ②：環境依存（クラウド不可）

`codex` CLI・ChatGPT ログイン・`~/.codex/sessions` に依存する **Linux/WSL 専用**。クラウド/ヘッドレスでは使えない。
疎通不明なら `codex exec --help` や `which codex` で存在確認してから流す（`agy-delegate` の疎通ゲートに相当）。

## done 条件

- [ ] **実行ごとに一意な `$RUN_DIR`**（gitignore 済み `tmp/codex-review/` 配下・`chmod 700`）を作り、
      `prompt.txt` / `final.txt` / `events.jsonl` / `stderr.log` を**その中だけ**に出した。
      **cwd 直下の固定名を使っていない**（旧実行の残骸を読む余地を作っていない）。
- [ ] 観点プロンプトを防御形式で書き、`codex exec --json -m <model> --sandbox read-only` で流した。
      **`2>&1` で併合せず**、stdout（JSON イベント）と stderr（診断）を別ファイルに分けた。
- [ ] `$RUN_DIR/events.jsonl` から `thread.started` の `thread_id` を機械抽出して控えた
      （取れなければ探索に降りず停止して報告した）。
- [ ] 最終応答は **`$RUN_DIR/final.txt`**（実行例の `-o` と同一ファイル）を読んだ。
      異常時は `$RUN_DIR/stderr.log` も確認した。
- [ ] ERROR(flagged) なら **①`$RUN_DIR/events.jsonl` の `agent_message`** から回収した（不足時のみ ②`rollout-*-<thread_id>.jsonl` を**その1ファイルだけ**開いた。「直近」で探していない）。
- [ ] ERROR(flagged) の後に **言い換え再提出をしていない**（同一セッション・新規セッションとも。D0 hard block ＝
      許されるのは既存証拠の限定回収と停止報告だけ。防御形式は**次回の事前設計**として適用した）。
- [ ] 所見を Claude 側レビューと統合し、**AI（Codex 由来）であることを明示**してオーナー/PR へ報告した（独断で「対応不要」としない＝CLAUDE.md）。
- [ ] 報告へ取り込んだ後 **`rm -rf "$RUN_DIR"`** した（秘密を含みうる未追跡ファイルを残さない・`git add` していない）。

> 原因特定の経緯・詳細はグローバルメモリ `feedback_codex_review_official_cli` にインシデント記録として残す。本スキルが手順の正本。
