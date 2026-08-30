# issue-fixer — 設計経緯・却下案・既知の限界（rationale・非規範）

> **これは規範ではない。** `.claude/agents/issue-fixer.md`（規範・正本）から Issue #372 で
> 移設した「設計判断の理由・却下案・既知の限界・過去インシデントの経緯・実測ログ」の保管先
> （PR8「消さない」＝削除ではなく移設）。**dispatch 時にロードされない**ので、行動を決める規範は
> すべて移設元に残っている。疑問が生じたときだけ参照する。
>
> - **移設元（規範・正本）**：`.claude/agents/issue-fixer.md`
> - **本文は移設元の文言を尊重して移した**（内容の変更・要約はしていない）。ただし `##` 見出しの
>   付与に加え、複数節をまとめる際・切り出した断片を単独の節として成立させる際に必要な最小限の
>   接続語・言い換えは補っている（見出しだけを付与した逐語移設ではない）。移設先で `##` 見出しを
>   付与し、どの節から来たかを併記している。
> - **相対参照は移設元の文脈を指す**：本文中の「後述」「上記」「下記」「本節」等は
>   移設元ファイル内の位置関係であって、本ファイル内の位置関係ではない。
> - 分離の方針・4ツリー波及方針は `.ai/rationale/README.md`。

## model / effort の選定根拠（移設元：frontmatter 直後の HTML コメント）

```
model/effort 選定根拠（/bloom-model-tier・Issue #308）:
  主要認知行為＝「レビュー指摘の失敗を根本原因まで分解し、責任箇所を特定する」＝分解・関連付け
  → Bloom Lv4 分析。軸2＝**網羅性ボトルネック**：期待する振る舞い（`expected`）と再検証条件
  （`recheck`）はレビューアが finding として与える契約になっており、本ロールは「何が正しいか」を
  裁定しない（対応要否・据え置きはオーナー専権・指摘の解消判定は再レビュー側）。難所は
  「未解消 finding を取りこぼさず、前ラウンドの失敗を踏まえて別角度を選ぶ」網羅性側にあり、
  effort を増やせば直接品質が上がる。→ 閾値表より `sonnet` + `effort: high`。
  （Issue #308 の既定案 `sonnet` と一致。「是正への転換時に model を昇格しない」というオーナー
  決定にも沿う——昇格は品質ではなくラウンド数への反応になるため。）
```

## なぜ初回実装と型が分かれているか（勝手に兼用しない）（移設元：同名の節）

`SubagentStop` のペイロードは `agent_type` / `agent_id` / `last_assistant_message` だけで、
呼び出し時の dispatch prompt を含まない。`issue-implementer` を是正にも兼用すると、フックが
「今のは初回実装か是正か」を判別できず、**初回実装まで誤ってブロックする**か、**是正の診断必須を
強制できない**かのどちらかになる。型を分ければ「`issue-fixer` は定義上つねにカルテを要する」となり、
条件分岐なしの fail-close なゲートが成立する。副次的に、診断必須の是正契約と初回実装契約が
別ファイルに分かれる（単一責務）。

## STOP 時も hand-off を書く理由

hand-off は dispatch が終了したことを呼び出し元が観測する signal である。STOP 時にチャットだけで報告すると、作業ツリーの回収・解放を開始できず手作業が必要になる。このため、`handoff_path` 自体が未提供で書込不能な着手前 STOP を除き、成功・失敗のどちらでも1件の hand-off を残す。

## `handoff_path` を相対にした理由・`karte_path` を絶対に据え置いた理由（移設元：「入力」節）

- `handoff_path`（作業ツリールート相対）について：

  相対である限り**定義上つねに自分の作業ツリー配下**へ
  解決されるので、「別のワークツリーを指すパス」という脅威が検査ではなく構造で消える。この形は
  本ロールが**非 isolated で動く現在**（相対＝メインワークツリー配下）でも、**isolation を課された後**
  （相対＝自分の worktree 配下・Issue #354）でも、文言を変えずに成立する。

- `karte_path`（メインワークツリーの絶対パス）について：

  カルテは
  **ラウンドをまたいで蓄積される呼び出し元側の台帳**であって本ロールの出力ではなく、受け渡し方式の
  見直しは Issue #354 の範囲。

### `karte_path` は Issue #354（PR-4・K2）で**廃止した**（2026-08-19）

上記の据え置きは #354 で決着し、**`karte_path` の受け渡し自体を無くした**。共通本文
（`.ai/agents/issue-fixer.md`）からは「入力」節の `karte_path` 行・「2つのパスは受け渡し方式が
異なる」節・「`karte_path` の検査（絶対パス完全一致／`..`／symlink の3点）」節を削除し（区分2＝
本文の書き換え）、代わりに「カルテには実行環境が提供する render/append/close-attempt 操作でのみ触れ、
パスを自分で組み立てない」という記述に置き換えた。経緯を保全するため、**なぜ絶対パスにしていたか
（上記）と、なぜ廃止できたか（以下）の両方をここに残す**（区分1）。

- **廃止できた理由**：`karte` CLI は `karte/paths.py` の `main_worktree_root()`（K-01）で
  台帳の所在を**決定論的に導出する**（`.git` ファイル → `gitdir:` → `commondir`）。linked worktree
  から呼んでも必ずメインワークツリーの台帳に収束するので、呼び出し元がパスを教える必要が
  そもそも無い。教えなければ「別 worktree・別 Issue の台帳を掴む」脅威は**検査ではなく構造で
  消える**——旧 `issue-fixer.md` が背負っていた3点検査（完全一致・`..`・symlink）は、守るべき脅威が
  無くなったので削除できた。検査を緩めたのではなく、脅威を消した。
- **`handoff_path` を相対にした #323 の考え方の対称形**：#323 は「呼び出し先が新規に書き、
  呼び出し元が回収する成果物」の置き場を相対にして worktree 外への誤誘導を構造的に消した。
  K2 は「呼び出し元が既に所有している共有台帳」については**パスを渡さない**ことで同じ効果を得る。
  一般則は `.claude/rules/05-skills-agents.md`「戻り値のハンドオフ規約」に1項として明文化した。
- **残る限界**：規律は機械強制されない。`.claude/settings.json` の `permissions.deny` は
  `Edit(/tmp/_karte/**)` のままで `Read` を塞いでいない（塞ぐと主文脈の正当な読みも巻き込む）。
  したがって「自分でパスを組み立てて読みに行かない」は多層防御の一枚として本ロールが守る
  （各 wrapper の「既知の限界」相当の節に明記済み）。

## `isolation: "worktree"` と `ISSUE_FIX_BINDING_V1` marker の enforcement（Issue #354・PR-4）

共通本文には「何を渡す契約か」だけを残し、統制の内部をここへ置く。

- **契約の実体**＝`issue_start/managed-entrypoints-v2.json` の `isolation_only` 区分
  （`agent_type: "issue-fixer"`・`claude` transport の `required_isolation: "worktree"` と
  `binding_marker: "ISSUE_FIX_BINDING_V1="`）。enforcement＝`issue_start/gate.py` の
  `_parse_isolation_only` / `_fix_binding` / `_validate_isolation`。
- **なぜ `managed` ではなく別区分か**：`managed`（`issue-implementer`）は dispatch のたびに
  GitHub API で blocker を fresh read する。是正ラウンドは**既に開いた PR への処置**で、Issue の
  着手可否は初回実装の dispatch で判定済みだから、ラウンドごとに再判定する意味が無い。むしろ
  毎ラウンド API を叩くと、API 不通時にレビュー是正まで fail-close で止まる——「直せない」ではなく
  「直しに行けない」という、統制の目的から外れた停止になる。よって `isolation_only` は
  shape 検証（必須/禁止 field・`required_isolation`）と軽量 marker だけを見る。
- **なぜ marker を要求するか（無検証で素通ししないか）**：worktree 所有台帳（FR-W4）に
  `{issue, round, branch_name, handoff_path}` が正確に載らないと、どの worktree がどのラウンドの
  ものか事後に辿れない。加えて `adopt-branch --expected-oid` に渡す値の出所が dispatch 契約側に
  固定される（是正者に組み立てさせると、掴む commit が dispatch の想定と食い違いうる）。
  deny 文言も「何を直せばよいか」を具体的に返せる。
- **`repository` field を追加した理由（F-354-10・2026-08-19）**：当初の marker は `expected_oid` を
  持つのに `repository` を持たず、`adopt-branch --repository OWNER/REPO` の出所が dispatch 契約に
  無いまま是正者へ丸投げされていた。是正者は生 `git remote` を deny されており（Bash 実行規律）
  OWNER/REPO を機械的に得る手段が無い——`expected_oid` を dispatch 契約側に固定した理由（上記）が
  そのまま `repository` にも当てはまるのに、当初は field が漏れていた。marker へ足すことで、
  `expected_oid` と同じ「出所を dispatch 契約側に固定する」設計を貫徹する。
- **reason code**：`ISSUE_START_ISOLATION_NOT_WORKTREE`（isolation 欠落・別値）／
  `ISSUE_START_BINDING_MISSING_OR_DUPLICATE`（marker の欠如・重複）／
  `ISSUE_START_BINDING_INVALID_JSON`／`ISSUE_START_BINDING_UNKNOWN_FIELD`（exact 6 field 以外）／
  `ISSUE_START_ISSUE_INVALID`／`ISSUE_START_ROUND_INVALID`／`ISSUE_START_BRANCH_INVALID`／
  `ISSUE_START_REPOSITORY_INVALID`／`ISSUE_START_EXPECTED_OID_INVALID`／
  `ISSUE_START_HANDOFF_PATH_INVALID`／`ISSUE_START_TOOL_INPUT_SHAPE_INVALID`／
  `ISSUE_START_MANIFEST_CONTRACT_ERROR`。
  加えて残留 worktree があれば `ISSUE_START_WORKTREE_RESIDUE` 等（PR-3・全 dispatch 共通）。
- **`adopt-branch` を本ロールにだけ付与した理由**：isolation を課すと worktree はまっさらで、
  是正対象ブランチが載っていない。初回実装は `new-branch` で新規に切るので既存ブランチを掴む
  必要が無く、`issue-implementer` へ付与すると最小権限が広がるだけで得るものが無い。
  worktree 解放系（`worktree-release`/`collect-worktree`/`worktree-forget`）は**他 dispatch の
  成果物を消せる**ため、どの gated ロールにも付与しない（実行主体は非 gated の主文脈と
  `SubagentStop` フックに限る）。allowlist 未登録＝既定 deny なので明示 deny のコードは要らない。

## 「権限は同一」の文言を訂正した理由（F-354-11・2026-08-19）

責務境界節冒頭は元々「権限は `issue-implementer` と同一」と無条件に書かれていたが、
`.claude/rules/05-skills-agents.md` は PR-4 で「implementer と違う点は2つだけ＝`adopt-branch` と
カルテ入力」へ改訂済みだった。normative 側は karte の非対称だけを直後で開示し、`adopt-branch`
の非対称は Step 0 の項まで下らないと現れない構成になっており、正本（rules/05）と分岐していた
（`.claude/rules/01-principles.md`「PR8 消さないの適用範囲」区分2＝古くなった手順書は本文を書き換える、
に従い追記ではなく冒頭の記述自体を「push/merge の権限境界は同一」＋「違う点は2つだけ」に書き換えた）。

## Step 2 の `close-attempt --base` を明示させる理由（移設元：「Step 2: Fix」ステップ0/4）

`close-attempt` の `--base` 既定は `HEAD`。Step 2 の手順順序は「Edit → テスト → **commit/push** →
`close-attempt`」なので、`--base` を省略すると commit/push 直後は作業ツリーが HEAD と一致し、
diff が空になる。空の実測 touched-set が append-only の台帳へ無言で固定されるのは、実測信号
（次ラウンドの類似判定の入力）が静かに劣化する事故であり、実際に PR #353 是正ラウンド1で発生した
（Issue #355）。

対策としては (a) `--base` を毎回明示する、(b) `close-attempt` を commit 前（Edit 直後・作業ツリーに
差分がある状態）に呼ぶよう手順を入れ替える、の2案を検討した。**(b) は採らなかった**——`git diff HEAD`
は commit 前の状態では**未追跡（untracked）ファイルを含まない**。本ロールの修正が新規ファイル
（新しいテストファイル等・本リポジトリで頻出）を追加するケースでは、commit 前に呼ぶと touched-set が
不完全または空になり、#355 が守ろうとしている実測信号をむしろ弱める。commit 後（新規ファイルも
`/dev/null → b/path` の diff として現れる）に、ステップ0で控えた commit を `--base` に明示して渡す
(a) の方が、`gitgate add` と `gitgate commit` の間に verb 呼び出しを挟むような手順上の脆さも無く安全。
`HEAD~1` は「このラウンドの修正が1コミットに収まっている」場合の近似値にすぎず（pre-commit hook 等で
追加コミットが生じると誤る）、必ずステップ0で控えた実際の commit を使うことを明記している。

`--base` を明示しても diff が本当に空になるケース（レビュー観点の解釈違いで実装は元々正しく、
コード変更が不要だった等）はある。この場合だけ `--outcome no-change` を使う——CLI 側がそれ以外の
`outcome` では空 diff を fail-close で拒否する（Issue #355 の受入基準）。

## ゲート allowlist の内部名と `ingest-review` を deny する理由（移設元：「責務境界」「Bash 実行規律」・Issue #373）

規範側には**本ロールが実際に打てるコマンドの一覧（＝I/F）**だけを残し、統制側の内部構造と
「なぜ deny なのか」をここへ移した。

- **push/merge の非対称を機械化している実体**：`agent-command-gate.sh` の
  `GATED_ROLES` / `GITGATE_VERBS_BY_ROLE` / `GH_SUBCOMMANDS_BY_ROLE` に `issue-fixer` が登録済み。
- **`karte ingest-review` を本ロールに許さない理由**（Issue #341 F-341-04）：

  取り込みは「レビューアの指摘を台帳へ入れる」手続きで `status: resolved` を書けるため、是正当事者である本ロールが実行できると自分の指摘を消して 類似飽和ゲートを迂回できてしまう。

## 既知の限界（Issue #129で追跡・過信しない）（移設元：同名の節）

`agent-command-gate.sh` の判定はシェル文字列の**静的検査**であり sandbox ではない。`agent_type` の詐称・
ハーネス外の実行経路・許可されたテストランナー経由の任意コード実行は閉じきれない。
「Step 1 を通さずに Edit しない」は**プロンプトレベルの規範**であり、フックが直接強制するものではない
（`Edit` は `matcher: "Bash"` のゲートを通らない）。多層防御の一枚として守る。
## Codex fixer transport と bootstrap 境界（Issue #452・2026-08-26、supervisor採用 2026-08-30）

当初は `issue_<N>_fix_r<R>` task key と durable ownership ledger により、事前検証済みの
`.worktrees/<name>`、branch、expected OID、handoff へ束縛した Codex `isolation_only` transport を
宣言した。しかし PR #453 round 1 で、`spawn_agent` は child workspace を受け取れず、
PreToolUse も effective tool workdir、actual agent identity、spawn 成功を運ばないことが確定した。
事前worktree/ledgerだけでは実agentの束縛にならないため、`collaboration.spawn_agent`のCodex fixer transportは
unavailableとして既存trusted issue-start hookでfail-closeする。恒久経路はrepo supervisorが別Codex CLI processの
PID/start token、JSONL thread、workspaceを観測し、外側OS sandboxと内側Codex sandboxで束縛する方式だけとした。
Claudeの`isolation: worktree`とSubagentStart/Stop lifecycleは弱めない。方式比較とsecurity trade-offは
`docs/methods/codex-workspace-binding.md`。

この transport を導入する bootstrap PR の finding を、未導入 fixerを worker/implementerへ偽装して直す案は
却下した。レビューと修正の分離、karte の書き手、権限非対称を同時に破るためである。原則は finding を記録して
STOPし、supervisor経路が独立reviewと段階的probeを通るまで正規Codex fixerの起動を予定しない。
例外はオーナーが明示したbootstrap処置として別記録にし、正規fixer transportの起動実績または保証として扱わない。
PR #453の旧spawn consume成功はsuperseded evidenceであり、spawn_agent経路はunavailable deny、別process経路は
supervisorのP0〜P4 evidenceを正本とする。
