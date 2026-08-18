---
name: issue-pipeline
description: Orchestrate a batch of open GitHub Issues through implement→PR→review→merge→close, one Issue at a time. The main thread stays thin — it triages processing order, dispatches issue-implementer / pr-reviewer sub-agents (model tier via bloom-model-tier, risk-based reviewer model), exchanges decisions with the owner via AskUserQuestion (showing premises/tradeoffs first), and tracks progress. Use when issue handling should proceed end-to-end with governance. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
---

# Issue 処理パイプライン（implement → PR → review → merge → close の連続処理）

> 複数のオープン Issue を **1件ずつ完結**させる repo 運用オーケストレータ。主文脈（このスキルの呼び出し元）は
> **よほど軽微でない限り自分で実装せず**、タスク管理・進捗報告・オーナーとの意思決定に専念する（Issue #120 ③）。
> ファンアウト実行は `issue-implementer`（実装→PR）と `pr-reviewer`（レビュー→マージ）へ委譲し、
> 重い調査は `agy-delegate` を積極利用する。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR7 空で止めない・PR8 消さない）／規約：[CLAUDE.md](../../../CLAUDE.md)
> （スコープ拡大禁止＝[`.claude/rules/03-operational.md`「スコープ拡大禁止」](../../rules/03-operational.md)・
> スケジュール独断禁止・AI-attribution・Bloom 委譲）。**このスキルはそれらを再掲せず、上に立って回す**。
> **本ファイルは規範（normative）だけを載せる**（Issue #372）。設計判断の理由・却下案・残スコープの
> status note・実測ログは [`.claude/rationale/issue-pipeline.md`](../../rationale/issue-pipeline.md) に
> 移設済み（削除ではなく移設＝PR8）。分離の方針＝[`.claude/rationale/README.md`](../../rationale/README.md)。

## 役割分担（DD-22 の対話／非対話境界を厳守）
- **主文脈＝対話オーナー**：`AskUserQuestion` を持つのはここだけ。**順序決め・オーナー判断・先送り可否・スコープ拡張の起票判断**を担う。
- **`issue-implementer` / `pr-reviewer`＝非対話ファンアウト**：`AskUserQuestion` を持たない。曖昧・矛盾に当たったら**STOP して報告**（意見なき停止禁止＝原案＋比較＋推奨を添えて返す）。
  対話ロジックを非対話エージェントに埋め込まない／順序・オーナー判断を主文脈から外へ出さない（DD-22）。
- **権限境界はハーネスで機械強制**（`.claude/hooks/agent-command-gate.sh`・PreToolUse）：`issue-implementer` は push/PR 可・merge 不可、
  `pr-reviewer` は merge 可・push 不可。プロンプトの自制ではなく機械ゲート（既知の限界は Issue #129・多層防御の一枚）。

## 段（各 Issue を直列に回す。バッチ内 Issue は ① で順序確定）

### ① 処置順の原案 → オーナー承認（主文脈・対話）
オープン Issue 一覧から**推奨処置順**を立てる（Issue #120 ①）。
1. `gh issue list` で対象を確定。各 Issue の本文・相互参照（"depends on #N" / "blocked by" / 同一ファイル群を触る等）を読む。
   - **読み取りが重いバッチ（多数 Issue・横断調査が要る）なら read-only 委譲でコンテキストを節約**：一般調査は `general-purpose`/`Explore`、
     大規模な横断影響調査は `agy-delegate`（疎通 OK 時）へ。**ただし「推奨順」を決めるのは主文脈**（対話オーナーが即 AskUserQuestion できるため・DD-22）。
     専用 `issue-triage` エージェントは作らない（却下理由＝`.claude/rationale/issue-pipeline.md`）。
2. 依存を有向グラフ化し、**順序必須（前段の成果に依存）**と**並列可（独立）**を分離。ブロッカーを先に、葉を後に。
3. **原案＋根拠＋メリデメを必ずチャットに提示してから** `AskUserQuestion` で承認/修正を仰ぐ（Issue #120 ③・空で止めない）。
   提示物＝依存グラフ要約・推奨順・並列可否・各 Issue のリスク見立て（② のレビュー model 選定に使う）。

### ② 1 Issue を完結（承認された順に直列。前 Issue が merge & close 済みになってから次へ・Issue #120 ②）
各 Issue につき次を回す。**主文脈は dispatch と進捗記録に専念し、実装・レビューはしない**。

**②-a 実装（`issue-implementer` へ委譲）**
- **dispatch の直前に managed Issue-start gate を通す（`issue-start-gate`・`.claude/hooks/issue-start-gate.sh`・PreToolUse）。**
  `issue-implementer` への `Task`/`Agent` dispatch の `tool_input.prompt` に、次の marker 行を
  **ちょうど1つ**含める。欠落・重複・値の不正はいずれも hook が dispatch そのものを deny する
  （`issue-implementer` は起動されない）。
  ```
  ISSUE_START_BINDING_V1={"entrypoint":"issue-pipeline","repository":"OWNER/REPO","issue":N,"branch_name":"BRANCH","base_ref":"DEFAULT","base_oid":"40-HEX","base_pr":null}
  ```
  **書くべき値＝下表の7 field ちょうど**（過不足はどちらも拒否される。marker は1行の JSON）：

  | field | 型 | 何を書くか |
  |---|---|---|
  | `entrypoint` | 文字列 | 常にリテラル `"issue-pipeline"` |
  | `repository` | 文字列 | `git remote get-url origin` を `OWNER/REPO` 形へ正規化した値（HTTPS/SSH どちらの remote でも同じ値になる） |
  | `issue` | 整数 | dispatch 対象の Issue 番号（1以上。文字列にしない） |
  | `branch_name` | 文字列 | 実装者に切らせるブランチ名 |
  | `base_ref` | 文字列 | 分岐元の既定ブランチ名（例 `main`） |
  | `base_oid` | 文字列 | fresh fetch 済み `origin/<base_ref>` の exact 40 桁 hex OID |
  | `base_pr` | 整数 または `null` | stacked branch のときだけ same-repository の OPEN PR 番号。それ以外は `null` |

  `branch_name`/`base_ref`/`base_oid`/`base_pr` は、後続で実装者へ渡す
  `python3 -m gitgate new-branch <name> --repository OWNER/REPO --base-ref DEFAULT --base-oid OID [--base-pr N]`
  と**同じ値**にする。ただし marker 内のこれらの値は branch-source ALLOW の根拠には**ならない**——
  `gitgate new-branch` が別途 fresh に再検証する。
  （deny の reason code 一覧・enforcement の実体・設計根拠＝`.claude/rationale/issue-pipeline.md`）
- **同じ dispatch に `isolation: "worktree"` を渡す（Issue #350・同じ hook が機械的に強制）。**
  `Task`/`Agent` 呼び出しの**パラメータ**として渡す（prompt 本文ではない）。欠落・別値（`"remote"` 等）は
  dispatch そのものが deny される。
  - **これが `issue-implementer` を独立 worktree で走らせる唯一の手段**：渡さなければ実装者は
    **主文脈と同じ working tree を branch switch して共有する**（＝主文脈の作業ツリーが実装対象ブランチへ
    意図せず切り替わる）。渡すと cwd は `.claude/worktrees/agent-<id>/` の locked worktree になり、
    主文脈のメインワークツリーは切り替わらない——**主文脈は自分のツリーで triage・進捗記録を続けられる**。
  - **要求は `issue-implementer` にだけ掛かる**。他の subagent（`pr-reviewer`・各 `*-author` 等）の
    dispatch は manifest 上 unmanaged で素通しされるので、`isolation` を付ける必要はない。
  （reason code・enforcement の実体・#350 の発端・この worktree の初期 HEAD に関する注意＝
  `.claude/rationale/issue-pipeline.md`）
- **model/effort は [bloom-model-tier](../bloom-model-tier/SKILL.md) のルーブリックで決める**（Issue #120 ④）。実装は既定 `sonnet`。
  Bloom Lv6・判断ボトルネック（曖昧仕様からの新規構造化・不可逆な設計判断を含む Issue）なら `model: opus` override で dispatch。
- dispatch prompt には**タスク固有情報のみ**（Issue 番号・関連ノード ID・スコープ）＋**共通契約への参照**（下記「共通指示の配り方」）。
- **`handoff_path` は主文脈が「作業ツリールート相対」で採番して渡す**（Issue #323 で確定）：
  `tmp/_handoff/issue-implementer--issue-<N>[-<suffix>].yaml`。**絶対パスは渡さない**——implementer は
  `isolation: "worktree"` 下で動き、**ハーネスが作業ツリー外への Write を機械的に拒否する**ため、
  メインワークツリーの絶対パスへはそもそも書けない（相対にした設計根拠＝`.claude/rationale/issue-pipeline.md`）。
  - **ファイル名の採番権は主文脈に残す**（取り違え・注入の防止）。implementer は自分でファイル名を組み立てず、
    渡された相対パスをそのまま使う。受理条件（相対であること・`..` 不可・`tmp/_handoff/` 直下1ファイル・
    `issue-<N>` の境界一致・サフィックスの文字種・symlink 不可）を満たさなければ STOP する契約
    （`issue-implementer.md`「入力」）。渡し忘れも同じく STOP。
  - **同一 Issue の複数ラウンドは `<suffix>` で分ける**（初回 `…--issue-<N>.yaml` ／ 是正1回目
    `…--issue-<N>-fix1.yaml` のように主文脈が採番する）。同じファイル名を再利用すると前ラウンドの PR URL・
    判断根拠・スコープ外指摘を上書き破壊する（`<key>` 一意化＝Issue #278／本件の発端＝Issue #323）。
    `<suffix>` に使える文字は `[A-Za-z0-9._-]`。
- 戻り＝`HANDOFF: <implementer が実際に書けた絶対パス>` ＋1行要約。implementer は isolated なので実体は
  `.claude/worktrees/agent-<id>/tmp/_handoff/…` にあり、**主文脈のメインワークツリー側には存在しない**。
  **PR URL・変更ファイル一覧・テスト結果・スコープ外指摘は主文脈が返ってきた絶対パスを Read して取る**
  （1行要約だけで判断しない。主文脈は isolated ではないので読める）。**`status: stop`（曖昧・矛盾）なら
  `stop_reason` ごと主文脈で受けてオーナーへ**（PR7）。

**②-b 初回レビュー（`pr-reviewer` へ委譲・model はリスクで選ぶ）**
- **初回レビューの model はリスク/難易度で選ぶ**（Issue #120 ④）。レビュー＝Bloom Lv5 評価。下の**リスク信号表**で `sonnet` / `opus` を機械的に引く
  （「判断で」で済ませない）。既定 override なし＝`sonnet`、opus 該当時のみ `model: opus` で dispatch。
- **`pr-reviewer` が各 finding に記入する `harm`（`real` / `none`）の線引きは、後述
  「実害の定義とエスカレーション条件」節が定める**（Issue #369）。`pr-reviewer.md` はこの節を参照する契約になっている。
- **指摘の処置要否・処置担当モデル（Sonnet 降格可否）は `pr-reviewer` 自身が決める**（Issue #120 ④・主文脈は決めない）。
  レビューアが「指摘は明確・機械的 → Sonnet で処置」と判断したら、主文脈はその指示どおり ②-c を回すだけ（降格判断を横取りしない）。
- **レビュー指摘・処置結果は PR レビューコメントに残す**（Issue #120 ⑥・Claude Code(AI) 明記＋具体的な変更/根拠。`gh pr comment`。
  承認/却下ステータスを偽らない＝`pr-reviewer.md` の絶対規範）。

**②-c 是正 → 再レビュー（指摘があった場合のループ）**
- **是正は `issue-fixer` へ差し戻す**（`issue-implementer` ではない＝Issue #308。`pr-reviewer` は push 不可＝コードを書けない）。
  `issue-implementer` は**初回実装専任**で、是正依頼を受けたら STOP する契約になっている。担当 model は
  **②-b でレビューアが決めた降格判断に従う**（明確な指摘なら `sonnet`）。
- **レビュー結果を先にカルテへ取り込む**（`issue-fixer` を dispatch する前）。`pr-reviewer` は構造化 finding
  （`### F-<issue>-<seq>` ブロック＋`harm`/`harm_detail`/`severity`/`locus`/`summary`/`evidence`/`expected`/`recheck`/`status`）を
  返すので、主文脈がそれをファイルへ書き出して取り込む：
  `python3 -m karte ingest-review --issue <N> --round <R> --from <path>`
  **`--from` に渡すレポートは repo-root 配下（例 `tmp/` 配下）へ書き出す**——`karte` は `resolve_within_repo` で
  リポジトリ外のパスを fail-close で拒否するため、スクラッチパッド等へ書くと取り込みが失敗する
  （`tmp/` は gitignore 済みでコーパスを汚さない）。
  （ID の採番・再発番検出・前ラウンド未解消 finding の全件再掲チェックはこの CLI が fail-close で行う）。
  **`ingest-review` は主文脈が実行する**——是正当事者である `issue-fixer` には権限ゲートで許可されていない
  （自分の指摘を `resolved` にできてしまうため・Issue #341 F-341-04）。
- **`round` と、メインワークツリーの絶対パスとしての `karte_path` を主文脈が渡す**（`handoff_path` とは
  受け渡し方式が異なる＝下記。カルテは fixer の出力ではなく**ラウンドをまたぐ主文脈側の台帳**のため絶対のまま）：
  `<main-worktree>/tmp/_karte/issue-<N>.md`。渡し忘れたら `issue-fixer` は STOP する契約（`issue-fixer.md`「入力」）。
  進行ポインタ `tmp/_karte/active.json` は `ingest-review` が更新する。
  - **`handoff_path` は `issue-fixer` にも渡す。ただし ②-a と同じ「作業ツリールート相対」**（Issue #323）：
    `tmp/_handoff/issue-fixer--issue-<N>-<ラウンドを区別するサフィックス>.yaml`。**ラウンドごとに別サフィックスを
    採番する**（使い回すと前ラウンドの是正記録を上書き破壊する）。`karte_path` だけが絶対パスなのは、カルテが
    本ロールの出力ではなく**ラウンドをまたぐ主文脈側の台帳**だからで、その受け渡し方式の見直しは Issue #354 の範囲。
    戻りは `HANDOFF: <fixer が実際に書けた絶対パス>` ＋1行要約で、主文脈はその絶対パスを Read する。
- **dispatch 前に主文脈が実装者 worktree を明け渡し、メインワークツリーを PR ブランチへ載せる**
  （isolation 必須化の帰結・Issue #350／F-350-02）。②-a で `isolation: "worktree"` を渡した結果、
  PR ブランチは実装者の `.claude/worktrees/agent-<id>/` に checkout されたままになっている。
  **これは現状唯一成立する経路の開示であり設計選択ではない**（理由・却下した代替案＝
  `.claude/rationale/issue-pipeline.md`）。主文脈は `issue-fixer` dispatch 前に次を実行する：
  1. **実装者のハンドオフを先に Read する（必須・条件付きではない）**。②-a の契約により、ハンドオフは
     **必ず**実装者 worktree 配下（`.claude/worktrees/agent-<id>/tmp/_handoff/…`）に書かれており、
     次の手順 2 が `--force` でその worktree ごと消す。Read を飛ばすと PR URL・テスト結果・スコープ外指摘が
     回復不能に失われる。宛先は実装者がチャットで返した絶対パス（`git worktree list` で
     `.claude/worktrees/agent-<id>/` を特定してもよい）。他に回収すべき成果物が残っていないかも併せて確認する。
  2. `git worktree remove --force .claude/worktrees/agent-<id>/` で実装者 worktree を解放する
     （実装フェーズは完了済みで、手順 1 で回収済みなので安全）。
  3. `git switch <branch>` でメインワークツリーを PR ブランチへ載せる。
  これでメインワークツリー上の `branch-current` が PR ブランチになり、`issue-fixer` は契約どおり進める。
- `issue-fixer` は**診断してから直す**（`karte render` で前ラウンドの試行・転換指令・未解消 finding の
  `expected`/`recheck` を引き、`karte append` で診断を登録してからコードを触る）。同じアプローチの3件目は
  `append` が機械的に拒否する＝**ラウンド上限ではなく類似で切る**。
- **再レビューは常に Sonnet**（Issue #120 ⑤・`pr-reviewer` を override なし＝既定 `sonnet` で dispatch）。
- **続行/停止は後述「実害の定義とエスカレーション条件」節で判定する**（Issue #369）。
  続行＝残存指摘に「実害あり」が1件以上あるとき。条件 (a)〜(d) のいずれかが成立したら主文脈が STOP して
  オーナーへ打ち上げる。**ラウンド上限は設けない**。**未解消 finding が0件（genuinely clean）になったら
  条件 (a)〜(d) の判定を待たずそのまま下記 ②-d のマージ経路へ進む**（条件 (a) は未解消 finding が
  1件以上残っている場合の基準であり、0件のケースには適用しない——0件を条件 (a) の対象に含めると、
  空集合に対する「すべて実害なし」の空真判定で全 clean PR が不要に STOP してしまう）。
- **握りつぶし禁止**：対応不要に見えても FND/Q 起票を主文脈へ提案させ、据え置きはオーナー判断（下記 ③・④）。

> **未了**：判定基準を `karte` の呼び出し手順へ結線する部分は Issue #310 の残スコープ
> （詳細＝`.claude/rationale/issue-pipeline.md`）。判定基準そのものは後述の節で定義済み。

**②-d マージ → クローズ → 次へ**
- `pr-reviewer` が genuinely clean と判断したら `gh pr merge`（マージは reviewer 専権・機械ゲート）。
- `Closes #N` で自動クローズされなければ主文脈がクローズ（クローズは主文脈がしてよい）。**merge & close を確認してから次 Issue へ**（Issue #120 ②）。
- **実装者 worktree を解放する**（isolation 必須化の帰結・Issue #350／②-c と同じ理由・②-c に手順が
  あるのは是正ラウンドを経由した経路だけで、**指摘なしの clean merge 経路（本節）には従来抜けていた**
  ＝Issue #360）。②-a で `isolation: "worktree"` を渡した結果、実装者の
  `.claude/worktrees/agent-<id>/` が locked worktree として checkout されたまま残っている。
  clean merge 経路は `issue-fixer` を経由しない（②-c の worktree 解放ステップを一度も通らない）ため、
  ここで明示的に解放しないと **clean merge のたびに locked worktree が残留する**（実測：
  `git worktree list` に残骸が多数存在）。**②-c を経由済みなら手順1・2は②-c 自身の手順1・2で
  既に完了しているためスキップする**（未経由のときだけ本節が担う）。merge & close を確認したら：
  1. **②-c を経由していなければ、実装者のハンドオフを先に Read する（必須・条件付きではない）**。
     ②-a のハンドオフ絶対パス。PR URL・変更ファイル一覧・テスト結果・スコープ外指摘。
     （②-c を経由していれば、②-c 自身の手順1で既に Read 済み——再読不要）。
  2. **②-c を経由していなければ**、`git worktree remove --force .claude/worktrees/agent-<id>/` で
     実装者 worktree を解放する（実装・レビューは完了済みで、手順1 で回収済みなので安全。対象
     `agent-<id>` は `git worktree list` で特定してよい）。**②-c を経由していれば、②-c 自身の
     手順2で既に解放済みなので実行しない**（対象不在の worktree に対する remove は失敗する）。
  3. **②-c を経由していれば**主文脈のメインワークツリーが PR ブランチへ切り替わったままなので、
     `git switch main` 等で戻す（②-c 自身の手順3で PR ブランチへ載せた分の対）。②-c を経由していない
     完全な clean merge では主文脈は元々ブランチ切替していないため本手順は不要。

  > **Codex 版（`.agents/skills/issue-pipeline/SKILL.md`）には本項は不要**（理由＝
  > `.claude/rationale/issue-pipeline.md`。`asset_parity/exceptions.py` の非移植例外ではない）。

  この手順を怠っても実装・レビュー結果には影響しないが、locked worktree の残留は
  ディスク使用量の増大と `git worktree list` の可読性低下を招くため、**次 Issue へ進む前に必ず実施する**。

### ③ スコープ拡張は別 Issue に逃がす（PR 肥大化の抑制・Issue #120 ⑧）
レビュー/調査中に**現 PR/Issue のスコープを超える対応**が要ると分かったら、現 PR で直さず **サブ Issue / 別 Issue を起票**（`gh issue create`）。
- `issue-implementer`/`pr-reviewer` は「スコープ外指摘」を報告して STOP する（自分で直さない・
  [`.claude/rules/03-operational.md`「スコープ拡大禁止」](../../rules/03-operational.md)）。**起票の実行は主文脈**。
- doc-system-v2 に関わる指摘なら FND/Q ノード起票（`verification-author` 経由）も併せて主文脈が判断（CLAUDE.md）。

### ④ 先送りは必ずオーナー許可（独断禁止・Issue #120 ⑨ / CLAUDE.md スケジュール独断禁止）
指摘・対応を先送り/繰り越すときは、**背景・検討結果・メリデメを提示した上で `AskUserQuestion` で許可を取る**。
- **AI が単独で「対応不要」「後でよい」「次スプリント繰り越し」と結論づけない**（CLAUDE.md・過去インシデント）。
- `scheduled` は空のまま「今実施 vs 繰り越し＋推奨」を添えて委ねる。判断者と理由をコメント/ノードに明記。

## 実害の定義とエスカレーション条件（②-b の `harm` 記入・②-c の継続/停止判定の判定基準・Issue #369）

`pr-reviewer` が全 finding に記入する `harm`（`real` / `none`）の線引きと、②-c の是正ループを
いつ続け・いつ止めてオーナーへ打ち上げるかの条件を、ここで定める。**②-b と ②-c の双方がこの節を参照する。**

### 「実害」の定義

**A. 機能・安全に関わる実害**

1. **正しさ** — 仕様・SPEC・設計ドキュメントに対する振る舞いの不一致（テスト失敗・期待値相違を含む）
2. **退行** — これまで通っていた振る舞い／テストを壊している
3. **fail-close の破れ** — 機械ゲート・検証・権限境界が迂回可能になる
4. **正本・履歴の破損** — `doc-system-v2/` / `docs/` / `.claude/` や履歴を壊す・消す（PR8 違反）
5. **契約違反** — ノード規約・`ref_version`・辺記法・4ツリー parity・CI を落とす変更
6. **秘密・コスト** — 資格情報の露出、無認可の課金構成

**B. 後工程が誤読・誤操作するリスク（品質系＝これも実害あり）**

7. **誤読リスク** — コメント・実装・ドキュメント間の不整合により、それを読んだ
   **後工程作業者（人・エージェント）が誤読するリスク**があるもの
8. **名前と実体の不一致** — 関数/変数/ノード名・型名が実際の振る舞いと食い違う
9. **トレーサビリティ断絶** — 指摘・決定・処置の対応が追えない（ID 欠落・根拠未記載・PR コメント不備）
10. **正本の分岐** — 同じ事実が2箇所にあり片方だけ更新される構造
    （`check-governance-drift.sh` が機械検知しているまさにその失敗）
11. **暗黙の前提** — 明文化されていない前提に依存し、知らない後工程が壊せてしまう
12. **観測不能** — 失敗・エラーが黙って握り潰され、後工程が異常に気づけない
13. **再現性の欠如** — 検証手順・テストが無く、後工程が同じ判断を再現できない

**実害なし**＝上記いずれにも当たらないもの。典型＝純粋な整形・語順の好み、予防的リファクタ、
レビュー対象 PR のスコープ外の改善提案、レビューアが実体（Read した差分）で根拠を示せていない推測。

**迷ったら `real` 側に倒し、`harm_detail` に迷った理由を書く**（握りつぶさない・`pr-reviewer.md`）。

**本節（A群1〜6・B群7〜13）が正本**。`pr-reviewer.md`／`.codex/agents/pr-reviewer.toml` は本節の
項目名を要約として転記しているだけであり、**両者の一致を検査する機械手段は無い**。本節を追加・改名したら
`pr-reviewer.md`／`.toml` 側の列挙も揃えて更新すること（追従漏れに気づいたら FND として起票する）。

### エスカレーション条件（**ラウンド上限は設けない**）

続行＝残存指摘に「実害あり」が1件以上あるとき。次のいずれかが成立したら主文脈が STOP して
`AskUserQuestion` でオーナーへ打ち上げる：

- (a) 残存指摘が**1件以上あり、かつそのすべてが実害なし**になった（未解消0件＝genuinely clean のときは
  この条件の対象外——上記②-c本文のとおり判定を待たずそのまま ②-d のマージ経路へ進む）
- (b) **同一 `finding_id` が3ラウンド連続で未解消**（＝無進捗。ラウンド上限ではない）
- (c) `karte append` が類似飽和で拒否した状態から、転換後も類似判定を外せない
- (d) `issue-fixer` が `status: stop`（矛盾・情報不足）を返した

> **`karte status` の出力との対応**（名称の食い違い防止・機械結線自体は Issue #310 のスコープ外）：
> `verdict` は `clean`（未解消0件）／`harmful-open`（実害あり残存）／`no-harm-only`（残存はあるが
> 全件実害なし）の3値、`escalate` フラグは条件 (b) 無進捗・(c) 飽和**のみ**を機械判定した値
> （`karte/cli.py` の `_status_payload`）。**条件 (a)（`verdict: no-harm-only`）・条件 (d)
> （`issue-fixer` の `status: stop`）は `escalate` フラグに含まれない**——`escalate: no` は
> 「打ち上げ不要」を意味しないので、主文脈は `escalate` だけでなく `verdict` と `issue-fixer` の
> 返り値も併せて確認する。

**「実害なし」＝「対応不要」ではない。** AI が単独で対応不要と結論づけるのは禁止（CLAUDE.md）なので、
実害なし判定の指摘も握りつぶさず、主文脈が Issue 起票案＋理由付き推奨を添えて打ち上げ、
据え置きはオーナーが決める。

> **本節は判定基準のみを定める**（Issue #369）。`karte` 呼び出し手順への結線は Issue #310 の
> 残スコープ（詳細＝`.claude/rationale/issue-pipeline.md`）。

## リスク信号表（②-b 初回レビュー model 選定・bloom-model-tier の軸2を Issue レビューに具体化）
レビュー＝Bloom Lv5 評価。**判断ボトルネック側の信号が1つでも強く立てば `opus`、すべて網羅性側なら `sonnet`（+high effort）**。

| 信号 | Sonnet 寄り（網羅性ボトルネック） | Opus 寄り（判断ボトルネック） |
|---|---|---|
| ブラストレディアス | 局所（1〜数ファイル・限定モジュール） | コーパス横断・共有資産・多数ノードの ref_version 伝搬 |
| 変更規模 | 小（数十行・定型追加） | 大（構造改変・広域リファクタ） |
| パターンの新規性 | 既存パターン踏襲（テンプレ流し込み・既存に倣う） | 前例なし・新規構造の創出・設計判断を含む |
| 触る対象の性質 | プローズ/資産テキスト・ドキュメント | 権限ゲート/フック/セキュリティ境界・doc-system グラフ構造・型 |
| 可逆性 | 容易に差し戻せる | 不可逆・広範囲に波及 |
| 仕様の明確さ | 受け入れ基準が一意 | 曖昧・利害 trade-off・解釈の余地 |

- 迷ったら **opus 側に倒す**（bloom-model-tier のタイブレーク＝effort は品質の代理変数にすぎない・安全側）。選定根拠を1行残す（信号→model）。
- **レートリミット／セッション上限は選定根拠にしない**（CLAUDE.md「レートリミット由来の品質降格の禁止」・Issue #321）。
  サブエージェントが上限で停止しても、上表の信号は変わらない。停止＝主文脈が動いている＝枠は回復している。
  同じ model・effort・委譲構成でそのまま再投入する（降格・effort 低下・主文脈代行はしない）。
  **上限停止後の再投入は②-cの「再レビュー」ではなく初回レビューの継続**であり、次項の
  「再レビューは常に Sonnet」は適用しない（対象は同じ model・上表で選定した model のまま再投入する）。
- **再レビューは表に依らず常に Sonnet**（Issue #120 ⑤）。是正の担当 model は**レビューアの降格判断に従う**（主文脈が決めない・Issue #120 ④）。

## 共通指示の配り方（dispatch テンプレをリーンに保つ）
`issue-implementer`/`pr-reviewer` の**恒常的な共通契約**（決定点で前提/背景/メリデメ＋選択肢＋推奨を報告に添える・PR コメントは AI 明記＋具体・
曖昧は STOP 報告・スコープ外は起票提案）は、**各エージェントの system prompt（`.claude/agents/*.md`）に常設**する（読者が見る場所・版管理・毎回自動適用）。
- **dispatch prompt には毎回タスク固有情報だけ**を書く。バッチ共通の補足がある場合のみ、CLAUDE.md の規約どおり
  `tmp/<sprint>/issue-pipeline-common.md` に書き出して各 dispatch から参照させる（同一指示をコンテキストに展開しない）。
- **SubagentStart フックは採らない（設計判断）**：恒常契約の配布に `SubagentStart` を使わず、各
  エージェントの `.md` に常設する（却下理由3点＝`.claude/rationale/issue-pipeline.md`）。

## エージェント定義のスナップショットが作業ツリーの現在値に追随するとは限らない制約（既知の制約・回避策・Issue #360）

**dispatch される subagent のシステムプロンプト（`.claude/agents/*.md` の内容）は、実際に適用される
契約が作業ツリー上の現在のファイル内容と食い違うことがある。** 作業ツリー上のエージェント定義ファイルを
`Edit`/`Write` により変更し、あるいは `git switch` で作業ツリーの内容を切り替えても、dispatch する
subagent が実際に従う契約がその変更を直ちに反映するとは限らない——**いつ・どの単位でスナップショットが
更新されるか（セッション開始時点で1回だけロードされ以後一切再ロードされないのか、それとも別の単位・
条件で再ロードされうるのか）は未解明**であり、本節はメカニズムを断定しない。

> **本節は Claude Code の実測に基づく**（Codex CLI・Copilot が同種の挙動を持つかは未検証）。
> 実測①②のログ・欠陥の所在・帰結・機構側対処のスコープ外扱いは `.claude/rationale/issue-pipeline.md`。

- **回避策**：呼び出し元は、**dispatch した subagent が実際に何を根拠に判断したか（STOP 理由・受理/
  拒否したパス形状等）を都度観察し**、そこから逆算してどちらの契約が適用されたかを判定した上で、
  以後の入力をその場で適用されている契約に合わせる。「作業ツリーの現在の内容だから新契約のはず」
  「前回旧契約だったから今回も旧契約のはず」のどちらも前提にせず、**回ごとに実測して確認する**。
- **新契約の実地検証にセッション再起動が必須とは限らない**：再起動すれば新契約が確実にロードされる
  保証も、再起動しなければ新契約が確実に適用されない保証も、現時点の実測からは言えない——**新契約が
  実際に機能するかは、再起動の有無によらず、dispatch のたびに実測で確認する**のが唯一確実な方法である。

## 重い作業は agy を積極利用（Issue #120 ⑦・fail-close）
横断影響調査・参照/孤児調査・スクラッチ計算・並列サブクエリなどの**重い調査**は `agy-delegate` へ回す。
- `agy-delegate` は**移譲前に必ず疎通チェック**（`antigravity_status`）し、NG（クラウド/ヘッドレス等）なら**移譲せず主文脈が直接遂行にフォールバック**（fail-close）。
- **正本への書き込み・確定著作・無検証コード採用は移譲しない**（agy 産は素案/レポート＝入力にすぎない・`agy-delegate.md` のガバナンス境界）。

## 点検観点（done）
- ① 推奨順を依存グラフ＋根拠付きで提示し、`AskUserQuestion` でオーナー承認を得た（独断で処理を始めていない）。
- 各 Issue が **implement→PR→review→merge→close** を1件ずつ完結（前 Issue の close 確認後に次へ）。
- 実装 model は bloom-model-tier、初回レビュー model はリスク信号表で選定し**根拠を1行残した**。是正降格は**レビューアが決めた**。**再レビューは Sonnet**。
- レビュー指摘・処置結果が **PR レビューコメント**に AI 明記＋具体で残っている（Issue #120 ⑥）。
- 是正ループの続行/停止を**「実害の定義とエスカレーション条件」節で判定した**（ラウンド上限ではなく実害の有無・条件 (a)〜(d)）。
- スコープ拡張は**別 Issue に逃がした**（現 PR を肥大化させていない・⑧）。
- 先送りは**オーナー許可を取った**（AI 独断で「対応不要/繰り越し」していない・⑨）。
- 主文脈は実装/レビューを自分でやらず、タスク管理・進捗報告・意思決定に専念した（③）。

## 成果物
- 承認済み処置順 ＋ 各 Issue の PR（merge/close 済み）＋ PR レビューコメント（AI 明記）＋ 起票したサブ Issue/FND/Q（あれば）＋ 進捗ログ。
