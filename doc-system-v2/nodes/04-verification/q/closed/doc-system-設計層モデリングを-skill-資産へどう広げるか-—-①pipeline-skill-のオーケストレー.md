**status: closed**（DD-22 へ昇格）

**指摘時 ref_version**: PROMPT-4 "0.1"（05-static.md PROMPT-4 現バッジ v0.1.0 時点）・PROMPT-6 "0.1"（05-static.md PROMPT-6 現バッジ v0.1.0 時点）・SPEC-27 "0.3"（03-spec.md SPEC-27 現バッジ v0.3.0 時点）・FR-13 "0.1"（01-fr.md FR-13 現バッジ v0.1.0 時点）・NFR-3 "0.2"（02-nfr.md NFR-3 現バッジ v0.2.0 時点）・SPEC-46 "0.2"（03-spec.md SPEC-46 現バッジ v0.2.0 時点）・ORC-1 "0.4"（03-orchestration.md ORC-1 現バッジ v0.4.0 時点）・ORC-2 "0.1"（03-orchestration.md ORC-2 現バッジ v0.1.0 時点）・ACTOR-1 "0.1"（01-actors.md ACTOR-1 現バッジ v0.1.0 時点）

> 本 Q の affects 辺（Q→X）は義務辺：辺の存在＝当該要素へのモデル化判断が未反映であることの追跡（RULE-002 WARNING）。決定（DD 昇格）時に辺を解消し、反映先（新規 PROMPT/ORC/FR/SPEC または現状維持）を確定する。本 Q は config.yaml の接続規則（must_link_to / must_be_linked_from）の変更を**含まない**未決論点のため、著作資産伝播チェック（FND-99 パターン）は不要。→ DD-22 で確定（2026-07-01・①-C／②-A 採用）。旧 affects 辺は反映先＝新要件軸（新 FR＋傘 SPEC・PROMPT-8〜）新設方針の確定に伴い解消し、DD-22 へ昇格辺を張った。

> **改訂理由（z バンプ v0.2.0→v0.2.1・SPEC-62/Issue #68）**: 本文中の孤立 `---`（ノード分離記法の本文内誤用）と `## `（H2＝パーサ境界）による本文 silent 截断を是正。内部 `---` を除去し本文内の小見出しを `## `→`### `（非境界）へ変更（論点・①・②・推奨・ブロッカーが本文から脱落していた）。実質内容の変更なし。

**論点（1文）**: doc-system の設計層モデリング（PROMPT/ORC 等の在グラフ表現）を `.claude/skills/` の skill 資産へどう広げるか——**①pipeline/orchestrator skill をオーケストレーターエージェント化するか**、**②（エージェント化しない）skill を LLM プロンプト資産として PROMPT 設計ノード化するか**。両者は結合し（①でエージェント化された skill は ORC/PROMPT のモデル化対象が変わるため、②のモデル化スコープが①の決定に従属する）、決定はオーナー。

### 読み取り専用で検証した現状（根拠）

1. **PROMPT-1〜7（05-static.md）は著作エージェントのみをモデル化**：`*-author`×5 ／ reconciliation=PROMPT-6 ／ reconciliation-validator=PROMPT-7。いずれも **SPEC-27**「著作エージェントが外部参照なしに著作規約を提供」→ **FR-13**「著作エージェントと層ワークフロー」を refine。**PROMPT 設計スコープは意図的に著作エージェント限定**（FR-13 が列挙するのも `*-author`＋reconciliation 系のみ）。
2. **`.claude/skills/` の skill 群（18件）は LLM プロンプト資産**（align / value-trace / mvp-scope / schema-design / domain-model / spec-pipeline / asset-pipeline / architecture-design / orchestration-design / prompt-design / impl-design-pipeline / test-strategy / asset-lateral-deploy / agy-delegate / bloom-model-tier / docidx / spec-principles / coverage-html）だが、在グラフでは **NFR-3「スキルは self-contained」＋ SPEC-46/-1/-2「skill 自己完結」（spec-inspector が WARNING 検査）** という**検査対象アーティファクト**としてのみ存在し、**skill を表す PROMPT 設計ノードは無い**。
3. **pipeline/orchestrator skill ＝ spec-pipeline / asset-pipeline / impl-design-pipeline**（下位 skill/agent を連鎖）。ORC-1/ORC-2 は inspector・著作パイプラインを在グラフでモデル化済みだが、methodology の pipeline skill は agent/PROMPT としては未モデル化。

### 検証した技術的制約（選択肢のトレードオフに反映）

- **前提の要確認**：「Claude Code が5段サブエージェントネストを安定化する」は**オーナー伝聞であり未確認**。①の選択肢評価はこの前提が確認できることを条件とする（確認前は安定化前提の選択肢を採れない）。
- **agent は AskUserQuestion 不可**（subagent は質問できず STOP 報告。CLAUDE.md）。対話的にオーナー判断（Q/DD）を仰ぐ pipeline（spec-pipeline・impl-design-pipeline 等）をエージェント化すると**対話性を失う**。一方でエージェント化は**コンテキスト隔離・並列・5段ネストの fan-out 利点**を持つ。
- **②でモデル化を広げる場合、SPEC-27（著作スコープ）に混ぜられない**：別の要件軸（新 FR/SPEC）が要る。または skill 専用ノード型の是非を別途決める必要がある。

### ① pipeline/orchestrator skill のオーケストレーターエージェント化

**論点**: spec-pipeline / asset-pipeline / impl-design-pipeline 等の連鎖型 skill を、サブエージェント（orchestrator agent）として実装するか。

**選択肢（排他・トレードオフ）**:

- **①-A（全 pipeline skill を orchestrator agent 化）** — 連鎖型 skill をすべてサブエージェント化し、下位 author/分析エージェントを fan-out 実行する。トレードオフ＝コンテキスト隔離・並列・5段ネスト fan-out の利点を最大化するが、(1) **agent は AskUserQuestion 不可**のため spec-pipeline/impl-design-pipeline の**対話的オーナー判断（Q/DD 起票→停止）が機能不全**になる（STOP 報告止まりで対話継続できない）、(2) **5段ネスト安定化の前提が未確認**（オーナー伝聞）のため、確認前にこの選択肢を採るのは技術リスクを伴う。
- **①-B（エージェント化しない・skill のまま維持）** — 現状の skill（手順記述＋主文脈実行）を維持する。トレードオフ＝対話的オーナー判断（PR7・空で止めない／起票して止める）を主文脈で保てるが、コンテキスト隔離・並列 fan-out の利点を逃し、大規模パイプラインで主文脈の肥大を招く。
- **①-C（ハイブリッド：対話の入口は skill のまま／非対話の fan-out のみ orchestrator agent 化）** — オーナー判断を要する対話フェーズ（Q/DD 起票・停止）は skill（主文脈）に残し、非対話で並列実行できる純 fan-out（例: 複数 author の並列著作、点検の並列実行）のみをサブエージェント化する。トレードオフ＝対話性と fan-out 利点を両立するが、**対話/非対話の境界をパイプラインごとに切り分ける設計コスト**が増し、skill とエージェントの責務分割を明示する必要がある。

**①の推奨**: **①-C（ハイブリッド）を本命・①-B を当面の安全側デフォルト**。理由：(1) **agent の AskUserQuestion 不可は確定した技術制約**であり、対話的オーナー判断を持つ pipeline（spec-pipeline・impl-design-pipeline）を丸ごとエージェント化（①-A）すると PR7「空で止めない・起票して止める」の運用が壊れる。対話入口を skill に残す①-C が制約と利点を両立する最小設計。(2) ただし①-C の fan-out 部分は**5段ネスト安定化の前提確認が条件**であり、前提が未確認の現時点では**①-B（現状維持）を安全側デフォルト**として、前提確認後に①-C へ段階移行するのが現実的。(3) ①-A は対話性喪失と未確認前提の二重リスクで非推奨。

### ② skill の PROMPT 設計ノード化（モデル化スコープ拡張）

**論点**: LLM プロンプト資産である skill を在グラフの PROMPT 設計ノードとしてモデル化対象に含めるか。現状 PROMPT-1〜7 は著作エージェント限定（SPEC-27→FR-13）で、skill は検査対象アーティファクト（NFR-3/SPEC-46）としてのみ存在する。

**選択肢（排他・トレードオフ）**:

- **②-A（skill を PROMPT 設計ノードとしてモデル化・新要件軸を新設）** — skill を LLM プロンプト資産として在グラフ表現し、SPEC-27（著作スコープ）に混ぜず**別の要件軸（新 FR/SPEC）**を新設して接続する。トレードオフ＝「著作支援は LLM＝PROMPT 設計対象」（MEMORY 方針）と整合し skill のプロンプト設計を在グラフで追跡できるが、(1) 要件層に新 FR/SPEC を起票するスコープ拡大、(2) 18 件全 skill を対象にするか pipeline 系のみかの線引き、(3) **skill 専用ノード型の是非**（PROMPT を流用するか新型を起こすか）を別途決める必要がある。
- **②-B（モデル化しない・現状維持）** — skill は NFR-3/SPEC-46 の検査対象アーティファクトに留め、PROMPT 設計ノード化しない。トレードオフ＝最小コストで PROMPT スコープの意図的限定（SPEC-27）を保てるが、skill が LLM プロンプト資産でありながら在グラフで PROMPT として表現されない**非対称が残る**（MEMORY「著作支援は LLM＝PROMPT 設計対象」との緊張）。
- **②-C（①の決定に従属：orchestrator agent 化された skill のみ ORC/PROMPT モデル化・非エージェント skill は現状維持）** — ①でエージェント化された skill（①-A/①-C の結果）のみ在グラフの ORC/PROMPT としてモデル化し、エージェント化しない skill は②-B（現状維持）とする。トレードオフ＝①②の結合を素直に尊重しモデル化対象を「エージェント化された資産」に限定できる（既存 ORC-1/ORC-2・PROMPT-1〜7 の「在グラフ＝エージェント」という現行原則と整合）が、①が未決の間は②も決まらず、非エージェント skill のプロンプト設計は引き続き在グラフ外に残る。

**②の推奨**: **②-C（①の決定に従属）を本命**。理由：(1) **①②は結合**しており（①でエージェント化された skill のみモデル化対象が変わる）、現行の在グラフ原則は「ORC/PROMPT＝エージェント（著作エージェント・inspector・著作パイプライン）」で一貫している（PROMPT-1〜7・ORC-1/ORC-2）。この原則を維持するなら**モデル化対象＝エージェント化された資産**とする②-C が最も摩擦が小さい。(2) ②-A（全 skill の PROMPT 化）は新要件軸・skill 専用ノード型・18 件の線引きという**未決を三つ抱え込む**ため、まず①を決めてから残余（非エージェント skill のプロンプト設計を在グラフ化するか）を**別 Q として切り出す**方が単一責務で進めやすい。(3) ②-B（純現状維持）は MEMORY 方針との非対称を放置するため、①でエージェント化が進む範囲は②-C で同時に解消したい。**ただし「非エージェント skill のプロンプト設計を在グラフ化するか（②-A 相当の残余）」は別途オーナー判断**とし、本 Q では①従属の②-C を当面の方針として推奨する。

**結合に関する推奨手順**: ①②は結合するため、**①を先に決定（pipeline skill のエージェント化方針）→ ②は①に従属（②-C）して確定 → 非エージェント skill の PROMPT 化（②-A 残余）は別 Q として切り出す**順を推奨する。①-C の fan-out 部分は5段ネスト安定化の前提確認が条件のため、前提確認の可否もオーナーに合わせて確認する。

**ブロッカー**: (1) **5段サブエージェントネスト安定化の前提確認**（オーナー伝聞→要確認。①-A/①-C の fan-out 採否の前提）、(2) ①の方針選択（A/B/C）、(3) ②のモデル化スコープ（①従属の②-C を採るか、②-A で全 skill へ広げ新要件軸・skill 専用ノード型を起こすか）、(4) 実施スプリント——いずれも**オーナー判断**。**独断でのスプリント繰越は禁止**（CLAUDE.md「スケジュール独断禁止」）。本 Q は `scheduled` を空のままとし判断を仰ぐ。決定後は DD へ昇格（id 通貫）。
