# issue-pipeline — 設計経緯・却下案・既知の制約（rationale・非規範）

> **これは規範ではない。** `.claude/skills/issue-pipeline/SKILL.md`（規範・正本）から Issue #372 で
> 移設した「設計判断の理由・却下案・既知の制約・実測ログ・残スコープの status note」の保管先
> （PR8「消さない」＝削除ではなく移設）。**skill ロード時に常駐しない**ので、行動を決める規範は
> すべて移設元に残っている。疑問が生じたときだけ参照する。
>
> - **移設元（規範・正本）**：`.claude/skills/issue-pipeline/SKILL.md`
> - **本文は移設元の文言を尊重して移した**（内容の変更・要約はしていない）。ただし `##` 見出しの
>   付与に加え、複数節をまとめる際・切り出した断片を単独の節として成立させる際に必要な最小限の
>   接続語・言い換えは補っている（見出しだけを付与した逐語移設ではない）。移設先で `##` 見出しを
>   付与し、どの節から来たかを併記している。
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
    渡さなければ実装者は主文脈と working tree を共有してしまう（渡さなかった場合の帰結＝規範側
    SKILL.md 参照。#350 の発端）。
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

### #354/#374 で機構を新設し、「主文脈が worktree を明け渡す」部分は解消した（2026-08-19・PR-3）

上記のうち**worktree の明け渡し（ハンドオフの回収 → `git worktree remove --force`）を主文脈の
手順として書いていた部分は、機構の新設によって解消済み**であり、規範側（SKILL.md ②-c／②-d）から
削除した。経緯を保全するため、何がどう変わったかをここに残す（PR8 区分1）。

- **旧状態（#350／#360 時点）**：②-c と ②-d の双方に「①ハンドオフを Read する → ②
  `git worktree remove --force` → ③ `git switch`」という**ほぼ同一の3手順が二重に書かれ**、
  ②-d 側はさらに「②-c を経由したか」で各手順を分岐させていた。手順の実行も、経由したかの
  判定も、**主文脈の記憶**に依存していた。
- **なぜ機構化したか**：#354 が実測したのは「残留 worktree があるのに `pr-reviewer` を dispatch し、
  レビューアが古い作業ツリーを掴んだ」という事象で、**レビュー結果の信頼性そのものが損なわれる**害だった。
  旧 SKILL.md は残留の害を「ディスク使用量の増大と `git worktree list` の可読性低下」と書いており、
  この過小評価も同時に訂正した（区分2＝本文の書き換え）。
- **新機構（#309 PR-1 → #354 PR-2 → PR-3 の3段）**：
  1. **PR-1**：worktree 所有台帳（`tmp/_worktree/ledger.json`）で「どの worktree がどの dispatch の
     ものか」を観測可能にした。この時点では**何も削除せず何も deny しない**。
  2. **PR-2**：`gitgate` に `collect-worktree`（回収→検証→解放の段構造）／`worktree-release`／
     `worktree-forget` を実装。**削除経路を1箇所に集約**した。
  3. **PR-3**：`SubagentStop` が `running`→`stopped` を経て `collect-worktree` を起動し（自動解放）、
     `issue-start-gate` が残留状態の次 dispatch を deny する（統制の発効）。
- **「統制を先に、付与は別 PR」の順序**：観測（PR-1）→ 削除経路の実装（PR-2・ただし gated ロールへは
  未付与のまま）→ 自動実行と deny（PR-3）という順に分けたのは、削除能力が統制より先に効き始める
  状態を作らないため。
- **解消していない部分**：`issue-fixer` が非 isolated であること自体は変わっていないので、
  ②-c の `git switch <branch>`（メインワークツリーを PR ブランチへ載せる一手）は残っている。
  `issue-fixer` の isolation 化は後続 PR のスコープ。上段の「唯一成立する経路」の記述は、
  **この `git switch` の部分についてのみ**今も有効である。

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

### この却下は Issue #309 で**部分的に覆した**（2026-08-19・PR-1）

上記の却下は**恒常契約の配布**という用途に対するものであり、その部分は今も生きている
（`issue-implementer`/`pr-reviewer`/`issue-fixer` の恒常契約は各 `.md` に常設したままで、
フックへは移していない）。**覆したのは「`SubagentStart`/`SubagentStop` をこのパイプラインでは
一切使わない」という含意の部分だけ**である。

- **理由(2)は覆っていない・むしろ根拠になった**：#309 で登録した3フックはいずれも
  「機械的に拒否できる境界」に閉じている——`SubagentStop` の `{"decision":"block"}` は
  **カルテ未更新のまま停止することを機械的に拒否する**ゲートであり、`SubagentStart` の
  worktree 束縛は**観測できない状態（worktree ↔ dispatch の所有関係）を観測可能にする**
  ための記録である。恒常契約という「助言的指示の配布」ではない。
  カルテの注入（`subagent-karte-inject.sh`）だけは助言に当たるが、これは
  「呼び忘れたら過去の試行を知らないまま修正に入る」という **#307/#309 が塞ごうとしている失敗
  そのもの**が対象で、`karte/cli.py` の `cmd_render` docstring（K-14）が「注入側に寄せた」と
  記録している設計判断に従う。
  **K-14 準拠の実体は「フックが `python3 -m karte render --issue <N>` を実行し、その標準出力を
  `additionalContext` に載せること」**であり、手順書（`karte-protocol.md`）の注入だけでは
  K-14 を満たさない——手順書は「render を呼べ」という規範であって render の出力ではなく、
  是正エージェントに render を引かせる形は K-14 が明示的に却下した設計だから。
  PR-1 の初版は手順書だけを注入しており、この点はレビュー指摘 F-309-04 として是正した
  （現在は手順書＋render 出力の2節を連結して注入する。render が取れないときは
  手順書だけに縮退＝注入は助言なので fail-open）。
- **理由(1)（フックだと settings.json ＋シェルに分散して可視性が落ちる）への対処**：
  注入本文はシェルから分離して `.claude/hooks/karte-protocol.md` に置き（`inject-governance.sh` と
  同作法）、判定ロジックは `issue_start/subagent_hooks.py` に置いて `.sh` は薄い起動口に留めた。
  分散の度合いを、既に同じ構成を採っている `issue-start-gate.sh` と同水準に抑えている。
- **理由(3)（常時 ON のグローバル副作用）への対処**：3フックとも `matcher` で対象ロールを絞り、
  **さらにスクリプト内でも `agent_type` を判定して対象外は stdout 無出力 exit 0** にした
  （`agent-command-gate.sh` の「対象外ロールは常に許可」不変条件と同型。ただし stderr には
  観測した payload のキー集合と判定結果を1行残す——「発火しなかった」と「発火したが対象外と
  判定した」を V-1/V-2 の実測で区別するため＝F-309-05）。二重にしたのは
  `SubagentStart`/`SubagentStop` の `matcher` が `agent_type` 名で効くかが本 repo で未実測
  （要実測事項 V-2）だから——効かなくても他ロール・主文脈へ副作用が漏れない。
- **覆した範囲の限定**：#309（PR-1）の時点で worktree の**削除**経路は1つも実装していない。
  `SubagentStop` による自動回収・自動解放と、残留 worktree での dispatch deny は
  後続 PR のスコープであり、本節の却下を根拠に据え置いているわけではない。

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
