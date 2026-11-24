# governance-directives：同期判断の履歴と注入方式の根拠

> `.claude/hooks/governance-directives.md` の非実行コメントから移設。現行の実効指示・同期hashはフック内の最新本文を参照。

## 過去の正本同期・差分監査ログ（原文保存）

<!--
  Issue #375（2026-10-31）: `.claude/rules/05-skills-agents.md` の戻り値のハンドオフ規約で `pr-reviewer`
  （Claude Code）を write 権限なし側から外し、項13へ `karte ingest-reviewer` と主文脈専用 verb を追記した。
  既存の中核規範（1〜12）は意味を保持。marker を再計算した。

  PR #712（2026-11-01）: `.claude/rules/05-skills-agents.md` の issue-fixer の診断前編集禁止に、PR base 取り込みの衝突解消の例外（`.ai/agents/issue-fixer.md`「取り込みとカルテ手順の順序」）への参照を括弧書きで足した。項13に同じ例外を括弧書きで反映し、marker を同期した。main の取り込み時の衝突（冒頭コメント欄）は両側の記録を残して解消し、marker を統合後の値へ更新した。

  `.ai/guidance/common.md` への項追加（2026-10-25・オーナー）: 「作業分離・判断境界」に、ドキュメントと既存コードが食い違うときはコードに従い食い違いを最後の返答で挙げる旨を追加。これを項14として配送する。

  Issue #685（2026-10-31・F-685-51）: `.claude/rules/02-decision-process.md` の起票先判定表
  「実行環境の面倒を見るフック」へ `issue-start-gate.sh`/`phase-tool-gate.sh`（列挙済みの
  `issue_start` の gate を起動する薄い起動口）を追記しただけ。下記9は「実行環境フック」を
  総称で配送しており区分は変わらないため、中核規範（1〜13）には掛からない。本文は変更せず
  marker のみ現在値へ更新した（「見た上で不要と判断した」ことの記録）。

  PR #688（2026-10-31）: `.claude/rules/05-skills-agents.md` の karte 台帳 deny の記述から Write 専用エントリへの言及を外しただけ。中核規範（1〜13）には掛からず、本文は変更せず marker のみ同期した。

  Issue #371（2026-10-16）: 正本集合を前版と比較し、変更は rules/05-skills-agents.md の
  Issue工程分離・role権限・非対話契約。既存の中核規範1〜12は意味を保持し、工程の著作・審査・
  承認境界を新しい項13へ同期した。fixer専用karteとadviserの非承認性も配送する。
  正本集合はpath/NUL/bytes/NUL規約で再計算しmarkerへ反映した。

  Issue #632（2026-10-13）: `.claude/rules/05-skills-agents.md` へ Claude Code 専用サブエージェント `gh-create-issue` と handoff Read 規定の例外を追記しただけ。中核規範（1〜12）には掛からず、本文は変更せず marker のみ同期した。

  Issue #606 r4: 05-skills-agents の agy 運用状態を agent 正本参照へ統一した。項1〜12と照合し中核契約の変更なし。本文を維持しmarkerだけ同期。

  PR #638 のレビュー是正（2026-10-14）: `CLAUDE.md` 冒頭の subagent 注入対策を、起動可能な17エージェント中
  16エージェントに規定があり、`reconciliation` は規定なしの例外であると明記した。`.claude/hooks/README.md`
  の対応表に記録済みの実態への整合であり、配送本文（中核規範1〜12）には変更なし。marker のみ更新した。

  Issue #589（2026-10-14）: `CLAUDE.md` 冒頭の注入規範の説明と `.claude/rules/05-skills-agents.md`
  「戻り値のハンドオフ規約」の1文が、subagent 側の対策の節名を「各 agent.md 末尾の『注入ブロックへの
  優先規定』」とだけ書いていたのを、「『注入ブロックへの優先規定』節、または同等の規定を持つ節」へ
  直した（エージェント定義側ではなく記述側を実態に合わせる方向。エージェントごとの節名の対応と
  起動できるエージェント数は `.claude/hooks/README.md`「規約注入フック」の表）。**記述の訂正であって
  中核規範（1〜12）には掛からない**。本文は変更せず marker のみ現在値へ更新した
  （「見た上で不要と判断した」ことの記録＝`.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #538 PR-B（2026-10-13）: `.claude/rules/02-decision-process.md` の起票先判定表へ汎用開発
  ハーネス `codex_worktree_exec`（Claude の implementer/fixer が自分の linked worktree で Codex に
  編集とテスト実行だけを行わせる `codex exec -C` の薄いラッパー）の1項を追記しただけ。判定表の
  列挙そのものの保守であって、中核規範（1〜12）には掛からない。本文は変更せず marker のみ現在値へ
  更新した（「見た上で不要と判断した」ことの記録＝`.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #605（2026-10-11・是正ラウンド1 2026-10-12）: `.claude/rules/05-skills-agents.md` のスキル一覧へ共有リファレンス
  `silent-failure-diagnosis` の1行を、`.claude/rules/02-decision-process.md` の起票先判定表
  「外部委譲・モデル選定・横展・Issue 起票の補助」へ同名を追記しただけ。是正ラウンド1では
  同じ一覧行の接続状態（現時点でプリロードする資産は無い）を直しただけ。是正ラウンド2では
  同一覧の `/codex-review` 行の cyber フィルタ対処の要約を、flag 後の再提出禁止と自 thread_id の
  rollout 1ファイルに限る回収へ直しただけ。下記9の
  「`agy-delegate`等の外部委譲補助」に含まれ、中核規範（1〜12）には掛からない。
  本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」ことの記録＝
  `.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #585（2026-10-08・是正ラウンド1 2026-10-09）: 項12の正本（オーナーへの報告はチャットが正本・
  報告タイミング・AskUserQuestion の使用）を `.claude/rules/02-decision-process.md` から主文脈専用の
  `.claude/main-context/01-owner-communication.md` へ移した。全文は orchestrator-context.sh
  （SessionStart）が注入し、項12は毎ターン用の要約の写しとした。main-context は正本集合へ加えた。
  あわせて注入本文（項1〜12）から Issue 番号・日付の出典を外した。経緯と設計判断は
  `.ai/rationale/main-context-injection.md`（是正ラウンド2 2026-10-09: 実体を
  `.claude/rationale/` から `.ai/rationale/` へ移した）。是正ラウンド3（2026-10-09・F-585-17）:
  `.claude/rules/01-principles.md` 区分1 と項11 の移設先を配置契約（実体＝`.ai/rationale/`、
  `.claude/rationale/` は案内のみ）に揃えた。是正ラウンド4（2026-10-09・F-585-18）: main 取り込みで
  入った正本の変更（02 の `jev_hooks` 行から Issue/PR 番号を除去、05 の merge をオーナー手動へ移し
  `doc-system-config-operator` を write-role へ追加）を項1〜12 と突き合わせた。いずれも項9・項12 の
  記述と整合し本文は変更せず、marker のみ取り込み後の正本集合の値へ更新した。是正ラウンド6
  （2026-10-09・F-585-19）: 区分1 と項11 の移設先の括弧書きを「`.claude/rationale/` には実体を
  置かない」へ絞り、案内ファイルの設置を必須と読めないようにして marker を再計算した。

  2026-10-09: `.claude/rules/05-skills-agents.md` に `doc-system-config-operator` を write-role として追加し、
  共通本文にハンドオフ契約を定義した。中核規範の変更ではないため配送本文は変更せず、marker を同期した。

  Issue #535 是正ラウンド4（2026-09-28・F-535-15）: `.claude/rules/05-skills-agents.md`
  「ctx_* ツールの付与方針」の検索系ツール例外注記から、正当化理由（「ゲート側の手当てを
  要さないため」「実行系＝ctx_execute/ctx_batch_executeの話であり検索系はゲートの統制層を
  経由しないため」）を削除し、条件（検索系ツールへの付与先追加は本規定の対象外である事実）
  だけを本文に残した。理由は `.ai/rationale/issue-fixer.md`「検索系ツールへの付与先追加が
  ゲート側の手当てを要さない理由」へ移設した（本文＝行動を決める区分2、理由＝区分1の
  線引きを、直前ラウンドで新設した例外注記自体に対しても徹底する是正）。上記の中核規範
  （1〜12＝独断禁止・起票義務・正本の所在・品質降格禁止・実行前報告等）には掛からない。
  本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」ことの記録＝
  `.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #535 是正ラウンド2（2026-09-27・F-535-08/F-535-13）: `.claude/rules/05-skills-agents.md`
  「ctx_* ツールの付与方針」を2点是正した。①検索系付与先列挙から「（GATED_ROLES では Grep/Glob が
  実効配布されないため。経緯は … を参照）」という付与理由の括弧書きを削除し、ロール名の列挙と
  rationale への参照リンクだけを残した（理由を本文に混入させず rationale 側だけに置く方針の是正）。
  ②「付与先ロールを増やすときは先にゲート側の統制を手当てし、付与は別 PR にする」という規定に、
  `ctx_search`/`ctx_index` のようなゲート対象外の検索系ツールへの付与先追加はこの規定の対象外である
  旨の一文を追記した（実行系＝`ctx_execute`/`ctx_batch_execute` の話であり検索系はゲートの統制層を
  経由しないため）。上記の中核規範（1〜12＝独断禁止・起票義務・正本の所在・品質降格禁止・実行前報告等）
  には掛からない。本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」ことの
  記録＝`.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #535（2026-09-27）: `.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」の
  検索系（`ctx_search`/`ctx_index`）付与先の列挙へ `issue-fixer`/`issue-implementer` を
  追加しただけ（GATED_ROLES では `Grep`/`Glob` が実効配布されないため、両ロールの `tools:`
  から外し ctx_search/ctx_index を付与する是正に伴う付与先表の保守）。上記の中核規範
  （1〜12＝独断禁止・起票義務・正本の所在・品質降格禁止・実行前報告等）には掛からない。
  本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」ことの記録＝
  `.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #531 是正ラウンド4（2026-09-20・F-531-08/F-531-09）:
  `.claude/rules/05-skills-agents.md` の `/issue-pipeline` 説明から
  「主文脈は処置順の triage・進捗管理・オーナーとの意思決定に専念し」を外し、
  「主文脈は処置順の原案作成とオーナー判断の取り次ぎ・記録、進捗管理を担い
  （決めるのはオーナーであって主文脈ではない）」へ書き換えた（同一クラスの表現を
  `.ai/skills/issue-pipeline/SKILL.md` の導入文・done、Claude/Copilot wrapper の
  description でも同時に掃引）。**スキル一覧の1行の役割記述**であって、上記の中核規範
  （1〜12＝独断禁止・起票義務・正本の所在・品質降格禁止・実行前報告等）には掛からない
  ——中核規範 3（「対応不要」を AI が独断で書かない）と 12（オーナーへの報告）は
  もともと決定主体をオーナーとして書いており、本是正で含意は変わらない。
  本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」ことの記録＝
  `.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #522 是正ラウンド2（2026-09-20・F-522-04/F-522-10/F-522-11）:
  `feedback_ledger/README.md`「既知の限界」・`karte/model.py`「改ざん防止の機械的裏付けと
  既知の限界」・`.claude/rules/05-skills-agents.md`「戻り値のハンドオフ規約」の3箇所を、
  主文脈が実測した拒否メッセージ（メインチェックアウトでの `permissions.deny` 発火、隔離
  worktree での worktree isolation 発火）に沿って書き換えた。台帳保護が二層
  （非隔離には `permissions.deny`・隔離ロールには worktree isolation）で成立していることの
  説明を追加しただけで、上記の中核規範（1〜12＝独断禁止・起票義務・正本の所在・品質降格禁止・
  実行前報告等）には掛からない。本文は変更せず marker のみ現在値へ更新した
  （「見た上で不要と判断した」ことの記録＝`.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #309（2026-08-19）: `.claude/rules/05-skills-agents.md` の変更は
  `dsv2 clean-tmp` の保護名リストへ `_worktree`（worktree 所有台帳の置き場）を
  足しただけで、上記の中核規範（1〜11）には掛からない。本文は変更せず marker のみ
  現在値へ更新した（「見た上で不要と判断した」ことの記録＝`.claude/hooks/README.md`
  「追従したあとにやること」）。

  Issue #354 PR-4（2026-08-19）: 同じく `.claude/rules/05-skills-agents.md` の変更。
  ①「戻り値のハンドオフ規約」へ「入力として渡すのは呼び出し先が新規に書く成果物の
  パスだけ。呼び出し元が既に所有している共有台帳（カルテ等）はパスを渡さず識別子だけを
  渡す」という1項を追加、②`issue-fixer` の説明から「権限は implementer と同一」を外し
  `adopt-branch` とカルテ入力の差を明記。**どちらも `/issue-pipeline` のファンアウト
  設計の細目**で、上記の中核規範（1〜11＝独断禁止・起票義務・正本の所在・品質降格禁止等）
  には掛からない。本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」
  ことの記録）。

  Issue #379（2026-08-20）: `.claude/rules/02-decision-process.md` に
  「オーナーへの報告はチャットが正本」節を追加したことに伴い、
  中核規範 12 を追加して marker を現在値へ更新した。

  Issue #484（2026-09-06）: セッション記憶にしか無かった作業規則5件を正本へ移設した。
  ①`.ai/guidance/common.md` へ3項（節番号を引くときのファイルパス併記／merge・push 等
  取り消しにくい操作の実行前報告／版付き文書の bump 規律＝見送らない・1 PR で複数回上げない）、
  ②`.ai/skills/issue-pipeline/SKILL.md` ②-d へ merge commit 方式（`--squash` 不使用）の明記、
  ③`.claude/rules/02-decision-process.md`「オーナーへの報告はチャットが正本」へ報告タイミング
  （実行前）の1項、④`.claude/rules/03-operational.md` へ新節「セッション記憶と正本の使い分け」
  （置き場の判定規則・迷ったらリポジトリ側へ倒す）を追加。**このうち③は中核規範 12 に掛かる**
  （形式＝チャットが正本、に加えてタイミング＝実行前を要求する）ため、中核規範 12 に
  タイミング要素を1文追記した上で marker を現在値へ更新した。①②④は中核規範（1〜12）の
  射程外と判断し本文へは反映していない（「見た上で不要と判断した」ことの記録）。

  Issue #522（2026-09-19）: `.claude/rules/02-decision-process.md` の
  「起票先はプロジェクト区分で決める」判定表へ、汎用開発ハーネス2件
  （`feedback_ledger`＝オーナー判断フィードバック台帳の CLI と機械 lint、
  `ai_layout`＝`.ai/` 直下の非活性ディレクトリ列挙の共通土台）を追記しただけ。
  **判定表の列挙そのものの保守**であって、上記の中核規範（1〜12＝独断禁止・起票義務・
  正本の所在・品質降格禁止・実行前報告等）には掛からない。本文は変更せず marker のみ
  現在値へ更新した（「見た上で不要と判断した」ことの記録＝`.claude/hooks/README.md`
  「追従したあとにやること」）。

  Issue #522 是正ラウンド1（2026-09-20・F-522-03）: `.claude/rules/05-skills-agents.md` の
  「戻り値のハンドオフ規約」にある `dsv2 clean-tmp` 保護名の列挙へ `_feedback`
  （オーナー判断フィードバック台帳の下書き置き場）を追記しただけ。`_karte`・`_worktree` を
  足したとき（Issue #309）と**同型の保守**であり、上記の中核規範（1〜12＝独断禁止・起票義務・
  正本の所在・品質降格禁止・実行前報告等）には掛からない。本文は変更せず marker のみ
  現在値へ更新した（「見た上で不要と判断した」ことの記録）。

  PR #494（2026-09-07）: `.claude/rules/05-skills-agents.md` のスキル一覧へ
  `/branch-hygiene`（マージ済みローカルブランチ ref の棚卸し・削除スキル）の1行を
  追加しただけ。上記の中核規範（1〜12＝独断禁止・起票義務・正本の所在・実行前報告等）
  には掛からない。本文は変更せず marker のみ現在値へ更新した（「見た上で不要と判断した」
  ことの記録＝`.claude/hooks/README.md`「追従したあとにやること」）。

  Issue #492（2026-09-07）: `.claude/rules/02-decision-process.md` の起票先判定表へ
  `blocker_gate`/`pr_merge_gate`/`issue_start`/`branch_source`/`project_status_sync`/
  `guidance_sync`/`defect_metrics`/`time_fixture_lint` を列挙し、汎用ハーネス追加時は
  同一 PR で表も更新する義務を明文化した。これは中核規範 9 の具体例を増やす変更なので、
  下記 9 に同じ代表例と追随義務を追記して marker を現在値へ更新する。
  Issue #495（2026-09-07）: レビューのスコープ外指摘が実害判定・カルテ記録・`karte status`
  の verdict を一度に迂回できた欠陥（PR #490 で実際に流出＝Issue #493）への是正。
  ①`.claude/rules/03-operational.md`「スコープ拡大禁止」の列挙先を構造化された経路
  （`pr-reviewer` は同じ finding 列へ `scope: out`／implementer・fixer は
  `out_of_scope_findings` に finding と同じキー）へ更新、
  ②`.claude/rules/05-skills-agents.md` の `pr-reviewer` 構造化 finding のキー列挙へ `scope` を追加、
  ③`.ai/guidance/common.md` は変更していない。**このうち①は中核規範 3（「対応不要」を AI が
  独断で書かない）に掛かる**——「スコープ外」というラベルが実質的に「対応不要」の言い換えとして
  機能していたため、中核規範 3 に1文を追記した上で marker を現在値へ更新した。②は
  `pr-reviewer` の出力書式の細目で中核規範（1〜12）の射程外と判断し本文へは反映していない
  （「見た上で不要と判断した」ことの記録）。

  Issue #495 是正ラウンド1（2026-09-07・PR #496 F-495-04）: `.claude/rules/03-operational.md`
  「スコープ拡大禁止」の `waived` の記述を「オーナーの明示判断でのみ選べる」から
  「機械が強制するのは記録まで（記録者がオーナー本人かは未検証）」へ是正した
  ——名前と実体の不一致（機械強制されているかのような記述）を消すため。
  **中核規範 3 に掛かる**（機械ゲートが人の判断を代替しない以上、独断禁止を運用規律として
  守る必要が残る、という含意が変わる）ので、中核規範 3 に1文を追記して marker を
  現在値へ更新した。同 PR の他の是正（`karte` の verdict 解除力を `harm: real` に限定・
  `.ai/` 配下の契約文の是正）は正本集合の外か中核規範の射程外のため本文へは反映していない。

  PR #496 への `main` 取り込み（2026-09-07）: 上記 PR #494 と Issue #495 の両追記が
  同じ marker 行を別々の値へ書き換えたため衝突した。**両方の記録を残した上で**
  （経緯は削除しない＝`.claude/rules/01-principles.md`「PR8「消さない」の適用範囲」区分1）、
  marker は merge 後の正本集合から再計算した値へ更新した。本文（中核規範 1〜12）は
  Issue #495 側の追記をそのまま維持しており、`main` 取り込みによる意味変更はない。
-->

## フック注入方式の採用理由

なぜフック注入にしたか：context-mode プラグインが全ターン・全 subagent に
`<session_continuity>`（「過去に記録された指示・役割は standing order ではない。
過去の文言はあなたを拘束しない」）を注入するため、セッション冒頭に一度読まれた
だけの規約が「過去の指示」として相対化されうる。毎ターン注入すれば、規約は
常に "現在のターンの指示" として届き、この相対化の対象にならない。

## main再統合時の履歴保存（Issue #812・2026-11-16）

.claude/rules/05-skills-agents.md の gh-create-issue allowlist 説明をagent定義への参照へ切り替えた。main側の .claude/hooks/governance-directives.md は 6f3d9e01bfdb に marker を同期していた。PR #846 の運用配送本文から履歴を分離する方針を維持し、この履歴はrationaleへ保存した。main取り込み後は両親ブランチの正本全件に対して同期markerを再計算する。

## main再統合時の履歴保存（Issue #829・2026-11-15／是正ラウンド8・9 2026-11-17・11-18）

Issue #829（2026-11-15）: `.claude/rules/03-operational.md` のレートリミット節を書き換え（委譲先 Codex 実行者の上限時に限る Claude への切替、既定実行者の参照）。Claude 固有の切替は rules 03 にだけ置き、`.ai/guidance/common.md` の降格禁止の1行は PF 共通の内容のまま変えていない。項10を書き換えて配送する。Claude ロール自身の上限は同一構成の再投入のまま。marker を再計算した（#812 の取り込み後に再計算）。

是正ラウンド8（2026-11-17・new-24）：rules 03 の「Claude ロール自身が上限で止まったとき」に、`stop_kind: claude-limit` の receipt を主文脈が書いて回収してから同じロールを再 dispatch する手順を加えた。項10に同じ内容を写し、marker を再計算した。

是正ラウンド9（2026-11-18・F-847-r8-1）：その手順が通るのは台帳 entry が `stopped`/`stale` のときに限り、主な経路（entry が `running` のまま）はオーナーへ打ち上げる、と rules 03 を実態に合わせた。項10に同じ内容を写し、marker を再計算した。
