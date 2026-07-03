**status: decided**（2026-07-01 オーナー確定・Q-6 からの昇格・実施 sprint-1）

> **辺の扱い**: 本 DD は decided。被参照は昇格元 Q-6 の `→DD-22`（昇格辺）で確保され RULE-005（完全孤立）は生じない。先例（Q-3→DD-20・Q-5→DD-21・Q-4→DD-16・DD-15〜DD-21 はいずれも `edges: []`）に倣い本 DD は `edges: []` とし、義務辺 DD→X を張らない。理由：(1) 本決定の in-graph 反映先（FR-17・傘 SPEC-61/-1/-2/-3・PROMPT-8〜20）は**本 PR #61 で同時に著作済み**であり、決定スパイン規約に従い**反映済みノード側から backref を張り返して被参照を確保**する（FR-17 が `→DD-22` を保有）。義務辺 DD→X は「未反映」を示す RULE-001 シグナルだが、反映済みのため不要（＝DD 自身は義務辺を持たず反映側から張り返す DD-16/20/21 と同型）。(2) 参照した既存ノード（PROMPT-1〜7・SPEC-27・FR-13・NFR-3・SPEC-46・ORC-1/ORC-2）は本決定で**不変**のため、義務辺 DD→X（「未反映」の RULE-001 ERROR シグナル）を張る対象がない。(3) 昇格元 Q-6 が処置側から `→DD-22`（昇格辺）を張り返すことで本 DD の被参照辺が確保される（Q-3→DD-20・Q-5→DD-21 と同型）。義務辺を一旦張って即削除する二度手間を避け、最新の昇格 DD（DD-15〜DD-21）の慣行に揃える。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は Q-6 から昇格（DD であり FND でない）ため「指摘時 ref_version」の本文記録は DD-3 制度上不要（DD-16〜DD-21 と同扱い）。論点・現状・関連ノードの出所は Q-6（05-questions.md）であり、Q-6 が保持していた affects 辺の関連ノードと本 DD 起票時に docidx で確認した現バッジ x.y を下記「関連ノード（Q-6 由来・provenance）」に記録して追跡性を保つ。

**論点**（Q-6 より昇格・要約）: doc-system の設計層モデリング（PROMPT/ORC 等の在グラフ表現）を `.claude/skills/` の skill 資産へどう広げるか。Q-6 の①（pipeline/orchestrator skill をオーケストレーターエージェント化するか）と②（エージェント化しない skill を LLM プロンプト資産として PROMPT 設計ノード化するか）の 2 論点。両者は結合し（①でエージェント化された skill はモデル化対象が変わる）、決定はオーナー。

**現状**（Q-6 で読み取り専用確認済み・要約）:
- PROMPT-1〜7（05-static.md）は**著作エージェント限定**でモデル化（`*-author`×5／reconciliation=PROMPT-6／reconciliation-validator=PROMPT-7）。いずれも SPEC-27「著作エージェントが外部参照なしに著作規約を提供」→ FR-13「著作エージェントと層ワークフロー」を refine。PROMPT 設計スコープは意図的に著作エージェント限定。
- `.claude/skills/` の skill 群は LLM プロンプト資産だが、在グラフでは NFR-3「skill は self-contained」＋ SPEC-46（skill 自己完結を spec-inspector が WARNING 検査）の**検査対象アーティファクト**としてのみ存在し、skill を表す PROMPT 設計ノードは無い。
- pipeline/orchestrator skill（spec-pipeline / asset-pipeline / impl-design-pipeline）は下位 skill/agent を連鎖するが agent/PROMPT として未モデル化。ORC-1/ORC-2 は inspector・著作パイプラインを在グラフでモデル化済み。

**選択肢**（Q-6 より要約・排他）:

_①（pipeline/orchestrator skill のエージェント化）_
- **①-A（全 pipeline skill を orchestrator agent 化）**: fan-out 利点を最大化するが、agent は AskUserQuestion 不可のため対話的オーナー判断（Q/DD 起票→停止）が機能不全（STOP 報告止まり）＋5段ネスト安定化の前提が未確認の二重リスク。
- **①-B（エージェント化せず skill のまま維持）**: 対話的オーナー判断を主文脈で保てるが、コンテキスト隔離・並列 fan-out の利点を逃す。
- **①-C（ハイブリッド：対話入口は skill／非対話 fan-out のみ orchestrator agent 化）**: 対話性と fan-out 利点を両立。対話/非対話の境界をパイプラインごとに切り分ける設計コストを伴う。

_②（skill の PROMPT 設計ノード化）_
- **②-A（skill を PROMPT 設計ノードとしてモデル化・新要件軸を新設）**: 「著作支援は LLM＝PROMPT 設計対象」（MEMORY 方針）と整合。SPEC-27（著作スコープ）に混ぜず別の要件軸（新 FR/SPEC）を新設。要件層の起票拡大・skill 専用ノード型の是非・対象線引きを要する。
- **②-B（モデル化しない・現状維持）**: 最小コストだが skill が LLM プロンプト資産でありながら在グラフで PROMPT 表現されない非対称が残る。
- **②-C（①に従属）**: エージェント化された skill のみ ORC/PROMPT モデル化。①未決の間は②も決まらない。

**推奨**（Q-6 起票時）: ①-C を本命（①-B を安全側デフォルト）・②-C を本命。本 DD では下記のとおりオーナー判断により**①-C 確定＋②-A 採用**（②-C を超えて要件軸新設に踏み込む）に確定した。

**決定**（オーナー確定・2026-07-01）:
- **①-C（ハイブリッド）を採用**: 対話入口（Q/DD 起票・停止・AskUserQuestion によるオーナー判断）は skill のまま維持し、**非対話の fan-out（複数 author の並列著作・並列点検等）のみ orchestrator agent 化**する。Q-6 起票時に未確認だった前提「5段サブエージェントネスト安定化」は**公式ドキュメントで確認済み**（Claude Code v2.1.172 以降サブエージェントが子サブエージェントを spawn 可能／深さは main 直下から数え depth 5 が最終段で further spawn 不可・上限固定）。よって orchestrator agent → author → validator → reconciliation の連鎖は 5 段内に収まる。agent は AskUserQuestion 不可のため対話入口を skill に残すのが①-C の要。
- **②-A（PROMPT 型を流用・新要件軸を新設）を採用**: skill を LLM プロンプト資産として在グラフの **PROMPT 設計ノード**にモデル化する。**新ノード型は起こさず既存 PROMPT 型を流用**。ただし著作エージェント軸（SPEC-27→FR-13＝PROMPT-1〜7）とは出自が異なるため、**別の新要件軸（新 FR＋傘 SPEC）**を新設して skill 用 PROMPT を束ね、著作エージェント PROMPT と区別する。
- **対象範囲＝skill 13 件**: doc-system の価値実現（VAL-3「工程別スキルが著作規約を内包」・VAL-1 トレーサビリティ・VAL-4 段階的前進）に直結する **工程別 10**（align / value-trace / mvp-scope / schema-design / domain-model / architecture-design / orchestration-design / prompt-design / test-strategy / spec-principles）＋**パイプライン 3**（spec-pipeline / impl-design-pipeline / asset-pipeline）。**対象外 4 件**（coverage-html / asset-lateral-deploy / agy-delegate / bloom-model-tier）は NFR-3/SPEC-46 の検査対象アーティファクトのまま。docidx は境界だが既定 IN（retrieval が VAL-1 を支援）。
- **実施 sprint-1**（オーナー承認済み・独断繰越でない）。①-C の fan-out 実装は本 DD の後続作業（skill/agent 実体＝`.claude/` の再編）。
- **軸の設計精緻化（Q-6 後のオーナー確認・2026-07-01）**: 新要件軸（FR-17／傘 SPEC-61）は**キャリアで分けず「機能」で束ねる**。skill｜agent はノードの**キャリア属性**（SPEC-61-3 で要件化）で表し、将来の skill→agent 変換（①-C）は**キャリア属性＋版バンプ**（キャリア/本文変更＝MINOR・役割契約/IO 構造変更＝MAJOR）で扱う。これにより PROMPT ノードの要件軸付け替え（churn）を避ける。実現＝FR-17／SPEC-61-1〜3。

**根拠**:
- ①：agent の AskUserQuestion 不可は確定した技術制約であり、対話的オーナー判断を持つ pipeline を丸ごとエージェント化（①-A）すると PR7「空で止めない・起票して止める」が壊れる。対話入口を skill に残す①-C が制約と利点を両立する最小設計。Q-6 のブロッカーだった「5段ネスト安定化」前提は公式ドキュメントで確認済みのため①-C の fan-out 採用条件が満たされた。
- ②：MEMORY 方針「著作支援は LLM＝PROMPT 設計対象」との非対称（skill が LLM プロンプト資産でありながら在グラフ非表現）を解消する。新ノード型を起こさず PROMPT を流用することで型体系の肥大を避けつつ（PR1 単一責務・過剰型化回避）、SPEC-27→FR-13 の著作エージェント軸に混ぜず別 FR/傘 SPEC で束ねることで出自の異なる 2 系統（著作エージェント PROMPT／skill PROMPT）を区別する。②-C（①従属）を超えて②-A へ踏み込むのは、5段ネスト前提が確認でき①-C が確定したことで skill の在グラフ化を先送りする理由が消えたため。

**関連ノード（Q-6 由来・provenance／本 DD 起票時に docidx で現バッジ x.y を確認・RULE-004 一致確認済み）**:
- Q-6 "0.1"（05-questions.md Q-6 現バッジ v0.1.0・**昇格元**）
- PROMPT-4 "0.1"（05-static.md PROMPT-4 現バッジ v0.1.0・著作エージェント PROMPT 軸の代表。本決定で不変）
- SPEC-27 "0.3"（03-spec.md SPEC-27 現バッジ v0.3.0・著作エージェント著作スコープ。本決定で不変・新 skill 軸は混ぜない）
- FR-13 "0.1"（01-fr.md FR-13 現バッジ v0.1.0・著作エージェントと層ワークフロー。本決定で不変）
- NFR-3 "0.2"（02-nfr.md NFR-3 現バッジ v0.2.0・skill は self-contained。skill は検査対象として維持）
- SPEC-46 "0.2"（03-spec.md SPEC-46 現バッジ v0.2.0・skill 自己完結の WARNING 検査。維持）
- ORC-1 "0.4"（03-orchestration.md ORC-1 現バッジ v0.4.0・inspector オーケストレーション）
- ORC-2 "0.1"（03-orchestration.md ORC-2 現バッジ v0.1.0・著作パイプラインオーケストレーション）
- VAL-3 "0.1"（01-val.md VAL-3 現バッジ v0.1.0・著作効率＝工程別スキルが著作規約を内包。本決定の価値根拠）
- ACTOR-1 "0.1"（01-actors.md ACTOR-1 現バッジ v0.1.0・著作/レビュー主体）

（辺の扱いは上記「辺の扱い」注記のとおり `edges: []`。上記は義務辺ではなく本文で追跡する provenance 参照であり、本決定で不変（PROMPT-1〜7/SPEC-27 等）、または本 PR #61 で著作済みの反映先（FR-17/SPEC-61/PROMPT-8〜20）が反映側から backref を張り返すため、DD-22 自身は辺を張らない。）

**接続規則変更チェック（FND-99 パターン）**: 本 DD 単体では `config.yaml` の接続規則（`must_link_to` / `must_be_linked_from` / `fnd_lifecycle` / `decision_spine`）の追加・変更・削除を**含まない**（新 FR/傘 SPEC・skill 用 PROMPT の新設は後続著作で行い、そこで初めて PROMPT→SPEC 等の既存規則が適用される＝規則自体は不変）。よって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**本 DD では不要**（DD-17/18/19/20/21 の同チェックと同じ判定）。後続の新 FR/SPEC/PROMPT 著作が既存規則の適用範囲拡大にとどまり規則本体を変えない限り、伝播チェックは引き続き不要。もし後続著作で skill 専用の新接続規則が必要になった場合は、その著作パスで FND-99 パターンの伝播チェックを実施する。

**影響範囲（後続著作・sprint-1）**:

in-graph（**本 PR #61 で著作済み**。本 DD 起票時点では後続著作予定だった）:
- **FR-17（skill＝LLM プロンプト設計資産の機能軸）＋傘 SPEC-61（＋子 SPEC-61-1/-2/-3）**を著作済み（requirements-author → spec-author → reconciliation）。SPEC-27→FR-13 の著作エージェント軸とは別軸として区別。
- **対象 skill ごとの PROMPT 設計ノード PROMPT-8〜20（13 件）**を著作済み（design-author → reconciliation）。各 PROMPT は傘 SPEC-61 を親に持ち `carrier: skill` 属性を保有（PROMPT→SPEC 既存規則）。

in-graph（本 DD 昇格に伴う更新・別パス）:
- `doc-system/04-verification/05-questions.md`: Q-6 を `status: closed`（DD-22 へ昇格）・`→DD-22`（ref_version は DD-22 バッジ x.y＝"0.1"）付与・MINOR バンプ v0.1.0→v0.2.0（昇格辺追加＝構造変更・Q-3→DD-20／Q-5→DD-21 先例に倣う）。Q-6 の既存 affects 辺（PROMPT-4/PROMPT-6/SPEC-27/FR-13/NFR-3/SPEC-46/ORC-1/ORC-2/ACTOR-1）は昇格に伴い解消（本 DD で反映先＝新軸新設が確定したため）。

in-graph（不変）:
- 既存 PROMPT-1〜7・SPEC-27・FR-13 は不変（著作エージェント軸として維持）。NFR-3・SPEC-46 も不変（skill は検査対象アーティファクトとして維持しつつ、新 PROMPT 軸を追加で載せる）。

out-of-graph（後続作業）:
- ①-C の fan-out 実装＝`.claude/` の skill/agent 実体再編（対話入口 skill／非対話 fan-out orchestrator agent の分割）。必要なら ORC への追記（在グラフ反映は別途 design-author で判断）。

**覆る場合の影響範囲**: 本決定を覆す場合＝新 FR/傘 SPEC・PROMPT-8〜（skill PROMPT 群）を撤回し、skill を NFR-3/SPEC-46 の検査対象のみへ戻す（②-B 相当）。①-C を覆す場合は `.claude/` の orchestrator agent 化を差し戻し skill 単体へ戻す（①-B 相当）。Q-6 を再 open（または別途整理）する。影響は要件層の新 FR/SPEC・設計層の新 PROMPT 群・`.claude/` 資産に限定され、既存の著作エージェント軸（PROMPT-1〜7・SPEC-27・FR-13）・検査軸（NFR-3・SPEC-46）は不変のため巻き戻し範囲は新設分に閉じる。
