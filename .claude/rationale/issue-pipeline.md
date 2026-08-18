# issue-pipeline — 設計経緯・却下案・既知の制約（rationale・非規範）

> **これは規範ではない。** `.claude/skills/issue-pipeline/SKILL.md`（規範・正本）から Issue #372 で
> 移設した「設計判断の理由・却下案・既知の制約・実測ログ・残スコープの status note」の保管先
> （PR8「消さない」＝削除ではなく移設）。**skill ロード時に常駐しない**ので、行動を決める規範は
> すべて移設元に残っている。疑問が生じたときだけ参照する。
>
> - **移設元（規範・正本）**：`.claude/skills/issue-pipeline/SKILL.md`
> - **本文は逐語（verbatim）で移した**（内容の変更・要約・言い換えはしていない）。`##` 見出しだけ
>   移設先で付与し、どの節から来たかを併記している。
> - **相対参照は移設元の文脈を指す**：本文中の「後述」「上記」「下記」「本節」「②-a」等は
>   移設元ファイル内の位置関係であって、本ファイル内の位置関係ではない。
> - 分離の方針・4ツリー波及方針は `.claude/rationale/README.md`。

## 却下案：専用 `issue-triage` エージェントは作らない（移設元：① 処置順の原案）

  専用 `issue-triage` エージェントは作らない（generic な issue 読解で asset-auditor も新規不要と判定・A14 再利用優先／決定は対話側に残す）。

## `ISSUE_START_BINDING_V1` marker の enforcement の実体と reason code（移設元：②-a・Issue #373）

  この hook は `issue-implementer` への `Task`/`Agent` dispatch の `tool_input.prompt` に、次の機械可読行を
  **ちょうど1つ**含めることを要求する（契約の実体＝`issue_start/gate.py` の `_claude_request`・
  `issue_start/managed-entrypoints-v1.json` の `claude` transport）：

  - `entrypoint`：この managed entrypoint では常に文字列リテラル `"issue-pipeline"`
    （`managed-entrypoints-v1.json` の登録値と exact 一致が必須）。
  - `repository`：`git remote get-url origin` を `OWNER/REPO` の canonical 形へ変換した値
    （HTTPS/SSH いずれも可・`gate.py` の `_canonical_github_repository` と同じ正規化）。
  - `branch_name`/`base_ref`/`base_oid`：marker 内のこれらの値は
    branch-source ALLOW の根拠には**ならない**——`gitgate new-branch` が別途 fresh に再検証する
    （`docs/tools/issue-start-and-branch-source.md`「決定」節）。
  - **exact 7 field 以外の混在・fieldの欠如は拒否される**（`set(raw) != {entrypoint, repository, issue,
    branch_name, base_ref, base_oid, base_pr}` で `ISSUE_START_BINDING_UNKNOWN_FIELD`）。
  marker が**存在しない・prompt 中に複数行ある**場合は `ISSUE_START_BINDING_MISSING_OR_DUPLICATE` で
  hook が dispatch そのものを deny する（`issue-implementer` は起動されない）。値の型・形式不正
  （`base_oid` が40桁hexでない等）はそれぞれ専用の reason code（`ISSUE_START_BRANCH_INVALID`／
  `ISSUE_START_BASE_REF_INVALID`／`ISSUE_START_BASE_OID_INVALID`／`ISSUE_START_BASE_PR_INVALID`等）で
  fail-close する。別経路への迂回はできない。

> **なぜ規範側に I/F 仕様（7 field の表）を残し、ここには enforcement の内部だけを移したか**
> （Issue #373・オーナー判断）：上記の reason code・内部関数名は**書き手（dispatch する主文脈）が
> 正しい marker を組み立てるのに使わない**情報であり、間違えれば機械が必ず止める。一方
> 「どの field に何をどう書くか」は散文が唯一の伝達手段なので規範側に残す（marker 契約の記載漏れで
> dispatch が必ず deny された実例＝Issue #346）。単に「機械が検証している」と指すだけの一行
> ポインタへの置換は**採らない**——それでは書き手が何を書けばよいか分からない。

## `isolation: "worktree"` の enforcement の実体・#350 の発端・worktree の初期 HEAD（移設元：②-a・Issue #373）

  欠落・別値（`"remote"` 等）は
  `ISSUE_START_ISOLATION_NOT_WORKTREE` で dispatch そのものが deny される（契約の実体＝
  `managed-entrypoints-v1.json` の `claude` transport の `required_isolation`・enforcement＝
  `gate.py` の `_validate_isolation`）。
  - **これが `issue-implementer` の「isolated worktree」を成立させる唯一の手段**：実装者側には
    worktree を作る verb が無く（`gitgate`）、`cd` も deny される（`agent-command-gate.sh` 層2）ため、
    渡さなければ実装者は**主文脈と同じ working tree を branch switch して共有する**（＝主文脈の作業ツリーが
    実装対象ブランチへ意図せず切り替わる。#350 の発端）。
  - この worktree の初期 HEAD は `origin/<default>` 相当とは限らない。分岐元の正しさは marker ではなく
    `gitgate new-branch --base-oid` の fresh 再検証が担保する（上記）。

## `handoff_path` を作業ツリールート相対にした理由（移設元：②-a・Issue #373）

  相対パスなら定義上つねに
  implementer 自身の worktree 配下へ解決されるので、「別のワークツリーを指すパス」という脅威が検査ではなく構造で消える
  （Issue #350 実装時に、ハーネスが作業ツリー外への Write を機械的に拒否することを実測）。

## ②-c で主文脈が worktree を明け渡す手順が「唯一成立する経路」である理由（移設元：②-c）

  `issue-fixer` はメインワークツリーで動く非 isolated ロールであり、`gitgate` にも `issue-fixer.md` にも
  既存ブランチへ移る verb が無く（生 `git switch`/`checkout` は全 deny）、何もしなければメインワークツリーの
  `branch-current` が `main` のまま残り、`issue-fixer.md`「ブランチ規律」の契約どおり是正着手前に STOP する。
  **これは現状唯一成立する経路の開示であり設計選択ではない**（Issue #350 の AC1 と同性質）——`gitgate` に
  既存ブランチへ移る verb を新設する案、`issue-fixer` にも isolation を掛ける案はいずれも機構の新設に当たり、
  本節では採らない（別 Issue 化の可否はオーナー判断）。

## ②-c の残スコープ（Issue #310）と #369 との分担（移設元：②-c 末尾）

  **本手順は isolation 下でブランチを取得する手段に限定した記述であり**、カルテ機構への結線を扱う
  ②-c 本文の書き直しは引き続き Issue #310 の残スコープとする（先取り・上書きしない）。
  ※「実害」定義・エスカレーション条件は #310 から分離され、**#369 で本 SKILL.md に定義済み**
  （後述「実害の定義とエスカレーション条件」節）。

> **未了（Issue #310）**：上記の判定基準を **`karte` の呼び出し手順へ結線する**部分——`ingest-review` /
> `status` の実行タイミング、`tmp/_karte/active.json` の受け渡し、merge 時にカルテ本文を PR コメントへ
> 投稿する手順——は #310 の残スコープであり、本節はまだその形になっていない。
> **判定基準そのもの（実害の定義・エスカレーション条件）は #369 で本 SKILL.md に定義済み**で、
> #310 はそれを参照する（再定義しない）。

## Codex 版に worktree 解放手順が不要な理由（移設元：②-d）

  > **Codex 版（`.agents/skills/issue-pipeline/SKILL.md`）には本項は不要**：同ファイル ②-a の記述の
  > とおり Codex の `spawn_agent` には isolation パラメータが無く worktree 分離が行われないため、
  > `issue-implementer` は呼び出し元と作業ツリーを共有し、Codex 経路ではそもそも
  > `.claude/worktrees/agent-<id>/` が作られず残留も起きない。`asset_parity/exceptions.py` の
  > 非移植例外ではなく、isolation 機構の有無という実体差による（Issue #360）。

## 「実害の定義」節の残スコープ（移設元：実害の定義とエスカレーション条件・末尾）

> **本節は判定基準のみを定める**（Issue #369）。この基準を `karte` の呼び出し手順へ結線すること
> （`ingest-review` / `status` の実行タイミング・`active.json` の受け渡し・カルテ本文の PR コメント投稿）は
> **Issue #310 の残スコープ**であり、本節では扱わない。

## 却下案：SubagentStart フックは採らない（設計判断）（移設元：共通指示の配り方）

- **SubagentStart フックは採らない（設計判断）**：`SubagentStart`（`hookSpecificOutput.additionalContext` で子コンテキストへ注入可）は実在するが、
  本パイプラインでは採用しない。理由＝(1) 対象2エージェントは本パイプライン専用で、恒常契約は各 `.md` に置く方が可視・版管理でき常に効く（フックだと settings.json ＋シェルに分散）。
  (2) 本 repo でフックは**機械的に拒否できる境界**（push/merge ゲート＝agent-command-gate）に限定する慣行（PR2・機械判定と運用ルールを混ぜない）。ただし Bash 文字列の静的検査であり、非バイパスの完全防御とは扱わない。
  助言的指示の配布はその範疇でない。(3) 常時 ON のグローバル副作用は、明示ブロックに比べ保守面が重く不透明で、得られるトークン節約は限定的。

## エージェント定義スナップショット制約の実測ログと帰結（移設元：同名の節）

> **本節は Claude Code（`.claude/agents/*.md`・`Task`/`Agent` dispatch）の実測に基づく記述**。
> Codex CLI（`.codex/agents/*.toml`・`spawn_agent`）や Copilot が同種のスナップショット挙動を持つかは
> 未検証——確認できていないため、本節の内容を他ツリーへ追従させるかどうかは本 PR のスコープ外とする
> （Issue #360）。

- **実測①（Issue #323 / PR #358 の是正ラウンド）**：主文脈がメインワークツリーを PR ブランチへ
  `git switch` し、作業ツリー上の `.claude/agents/issue-fixer.md` が新契約（`handoff_path` を
  「作業ツリールート相対」で受理する契約）になった状態で `issue-fixer` を dispatch したところ、
  起動した `issue-fixer` は**その時点で作業ツリーに反映されていたはずの新契約ではなく旧契約**
  （`handoff_path` を「メインワークツリーの絶対パス・完全一致」で検証する契約）のまま動き、新契約の
  形で渡された `handoff_path`（例：`tmp/_handoff/issue-fixer--issue-323-r1.yaml`）を「絶対パスでない／
  ファイル名が旧契約の完全一致条件を満たさない」として拒否し STOP した。
- **実測②（PR #361 是正ラウンド1・Issue #360）**：**同一セッション内**で、実測①と同種の場面
  （PR #358 是正ラウンド）では旧契約が適用された一方、時間的に後続する本 PR の是正ラウンドでは
  `issue-fixer` が**新契約**（`handoff_path` の絶対パス入力を拒否し STOP）で動いた。**同一セッション
  内で適用契約が旧→新に変わりうる**ことを示しており、「セッション開始時点で1回だけロードされ以後
  一切再ロードされない」という単純な固定モデルとは矛盾する。
- **`issue-fixer` 側の各回の判断自体は正当**：それぞれの回でロードされていた契約に照らせば正しい
  fail-close であり、欠陥はエージェント定義の記述にはない。欠陥は「作業ツリーの現在の内容」と「その
  dispatch で実際に適用される契約」がズレうる、かつ**そのズレ方（更新タイミング）が未解明**という、
  ハーネスのロード挙動そのものにある。
- **帰結**：**エージェント契約（`.claude/agents/*.md`）を変更する PR は、その変更を実装している
  セッション自身の中で、変更後の契約が確実に適用されると当てにできない。** `/issue-pipeline` は自分
  自身の運用資産（`issue-implementer`/`issue-fixer`/`pr-reviewer` の契約）を改修対象にもする
  （ドッグフーディング）ため、この制約はパイプライン運用に直接効く——同一セッション内でこれらの契約を
  変える Issue を実装し、同じセッションで変更後の版を dispatch しても、その dispatch がどちらの契約で
  動くかは事前に確定できない。
- **本節は制約の明文化と回避手順の共有に留める**：エージェント定義のスナップショット挙動を機構として
  解消・安定化すること（更新トリガーの解明・動的リロード等）は本節の対象外。機構側の対処が要るかは
  オーナー判断で別途（Issue #360 Out of scope）。
