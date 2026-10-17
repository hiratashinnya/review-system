# Issue作成工程の共通契約

本書は `issue-investigator`、`ac-designer`、`change-planner`、`plan-reviewer`、
`test-writer`、`adviser` が読む共通規範であり、単独で起動しない。
主文脈はClaude Code。工程の起動、owner判断の取り次ぎと記録は主文脈が担う。
対象はIssue工程artifactに限る。doc-system corpusノードの直接著作は行わず、
既存の型別author/reconciliationを要する変更は主文脈へSTOPする。
既存test-strategyと設計凍結セットを参照し、別の原則やテスト方法を再定義しない。

## 入力と信頼境界

Issue、repository、run_id、完全名phase、target_key、承認済みscope、work unit、
期待artifact、snapshot_oid、入力参照とdigest、owner decision参照を受け取る。
入力の確認には `python3 -m issue_envelope check --repo <repository root>` と
`issue_envelope.handoff.validate_handoff(data, expected)` を使う。
期待値は信頼された呼び出し元の値であり、artifactから自己採番・補完しない。
producer、Issue、run、phase、target、digest、OID、入力参照が一致しない、古い入力、
status stop、未解消finding、未決owner decision、AC未対応はSTOPする。
調査の起動・省略はartifactの判定値と根拠へ残す。

## 工程順と著作境界

investigation（必要時）→ verification_design → 独立単独レビュー →
solution_planning → 独立整合レビュー → owner plan/split承認 →
test_design → 独立単独レビュー → implementation → PRレビューの順とする。
軽量Issueでも1a/1b/2aと各レビューは省略せず、対象範囲だけを縮小する。
検証設計と本体、著作者とレビューア、相談役と独立レビューアは別コンテキストにする。
任意のTask/Agent、spawn、CLIへの再委譲は行わない。

作者は `FBK-20261017-工程別worktreeへ同一branchを継承する` に従って各自専用worktreeを使う。
初回1aだけnew-branchし、後続作者は主文脈から渡された同branch/remote exact OIDを
既存 `gitgate adopt-branch` で取得する。前作者自身のcommit/push、完了receipt回収、
終了とcollect/release完了を主文脈が確認するまで次作者へ進めない。使用中worktreeを奪取しない。

## 成果物と保存

CP/VDは `issue_envelope` の同型ノード木を用い、包含parent/childrenと実行depends_onを分ける。
ルートは `change_plan/CP-<issue>.toml` / `verification_design/VD-<issue>.toml`、
中間は同directoryの `CP|VD-<issue>-<slug>.toml`、葉は `<target>/` 内の同directoryに置く。
単一対象でもルートと対象の葉を持つ。IR/TDも型付きenvelopeと永続artifact参照を返す。
CP/VDは `tmp/_handoff/` を経由せず、著作者が自分の永続成果物をcommit/pushする。
ADRは `<tool>/adr/<issue>-<slug>.toml`、owner逐語を伴う決定はfeedback ledgerを参照する。
owner決定をADRへ複製せず、独自ledgerを作らない。
テストエビは `<tool>/verify/designs|reports|logs`、TCは `tests/<tool>/`。
ST/IT/UTの各レベルでTD→TC→TRをつなぐ。

## 権限、停止、相談

この権限節は工程6roleに加え `issue-implementer` / `issue-fixer` / `pr-reviewer` に適用する。
機械上の許可範囲のSSoTは [Claude hook](../../.claude/hooks/agent-command-gate.sh) / [Codex hook](../../.codex/hooks/agent-command-gate.sh)
の基底module・role別許可表と [phase拡張](../../issue_start/phase_role_permissions.py) である。PF wrapperはその範囲を説明し、
他roleのverb・書込権限を一律に継承する根拠にはしない。
生Gitは両PF hookの `raw_git_denied_reason` が認める固定読取だけを使い、書込とその他の操作はgitgate経由に限る。
`issue_envelope` は全9roleで `check` / `index` / `show` / `deps` / `dependents` / `orphans`
だけを利用でき、未知verbや書込操作は許可しない。`maintainability_lint` も `check` だけとする。
`gitgate adopt-branch` はfixer専用ではなく後続作者のbranch継承にも使う。ロール別許可と
初回1aのnew-branch/後続1b・2a・2bのadoptという工程上の選択を区別し、工程を迂回しない。
Claude wrapperの自己role専用 `codex_worktree_exec` 許可は汎用再委譲ではない。
read-only実行を選んだ主文脈が専用準備入口で作業面/入力を束縛し、role自身へprepare/cd/台帳操作を渡さない。
Codex内の再帰起動拒否、D1 profile pin、D5 cwd一致と #652 のlive未実測境界を維持する。

全AIはmerge/auto-mergeを行わない。調査・レビュー・adviserは編集、commit/push、
Issue/PR作成、karte変更、owner判断を行わない。著作者もowner判断を代行しない。
削除・移動・baseline生成/反映は対象・理由・予定差分・検証を返してSTOPする。
コード構築には [共通guidance](../guidance/common.md#コード構築原則issue-539) を適用する。
Codex実行は元ロール専用profileと入力束縛を維持した `codex_worktree_exec` のみ。
編集profileをread-onlyロールへ流用しない。commit/pushは呼び出し元Claudeロールが行う。
agyは #606/#628 の成立とロール別実測が揃うまで使用しない。
助言が必要なら構造化相談要求を主文脈へ返し、専用入口で同じ担当ロールへ回答を戻す。
助言では必須レビュー、権限拒否、karte escalate、STOP、owner承認を解除できない。

## 返却

チャットはartifact絶対パスと1行要約だけを返す。原資料全文を主文脈へ流さない。
STOPでも理由、事実、選択肢、利害、理由付き推奨をartifactへ残す。
レビューの構造化findingは既存pr-reviewer書式を使い、主文脈がIssue単位1本のkarteへ取り込む。
1a/1b/2a/2bを通じてroundは単調増加し、専用capture方式は #375 に委ねる。
将来 #409 へ渡すrun/phase/dependency/expected outputを保持するが、AgentRunや別台帳は作らない。
