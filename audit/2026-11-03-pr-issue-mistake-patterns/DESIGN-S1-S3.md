# 短期対策 S1–S3：具体設計

作成日 2026-11-03 / ChatGPT (AI)。設計原案であり未承認。関連: [調査レポート](README.md)・[S4–S6](DESIGN-S4-S6.md)・[長期設計](DESIGN-L1-L3.md)・[Issue反映計画](ISSUE-HANDOFF-PLAN.md)。

## 0. 共通制約

既存の investigation（必要時）→ verification_design → solution_planning → test_design → implementation、独立レビューを維持し、新フェーズ・新台帳は作らない。変更する規範は .ai/agents/ 等の共通正本から修正し、PF側のwrapperは既存の同期規則に従う。scope override・disposition・処置順・mergeはオーナー専権。発見したOOS実害は既存Karteへ記録し、主文脈で判断を受ける。新たな必須schemaフィールドは短期案では設けない。未確認・非該当・否定結果を区別する。

## S1 変更影響面の閉包：IR→CP→VD→レビューへの受渡し

### 現状と設計の差分

既存 issue_envelope/schema.py の InvestigationReport.affected_surfaces はTEXTであり、ChangePlanはinterfaces/invariants/failure_behavior/oos/operational_verificationを持つ。.ai/agents/issue-investigator.md はaffected_surfacesを要求し、.ai/agents/plan-reviewer.md はevidence→design→AC→verificationを点検する。今回追加するのは**影響面の列挙単位と接続検証**であり、項目の増設ではない。

### 入力・出力

- 入力：Issue/AC・変更前のbase OID・対象予定ファイル・既存caller/callee・role permission・PF wrapper・CI・環境制約。
- 出力正本：IRがある場合は affected_surfaces。IRを省略した場合はCP.interfaces、CP.oosに省略理由と同等の調査結果。CPはIRの記載をただ複製せず、採用設計/変更影響/検証要否を追記。VDは影響する面に対応するST/ITケースを定義する。
- TEXT欄に次の列を持つMarkdown表を用いる（**データ形式の強制パーサは今回作らない**）。
  - surface_id：SURF-001形式で成果物内だけ一意
  - source：変更されるfile::symbol/入口
  - relation：呼出、入力、権限、正本同期、状態遷移、CI、実運用
  - consumer：実際の相手ファイル/role/PF/外部系
  - normal_negative：正常・異常の必要ケース
  - evidence：コード行/既存決定/試験番号
  - status：covered / out_of_scope / not_applicable / unknown
  - followup：CP/VD/既存Issueの参照または判断要求。
- 影響面を確認する既定8軸：①producer→consumer、②role permission、③Claude/Codex/Copilot入口、④branch/worktree/OID、⑤共通正本とmirror、⑥CLI・hook入出力とexit code、⑦CIトリガと検査対象、⑧実行環境/API/version。すべての変更で8つの追加テストを要求するものではない。

### 処理手順

1. investigatorは影響面の推定に用いた参照箇所・反証を記録し、未確認をunknownとする。仕様から一意に決まらない重要箇所が残れば既存STOP契約に従う。
2. 調査省略時はchange-plannerが上記8軸を評価し、CPに含める。調査を強制起動しない。
3. change-plannerはinterfaces/invariants/failure_behavior/oos/operational_verificationへ採用設計と必要な検証ケースを配置。影響範囲外は勝手に修正せず、オーナー判断へ渡す。
4. plan-reviewerは、列が埋まっただけでなく、少なくとも1つ以上の**実際の変更面から見つけたconsumer**が列挙と一致するかを独立検証する。
5. 実装後pr-reviewerは既存契約どおりPR差分と対称箇所を確認し、CPで想定しなかった実変更先をfindingで報告する。

### 変更候補

.ai/agents/issue-investigator.md、change-planner.md、plan-reviewer.mdの既存の対応節、および必要な場合だけ .ai/skills/issue-pipeline/SKILL.md の参照。PR reviewerの既存横断規定は再定義しない。issue_envelope/schema.py/coverage.pyへの変更は**この短期施策では行わない**。

### テストセット

- S1-T1 ガイダンス変更：共通本文→PF入口→CI trigger→生成物に対応する参照を列挙できる。
- S1-T2 worktree解放：worktree ledger→collect/release→次dispatchを対象に含める。
- S1-T3 CLI終了コード：argparseと公開consumerの影響が含まれる。
- S1-T4 investigator省略でもCPが影響面と省略理由を保持。
- S1-T5 実害のあるunknownを「非該当」で処理せず、独立レビューのfinding/STOPに上げる。
- 出力の意味正しさはLLM依存。schema checkがGreenであることは網羅性の機械保証ではない、と報告する。

### AC-S1

- [ ] 既存TEXTに記す表の項目・語彙・8軸が1箇所に定義され、各ロールが参照する。
- [ ] IRあり・省略の両方でCPに影響面と未確認箇所が渡る。
- [ ] S1-T1〜T5の成果を実例として保存し、独立レビューで照合する。
- [ ] 既存issue_envelope check、工程間binding、asset_parity、unit testsが維持される。
- [ ] 新フェーズ/新台帳/オーナー権限移動がない。

## S2 修正前の同型根本原因探索

### 既存規定と追加点

.ai/agents/pr-reviewer.md は既にレビュー時の同型箇所を同ラウンドで横断し、同型は1つのfindingへ集約すると規定済み。今回は同じ規定を追加せず、**修正に着手する前の原因探索と候補の処遇の見える化**を実装する。

### 入力・出力

- 入力：再現条件、原因仮説または確定原因、baseの該当コード、共有契約。
- 正規化した探索キー：何の前提が、どの経路で成立しなかったかを一文で記載。単に「バグ」「誤判定」は無効。
- 候補一覧：candidate_id / file::symbol / same_cause_evidence / disposition_proposal / reason。提案語彙は fix_in_scope・out_of_scope・not_same_cause・unknown。
- 保存先：IR.affected_surfacesの一部、またはIR省略時CP.interfaces/oos。レビュー側は既存findingのlocusを複数記載する。**新規のfinding ledgerは作らない**。
- 同型探索の6視点：①同型parser/例外ガード、②同じ意味の別verb、③同じconsumerの別入口、④PF mirror、⑤状態遷移の逆向き、⑥同じassert形式。無関係な視点には理由を残す。検索一致だけで修正対象にしない。

### 手順

1. investigatorまたはplannerが原因と候補を列挙（採用できない仮説はunknown）。
2. change-plannerが承認スコープ内で修正対象を選び、外の同型はOOS/判断要求として保持。承認外編集はしない。
3. issue-implementer/issue-fixerは修正前に同型候補を読み、計画外修正が必要ならSTOP。
4. pr-reviewerは変更後の差分全体と同型箇所を現行の統合finding規則で点検。
5. 不具合を別Issueとして残すか、当該PRで処置するかはownerが決定する。単なる候補検索では勝手にIssueを切らない。

### 実装候補

.ai/agents/issue-investigator.md、change-planner.md、issue-implementer.md、issue-fixer.mdの手順接続。既存レビューアの同型統合契約は維持する。静的grepツールは必要に応じた手段であって**新規の専用パーサ実装は不要**。

### 回帰事例と検証

- S2-T1 #719：isdigit→intの同型ガードを複数CLIへ適用し、修正対象・対象外の区別を記録。
- S2-T2 #722：RecursionError漏れが別hook入口にないか確認。
- S2-T3 #503：Karte status/check/escalateの対象述語の意味が同じか確認。
- S2-T4 偶然キーワード一致した別仕様を理由付きnot_same_causeに分類。
- S2-T5 scope:outかつharm:realの候補を無視せず、owner決定まで既存Karteへ残す。
- この対策の成果は「すべての同型を必ず見つける」保証でなく、探索・判断漏れの発生経路を狭くすること。

### AC-S2

- [ ] root cause/探索キー/候補/根拠/分類の様式が既存IR/CPで使える。
- [ ] 上記3事例に対する探索結果に、少なくとも1つの同型候補と非同型除外根拠が記録される（候補が実在しない場合は捏造せず探索範囲を記録する）。
- [ ] 未処置の実害はKarteとowner判断へ接続される。
- [ ] pr-reviewerの既存同型統合を重複実装しない。
- [ ] 探索にかかった追加時間・検出同型数がPR単位で計測可能。

## S3 ALLOW/DENYを対にしたコマンドゲート回帰試験

### 対象と境界

Claude: .claude/hooks/agent-command-gate.sh。Codex: .codex/hooks/agent-command-gate.sh。共通ロジック: agent_command_gate/ と既存のrole別コマンド処理。既存テスト: tests/unit/test_agent_command_gate.py、test_codex_agent_command_gate.py、test_phase_role_commands.py。

フック単体の判定はOS-level sandboxではない。現在の既知の静的shell解析の限界は docs/tools/pr-merge-gate.md に記載済み。**当施策は既知の拒否を維持し、正常コマンドの誤拒否を機械的に検出するための短期対策**である。

### 新規fixture候補と入力形式

新規候補: tests/fixtures/command-gate-cases.json。1ケースのキーは次のとおり。

~~~json
{
  "id": "GATE-ALLOW-001",
  "platform": "claude",
  "role": "pr-reviewer",
  "tool_name": "Bash",
  "command": "gh pr view 123",
  "intent": "read_pr",
  "expected_decision": "allow",
  "expected_reason_code": "READ_ALLOWED",
  "reason": "PRの読み取り"
}
~~~

上記のreason_codeは**新規fixtureでの期待カテゴリ案**であり、既存hookに実在する文字列ではない。現行hookの実レスポンスを読んだうえで、既存reasonへのマッピングを導入する。互換性がないPFでは明示的にnot_applicableとし、存在しないaskをでっち上げない。

### 検証アダプタ

- 各PFの正規payloadを生成し、**hookだけ**を子プロセスとして呼ぶ。入力コマンドは破壊操作であっても絶対に実行しない。
- 結果は tool hookのstdout/exit code/permissionDecision等を**PF別の既知契約に基づき**allow/deny/askに正規化する。exit 0だけをallowとみなさず、レスポンスとhost側のpermission規則を分ける。
- 代表的な同じ意図の入力は両PFで検査する。ただしrole permissionの差は正規role仕様を参照し、無条件に同一判定としない。
- shellを完全解釈したという主張をしない。解釈不能な操作は既存規定どおりdeny/askへ回す。エージェントが別経路で拒否を迂回する試験はD0停止規律に従い、実操作で試さない。

### テストマトリクス（最低限）

| ケース | 正常側 | 拒否側 |
|---|---|---|
| GitHub PR | gh pr view, diff | AIによるmerge、既知のmerge REST/GraphQL |
| Git write | 許可された作業branchの非強制push | read-only roleのpush、禁止branch書込 |
| path | 許可されたcwd/cacheなど | 承認外ディレクトリ、symlink逸脱 |
| PF/tool | 対応するrole/toolの正規実行 | 不正role、間接dispatch、動的に読めない入力 |
| shell形 | 正常なwrapperとグローバルoption | 既知の禁止同義形 |
| 異常 | 有効・読み取り可能payload | 不正JSON、型不一致、解釈不能/例外 |

「正常側を誤denyしない」と「禁止側を誤allowしない」を**別々の指標**として集計。1方の率が高いことを他方の成功とはみなさない。

### 変更候補・導入手順

1. 既存のサンプルテストを撤去せず、上記対照fixtureとPFアダプタをtests/unitに追加する。
2. 最初は各プラットフォーム10件ずつ以上の代表正常/拒否（両方を含む）を固定。ケース数を成果の代用品とせず根拠ある操作を選ぶ。
3. 誤拒否・誤許可を見つけたらrole/command/正規契約を照合して専用Issue候補へ分類。短期テスト導入PRの中で無承認の権限緩和を行わない。
4. 既存のfull unitとasset_parity、実hook形式の回帰試験を実施する。

### AC-S3

- [ ] 正規payloadで両hookのALLOW/DENY対照ケースが実行される。各PFについて正常/禁止が各5件以上あり、異常系も含む。
- [ ] 正常な読み取りコマンドが誤拒否されないことと、危険な操作が誤許可されないことを両方検査する。
- [ ] 同じ意味の共通ケースでPF間の差があるならrole/hostの具体的な契約で説明される。
- [ ] 静的shell解析やhost permissionの限界を開示し、フック単体のGreenをlive認可保証と誤認しない。
- [ ] 破壊操作の実行なしに検証が完結する。現行fail-close/owner手動merge境界を弱めない。
