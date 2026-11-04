# Issue反映・実装依頼に直結する引継ぎ仕様

作成日 2026-11-03 / ChatGPT (AI)。**本書はIssueを作成・更新していない。全て反映先の原案。** 反映後に「Issue #N を処置して」と指示すれば、現状調査→既定のIssue Pipeline→実装PRまでを開始できるように、scope/成果物/試験/AC/依存/禁止事項を示す。

**設計正本（この分析PRの範囲内）**：
- [S1–S3具体設計](DESIGN-S1-S3.md)
- [S4–S6具体設計](DESIGN-S4-S6.md)
- [L1–L3具体設計](DESIGN-L1-L3.md)
- [L4–L6具体設計](DESIGN-L4-L6.md)
- [元の反復ミス分析](README.md)

## 1. 反映前に遵守するルール

1. **レポートのDraft PRをmainへ反映するまでは**、各Issue本文がこの文書をmain上の既存仕様だと参照するのは不可。反映するときは、mainに到達したコミットとパス、またはその時点の不変コミットSHAを参照する。
2. Issue起票・既存IssueのAC変更・親子/blocked-by変更・優先順位の確定は、オーナーが対象と文面を確認したあとに行う。**この段階では一切行わない**。
3. 一Issue＝独立に検証できる一成果物。tracking Issue（#691/#551等）そのものに長い実装と完了判定を背負わせない。分割時は既存Issueの担当を勝手に削除しない。
4. 依頼「Issue Nを処置して」は実装と独立レビュー・PR作成までを含むが、ownerの判断・PR merge・Issue closeは含まない（既存issue-pipelineの承認境界）。
5. Issueの本文には**実装で固定する契約、変更対象、試験、AC、前提となる承認済み決定**を入れる。候補や検討事項だけに留めない。調査対象のHEADが変わったら再確認し、矛盾は新仕様を捏造せずSTOP。
6. 不具合やレビューfindingの実害を追跡するときはKarte正本を使う。運用改善の成果を別の集計台帳へ二重登録しない。
7. 当レポートの工数・効果評価は**未実測の推定**。優先順位・納期・性能閾値を勝手にowner承認済みと扱わない。

## 2. 12対策→Issueへの推奨マッピング

| 対策 | 実装の最小独立成果 | 主たる反映先候補 | 新規起票 | 既存との境界 |
|---|---|---|---|---|
| S1 | 影響面表をIR/CP/plan reviewへ結線 | NEW-SURFACE（S2と同じ成果単位） | 要 | #370は計測専任、#371はCLOSED |
| S2 | 修正前の同一原因探索・OOS引継ぎ | NEW-SURFACE（S1と共有） | 要 | pr-reviewerの横断規定は実装済み |
| S3 | 両PF hookのALLOW/DENY対照試験 | NEW-GATE-CASES | 要 | 現行安全ゲート本体を不用意に再設計しない |
| S4 | #720/#728のテスト変異検証＋汎用規定 | #720・#728、必要ならNEW-MUTATION-RULE | 条件付 | 個別不具合修正と一般規定を分離 |
| S5 | reviewer証拠4点のhead束縛 | #375／#409、既存仕様で充足なら追加不要 | 原則不要 | #530 CLOSEDを再実装しない |
| S6 | CPにlive要否条件とケース様式を接続 | NEW-LIVE-CRITERIA、実測は#652 | 要（汎用ルールのみ） | #652は#371固有の初回実測 |
| L1 | AgentRun依存DAGとphase/receiptのclose検証 | #409、traceは#703 | 原則不要 | #371既存結線を再利用 |
| L2 | 安全なworktree回復・一般fault契約・結果整合 | #559・#699・#679、AgentRunは#409 | 原則不要 | 各Issueの責務を統合しない |
| L3 | 安全重要verbの構造化認可と対照試験 | NEW-SAFE-OPS | 要 | #706のintegrate-baseの過剰制限撤廃を維持 |
| L4 | CI trigger/対象/head/実機証拠の対応 | NEW-CI-EVIDENCE、type/schemaは#701、traceは#703 | 条件付 | #467/#530 CLOSED、#652はlive |
| L5 | reviewer→triage→Karte→STOP/解除の閉ループ | #691下の独立子Issue群、#513/#375/#683/#523/#614/#409 | #691の子として複数 | #691自体は非実装tracking |
| L6 | #370の4分類と効果比較の補助レポート | NEW-DEFECT-COHORT（#370関連） | 要 | #488のv1計測/基線を変えない |

NEW-名称は**仮ID**。GitHub Issueはまだ存在しない。

## 3. 新規Issueに転記できる「成果契約」

下の各項目は、**Issue作成本文のScope/Out of scope/ACの核**。反映時には対応設計書のリンクと対象コミットを必ず冒頭に付ける。実装時の詳細手順とテストセットは各DESIGN文書で凍結した案を参照し、ここで再定義しない。

### NEW-SURFACE：Issue工程の影響面と同一根本原因探索を繋ぐ（S1+S2）

**成果**：IR.affected_surfacesおよびCP.interfaces/oosで、role/PF/入口/状態/正本/CLI/CI/liveの影響面と、同じroot causeの同型候補が確認・引継ぎされる。対象は既存Issue Pipelineだけ、一般のAIチャット・doc_system新形式への全適用は対象外。

**変更対象**：.ai/agents/issue-investigator.md、change-planner.md、plan-reviewer.md、issue-implementer.md、issue-fixer.md。必要時にissue-pipelineの既存節へ最小参照。issue_envelope/schemaの変更はしない。

**検査**：S1-T1～T5、S2-T1～T5。IRの省略/存在、unknown、OOS、別PF、同型でない一致を含む。

**AC**：AC-S1全5件とAC-S2全5件。共通の文面を増やす代わりに既存TEXTへ集約、未決判断はオーナーへ報告。独立レビューが報告した同型findingを勝手に解消扱いしない。

**依存**：既存工程分離#371（CLOSED）がmainにあること。既存主文脈からの実dispatchを対象にlive保証までは要求しない。

### NEW-GATE-CASES：hookのALLOW/DENY対照契約テストを増強（S3）

**成果**：Claude/Codexの正規hook payloadを入力する共通fixture・PF別判定adapter・正常/禁止それぞれの回帰テスト。破壊操作は実行しない。別のポリシーエンジンは新設しない。

**変更対象**：tests/fixtures/command-gate-cases.json（候補）、tests/unit/test_agent_command_gate.py、test_codex_agent_command_gate.py、test_phase_role_commands.py。差分を根拠に必要ならagent_command_gate/の既存関数を改修。

**検査**：S3の対照マトリクス、各PF正常/禁止5以上、malformed/unknown、重複した意味のPF別結果。

**AC**：AC-S3全5件。owner手動merge、D0、readonly role、非強制pushの従来可用性を損なわない。

### NEW-MUTATION-RULE：重要分岐の変異Redを検証設計に織り込む（S4の一般規定・条件付）

**成果**：重要なverdict/終了コード/入力ガードのテストは、実装へ代表変異を入れると対象assertが赤になり、元へ復元したことを記録する。#720/#728の個別欠陥修正そのものは含めない。

**変更対象**：.ai/agents/test-writer.mdとpr-reviewer.mdの既存2aレビュー契約（参照追加）、既存test reportの証拠記法。新しいmutation runner、常時CI全域走査は作らない。

**検査**：S4-T4～T6を含む一般プロトコル。原本・変異中・復元後の3状態のSHAを取得し、**mutated≠base、restored=base、未commitのHEAD OID不変**を確認する。#720/#728で実績が揃った場合、**規範更新が不要と判断されたら起票不要**。

**AC**：AC-S4のうち一般規定3点＋既存工程のRed-firstと独立reviewの維持。導入が既存Issueのscopeに収まらなければ分ける。

### NEW-LIVE-CRITERIA：実機検証要否の判定・証拠様式をCPに接続（S6）

**成果**：ChangePlan.operational_verificationに変更面に対するlive要否、ケースID、正規入口、期待値、実行環境/版/OID、判定の書式が入り、実機未実測をpassと誤認しない。

**変更対象**：.ai/agents/change-planner.md、既存検証レシピへの参照のみ。#652のlive実行、PFの権限解除、CI大改造、常設監視は含めない。

**検査**：S6-T1～T6。mock成功、profile pin未到達、正しい拒否、外部API無し、未認可料金を別判定。

**AC**：AC-S6全5件。liveが必要なときは実装から分離された検証Issueを参照でき、実装をlive成功と誤報しない。

### NEW-SAFE-OPS：安全重要verbの実操作先への束縛（L3）

**成果**：高影響操作（AI merge禁止、制限されたgitgateの書込等）のrole/target/OID/owner/scopeを、既存の構造化CLI入口で信頼できる値と照合する。hookを万能shell sandboxと主張しない。

**変更対象**：既存agent_command_gate/、gitgate/の実行前検査、.claude/.codex hook adapter、tests/unitの対照fixture。**#706で過剰制限撤廃済みのintegrate-baseを本案の対象へ自動追加しない**。

**検査**：L3-T1～T8とS3対照ケース。一般read-only経路は従来どおりallow、危険操作の拒否に伴う可用性の低下を計測。

**AC**：AC-L3全6件。追加権限/制限を入れる前に対象verbを固定し、追加禁止が既存owner決定と整合することを確認する。

### NEW-CI-EVIDENCE：CI要否・実起動・HEAD同一性の検証（L4、条件付）

**成果**：変更面に対して必要なworkflowが起動し、event内PR head SHAと、実checkout/tested SHA（`pull_request`なら通常merge SHA）が正しく対応するrunの成功であることを示す。**PR head=A、tested merge SHA=M（M≠A）でも有効**、head=Bへの更新後はA由来runを無効とする。#467/#530で既に機械化済みの機能は再実装しない。

**変更対象**：tests/unit/test_asset_parity_ci_paths.py周辺、既存レビュー証拠、必要な場合だけ小さなCI contract validator。#701型check、#703trace、#652liveは別issue。

**検査**：L4-T1～T8（T4a/T4bを含む）。正例は`pull_request`のevent head=A/merge-tested=Mの成功、負例はhead=B更新後のA由来CI、別PR、別event、証拠欠落。skip・旧HEAD・CIパス漏れ・scan/trigger分離・Pages PR buildも区別。

**AC**：AC-L4全5件。既存テストで全て検出可能なら本Issueを起票せず証拠として報告する。

### NEW-DEFECT-COHORT：#370の4分類と施策効果の別レポート（L6）

**成果**：既存defect_metrics v1を不変に保ちながら、#370の第2分類へ**承認済みdeferred/waivedも含めたmerge前発見済み残置**を計上し、別の`disposition_state`で未承認/未完了の実害を集計する。4分類は発見・残置とmechanism_gapの2軸で保持し、施策前後の観測条件を比較できる補助レポートを作る。

**変更対象**：defect_metrics/classification.py・cohort_analysis.py・tests/unit/test_defect_metrics_cohorts.py（新規候補）、バージョン付き分類annotationの単一保存先。既存定義・基線・72時間集計・通知を変更しない。

**検査**：L6-T1～T10。承認済みdeferred1件と未承認の実害残置1件をともに第2分類 `known_retained_at_merge` へ加算（残置合計2）、内訳 `disposition_state` は `approved_deferred=1` / `undecided=1`、未承認実害は1件だけ。v1レポートとbaselineの互換、分類証拠欠落・API打切り時のunknown/errorも確認。

**AC**：AC-L6全5件。#370の観測/計測の責務に関連付け、#488を再実装しない。

## 4. 既存Issueへ反映する追加仕様（本文上書きはしない）

### S4：#720、#728

すでに各変異の元実装・対象test・検出条件が具体的。新規Issueを切らず、両Issueに「S4の共通変異証拠プロトコルを適用し、変更前Green→代表変異で対象assertの失敗→復元後Green、原本SHA≠変異SHA、原本SHA=復元SHA、未commit HEAD OID不変を記録する」を補足するだけでよい。**対象外の一般規定**が必要ならNEW-MUTATION-RULEに分ける。

### S5：#375と#409

#375へ「review artifactにPR head、diff完全読了・未読範囲、CIのrun ID/attempt・event PR番号/head SHA・tested SHA（merge-refの場合はM）・Karte round/findingを記録し、head更新後の旧runを拒否」を追加候補とする。**CIのtested MとPR head Aは同一SHAでなくてよい**。#409へは「close時にreview artifactとCIの正規run/head対応を検証し、Karteの**verdict・owner判断・close専用判定**を照合する。**#683の無進捗からの除外はclose免除ではない**（open件数ゼロもescalate集合ゼロも代替不可）」を追加候補とする。既存ACで既に充足していれば**新しいIssueや実装は作らない**。#530 CLOSEDの完全差分取得とSTOPを再設計しない。

### L1：#409、#703

#409のスキーマ、状態遷移、phase依存・expected artifact・close gateへL1の型付DAGとT1〜T14を追記候補とする。**既存ACの「未解消findingゼロ」をopen全件ゼロや無進捗集合ゼロとして実装しない**。Karteの検証済み`status_verdict`・owner/STOP・close専用条件を照合し、`harm:none/deferred`のverified handoffは#683に従って無進捗から除外しても`verdict:no-harm-only`のままなので**owner判断なくclose不可**とする。#691で採用後の正式Advisoryのみ別途承認済みのverdict/close条件に従い、未分類/未承認harm:real・参照不一致・判定不能はclose不可というACへの具体化を提案する。#703へはtrace linkのexists・orphan・例外/履歴の正当性を接続し、同じDAG正本を複製しない。#371の成果物schema/handoffは既存のまま使用。

### L2：#559、#699、#679（#409と関連）

- #559: 観測済み5経路をそのまま保持し、実際のworktree/ledger/gateを使ったfault injectionと次dispatchの成功を追加。活性所有者や未回収成果物を自動削除しない。既知再発是正の主処置先。
- #699: 故障点の列挙、再試行ID/二重実行/部分成功/commit pointの共通設計パターンと代表契約試験。別のworktree回収機構を作らない。
- #679: agy_delegateの「CLI返却と永続結果の一致」を、失敗しうる後処理を最終確定前へ移す推奨方式を候補として比較・owner判断し、決定後の二重故障回帰試験を追加。永続結果を2正本にしない。
- #409: AgentRunとの参照とtimeout/close冪等はここで扱い、worktree所有ledgerへ統合しない。

### L4：#701、#703、#652

#701は現行typechecked-filesの追加/削除/renameとpyright実行対象一致のratchet。#703は成果物→検証証拠の欠落・孤立を検出。#652は正規製品経路のlive証拠。CIのHEAD同一性はPR headとtested merge SHAの文字列一致でなく、run/eventからの対応で判定する。CIのhead取り違え・skipを補う新規成果が本当に不足する場合のみNEW-CI-EVIDENCEとし、#467の修正を再発明しない。

### L5：#691下の子成果と#513のSTOP

#691は明示的に**非実装tracking**。次の独立成果案を子Issueとして扱う（いずれも未作成・仮ID）。

| 仮ID | 一つの成果 | 既存Issueとの責務 |
|---|---|---|
| NEW-TRIAGE-POLICY | owner事前承認された版付き決定論的policyと権限境界 | #691、#523、harm正本#723(CLOSED) |
| NEW-TRIAGE-ARTIFACT | reviewer不変原本→別コンテキストのtriager成果とrun/OID/digest束縛 | #375が原本、#409がrun |
| NEW-ADVISORY-LEDGER | .ai/advisory/ledgerの検証付きCLI、重複/衝突/索引/昇格 | #691。feedback_ledgerと別正本 |
| NEW-KARTE-DISPOSITION | **検証済みfinding原本と処置証拠を共有し、verdict/STOP・escalate無進捗・check診断要否・#409 closeを用途別の派生述語に結線**。#683のhandoffは無進捗のみ除外しverdict維持、#614の診断除外はowner決定まで不変更 | #683＝無進捗と転記検証、#614＝check、#691＝承認済みAdvisoryの効力、#409＝close専用消費 |
| NEW-TRIAGE-PIPELINE | capture→triage→validated ingest→STOP/解除のphase接続 | #513、#409、#523との競合を解消 |
| NEW-TRIAGE-LIVE | 正規PRのreview→triage→処置→Karte→owner判断のlive受入 | #652の手法を再利用、後日別Issue |

**重要**：#513のtool全denyとtriager dispatchの競合の解（L5のtriage_pending）をownerが明示採用するまでNEW-TRIAGE-PIPELINEの権限変更に着手しない。#409 closeは**Karteの検証済みverdict・owner決定・close専用判定**を消費する（L5-T12/T15〜T22）。**#683のhandoff検証済みharm:none/deferredは、無進捗から除外されてもverdict:no-harm-only・owner STOP維持**。正式Advisoryは#691の承認済み契約の範囲だけ別扱いし、#614のcheck診断要否は決定前に変更しない。レビュー原本未取込や未承認実害はclean/close扱いにしない。


### F-733-05：子Issueと既存Issueへ引き継ぐ用途別の契約試験（反映前原案）

- **#683（既存scope/ACは不変更）**：verified `harm:none/deferred` を無進捗3ラウンド計数と`render ★無進捗`からのみ除外する。元の`status:open`と`verdict:no-harm-only`、既存owner STOPを維持。転記hash変更・コメント編集/削除・転記先closed・検証失敗時は計数へ復帰。`check`とverdictの改変は#683のOut of scope。
- **#614（既存owner判断の対象）**：`check`診断必須集合は#683によって自動除外しない。`harm:none/deferred/waived`と主文脈担当fix-hereの診断要否は#614の結論と理由に従って別に実装・検証。
- **NEW-KARTE-DISPOSITION（#691の子Issue候補）**：共通の検証済み入力→用途別の派生述語というAPI/責務を定め、L5-T12/T15〜T22を受入条件に加える。将来の#691承認済みAdvisoryのみ、承認した用途別効果を有効化する。#503の既存一元化や#683の意図的非対称性を壊さない。
- **#409（既存close gate）**：`escalate:no`を`verdict:clean`やclose可能へ読み替えない。`no-harm-only`が残る場合は有効なowner判断なしのcloseを拒否。`status`/`check`/`escalate`と原本・処置証拠が一致することを検証し、**用途ごとの出力結果が異なるだけで不整合としない**。
- **#513**：無進捗false-positiveの抑制はowner STOP解除の根拠にならない。tool全denyの発動理由・解除はオーナーが承認した専用の条件を使い、`escalate:yes/no`へ無条件連動させない。

受入fixtureの中心：`status:open, harm:none, disposition:deferred, verified handoff, rounds>=3` → `verdict:no-harm-only`, `stall_candidates`除外, `check`は#614の現行ルール, owner未決なら`close_eligible=false`。同じ入力でhandoff証拠を無効化→`stall_candidates`へ復帰、verdict/owner STOPは変化なし。**これは実装時のAC候補であり、どの既存Issue本文にもまだ投稿・反映していない。**

### L6：#370の計測・再集計

#370は**事前分類供給と導入後計測**が成果で、独自のゲート実装は対象外。merge前発見済み残置は承認済みも含めた事実分類として数え、未承認/未完了の実害を別の`disposition_state`集計へ分ける。新しい分類器/補助レポートの実装成果はNEW-DEFECT-COHORTとして切り出し、#370から参照。既存defect_metricsのv1報告と#489の運用実測は再実装しない。

## 5. 採用前にownerが一括決定すべき6点（推奨案を記す）

| 判断ID | 未確定点 | 推奨確定案 | 不採用時の影響 |
|---|---|---|---|
| DEC-1 | #513停止と#691 triageの順序 | 不変原本capture→trusted triage→検証済みKarte ingest→未決実害ならhard stop。triage_pending中は通常の後続phase不可。必要な限定dispatchだけowner承認の例外を定義 | 先に全denyするとtriagerを起動できずdeadlock。例外自体にも独立検証要 |
| DEC-2 | #513 stop解除手段 | owner回答に紐づくtrusted hook経路が実証できた場合のみ機械記録。実証不能時は**owner制御の外部解除CLI**を用意し、AIのBash/Editによる解除を禁止 | hostの本人性/回答構造が得られない時は自動解除不可 |
| DEC-3 | #559の自動解放範囲 | 信頼済み終端/回収/未変更が確認できるケースのみ自動。活性不明は削除せず停止と証拠報告 | すべての未知残留を自動解放する方式は成果物消失リスクが高い |
| DEC-4 | #679の最終結果整合 | 失敗し得る後処理をcommit pointの前に集め、1つの権威ある結果をatomic確定。再読不能時はindeterminate | 異なるファイルの原子的同時更新は簡単には保証できない |
| DEC-5 | L3適用の広さ | 高影響・構造化verbに限定。#706のintegrate-base過剰制限撤廃を維持。静的hookをOS sandboxとは呼ばない | 全コマンドに追加denyすると既存の正常操作に大きな誤拒否 |
| DEC-6 | #370の施策評価と新merge gate | 既存v1指標を維持し補助集計で観測。#370既決どおり実測の残件が出るまで新merge hookなし | 再発クラスの確実性を上げても因果・観測窓の問題は残る |

これらは**おすすめの採用判断**であり、「オーナー決定済み」とは記載しない。採用された場合は原決定記録へ正しく捕捉してから対応するIssueへ反映する。

## 6. 依存グラフ（実装着手順の原案）

~~~text
S1+S2 NEW-SURFACE ───────────────┐
                                 ├── 代表PRへの導入結果測定 ── L6の効果分析
S3 NEW-GATE-CASES ─── L3 SAFE-OPS┤
S4 #720/#728 ── (一般化必要時 NEW-MUTATION-RULE)
S5 #375 review artifact ─┐
                          ├── L1 #409 close ──┐
S6 NEW-LIVE-CRITERIA ── #652 actual live ─────┘
L2 #559 (個別回復) ── #699 (横展開pattern) ── #409 (run参照)
L2 #679 (agyのcommit point設計: owner判断が先)
L4 #701 clean type / #703 trace ── (未充足なら NEW-CI-EVIDENCE)
L5 #375 review原本 ── NEW-TRIAGE-POLICY / ARTIFACT
                      ── NEW-ADVISORY-LEDGER
                      ── NEW-KARTE-DISPOSITION (依存 #683/#614)
                      ── NEW-TRIAGE-PIPELINE (依存 #513/#409/#523, owner DEC-1/2)
                      ── NEW-TRIAGE-LIVE
L6 NEW-DEFECT-COHORT ── #370測定・owner評価
~~~

**前提**：これは論理依存であり、着手順の承認ではない。実際は各Issue Pipelineの①でOPEN Issue・PR・依存関係と競合を再点検しowner承認を受ける。長期の#409/#691等を優先して短期の正常運用を止める必要はない。

## 7. 後続の「Issue #Nを処置して」用の作業指示テンプレート

文面例（まだ投稿しない）:

> 本Issueは実装対象です。対象版の main に保存された「audit/2026-11-03-pr-issue-mistake-patterns/」の対応DESIGN節とAC（SxまたはLx）を設計入力とする。今回のScopeは本文の対象成果に限定。既存のrole、Issue Pipeline、owner決定、関連Issueの責務、CLOSED機能を維持する。調査・VD/CP・TestDesign Red・独立レビュー・実装・CI・必要なlive検証先への引継ぎを正規手順で実施し、変更した正本と対応mirror、負例、既存機構との差分、未実測をPRへ記録。未決判断/実装不能は判断材料・選択肢・推奨と証拠を示してSTOPし、勝手にAC/Scopeを拡張しない。AIはmergeしない。

## 8. 「Issue反映前」に必ず確認すること

- [ ] #733がmainにmergeされたか。未mergeならbranch/ref付きの不変資料へリンクする。
- [ ] 各IssueのOPEN/CLOSED、本文の最新AC、既存設計の更新、同時進行PRを再取得する。
- [ ] 既存issueと新規issueで同じ成果物を二重に担当しない。
- [ ] ownerの既決方針とDEC-1～6の未決/提案の区別がIssue本文でも維持される。
- [ ] Issue単位の成果が、作業の完了時に客観的な証拠で確認できる。
- [ ] #691はtrackingに留め、子Issueへ独立の実装/試験/運用検証を配置する。
- [ ] issue-pipelineはmainの完全一致bindingを尊重し、Draft PRの未mergeプロフィールを正規live検証成功として扱わない。
- [ ] 本段階のレポート作成でIssueの作成・更新・コメント・relation/AC変更を一切実行していない。
