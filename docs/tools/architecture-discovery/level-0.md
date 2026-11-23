# 開発基盤の Level 0 PFD・DFD

基準は `main` [`4866a525c5ce923992a62cab3b6458d31bbda9dc`](https://github.com/hiratashinnya/review-system/commit/4866a525c5ce923992a62cab3b6458d31bbda9dc)。識別子と担当は [発掘目録](README.md) に従う。この図では工程で交わる境界と独立した検査・記録経路を示す。実行者や前提は各入口によって異なる。製品側の既存 DFD は [docs/process/01-dfd-level1.md](../../process/01-dfd-level1.md) を参照。

## PFD — P0 開発作業・補助処理

```mermaid
flowchart TD
    subgraph L1[依頼者・主文脈]
        Req([P0-01 Issue と対象を指定])
        Refuse([停止・診断・前提の再確認])
        Expect[P0-06 取込期待値を記録して独立レビューを依頼]
        ReviewResult{カルテの是正対象を確認}
        Notice([通知結果を受領])
        Finish([検査結果・残課題を受領])
    end
    subgraph L2[工程ゲート・Git 安全制御]
        Gate{P0-02 依存・権限・対象を確認}
        Git{P0-03 必要な Git 操作の前提を確認}
        Collect{P0-05 Stop・回収・解放を確認}
        Continue{後続工程の入力と前提を照合}
        Hold([一時停止・解放待ちを再評価])
    end
    subgraph L3[工程担当]
        Run[P0-04 束縛した工程で成果物を作成]
        Publish[作者が commit・push、実装担当が draft PR を作成]
        Fix[指摘を是正]
    end
    subgraph LReview[独立レビュー・カルテ取込]
        Review[対象をレビューし主 checkout に原本を新規保存]
        Ingest{原本を照合してカルテに取り込む}
        Recover([保存到達点に応じて回復])
    end
    subgraph L4[CLI・hook・CI の独立した経路]
        Notify[P0-07 状態から通知を判断]
        CheckTrigger([検査・同期要求])
        Check{P0-08 品質検査・Project 同期}
        CheckOutput([診断・結果・無変更])
        Snapshot[Actions が snapshot を発行]
        ApplyProject[Project Status の変更を適用]
        ReportFile[同期 CLI が report.json を保存]
        Report[Actions が Project 同期の report.json を発行]
        DecisionTrigger([設計判断・オーナー判断])
        Ledger{P0-09 参照と形式を検証し正本に登録}
        LedgerOutput([登録・索引・明示起票の結果])
    end
    Req --> Gate
    Gate -->|許可| Git
    Gate -->|拒否・証拠不足| Refuse
    Git -->|確認済み・操作不要| Run
    Git -->|不一致・操作拒否| Refuse
    Run -->|作者の公開工程| Publish
    Run -->|公開を伴わない引渡し・停止| Collect
    Publish -->|公開結果・停止イベント| Collect
    Collect -->|回収済み・解放状態を渡す| Continue
    Collect -->|handoff 未生成で一時停止中| Hold
    Collect -->|handoff なしで停止し running 残留・回収不能| Refuse
    Collect -->|Stop のカルテ検査でブロック| Fix
    Hold -.->|担当者の再開後に handoff 検出| Collect
    Hold -.->|次の gate が保留中の解放を再試行| Continue
    Continue -->|ready のレビュー対象・該当する PR head| Expect
    Continue -->|承認済み入力・前担当の remote exact OID| Gate
    Continue -->|後続作者に必要な前担当の解放待ち| Hold
    Continue -->|該当工程の確認条件を充足| Finish
    Continue -->|回収済み STOP・未解消・入力不整合| Refuse
    Expect -->|承認済みの対象・照合ヘッダ| Review
    Review -->|専用 Markdown の絶対パス| Ingest
    Ingest -->|事前拒否・空レポート| Refuse
    Ingest -->|書込失敗| Recover
    Ingest -->|取込済み・未完了| Expect
    Ingest -->|取込完了| ReviewResult
    Ingest -.->|対象 verb の実行後| Notify
    Notify -->|通知・スキップ・診断| Notice
    ReviewResult -->|要是正| Fix
    ReviewResult -->|完了条件充足| Finish
    Fix -->|是正後に公開| Publish
    CheckTrigger --> Check
    Check -->|単独検査の結果・発行前の失敗| CheckOutput
    Check -->|発行可能な snapshot| Snapshot
    Snapshot -->|発行後の判定| CheckOutput
    Check -->|適用する Status の差分あり| ApplyProject
    Check -->|dry-run・適用前の中断・差分なし| ReportFile
    ApplyProject -->|適用結果・警告| ReportFile
    ReportFile -->|workflow で CLI が 0 または 20| Report
    ReportFile -->|単独実行の結果・保存失敗| CheckOutput
    Report -->|発行後に 20 なら job 失敗| CheckOutput
    DecisionTrigger --> Ledger
    Ledger -->|条件充足| LedgerOutput
    Ledger -->|不整合・書込不可| Refuse
```

| 処理・担当 | 正常経路と外部副作用 | 拒否・保留・診断の境界と根拠 |
| --- | --- | --- |
| `P0-01`〜`P0-02` D2、依存判定 D5 | 依頼から GitHub の証拠または検証対象の snapshot、工程承認・束縛を照合。許可後の managed dispatch は起動単位の所有台帳を更新し得る。 | 依存や証拠の不備、承認と role/run/target/OID/digest の不一致を診断。条件を満たさない起動へ進まない。[工程ゲート](../../../issue_start/gate.py) · [束縛](../../../issue_start/phase_dispatch.py) · [束縛テスト](../../../tests/unit/test_phase_dispatch_binding.py) |
| `P0-03` D3 | `verify_branch_source` は default または PR head を照合用ローカル ref に fetch して OID を照合する。`new-branch` は照合済みの起点で新規 branch を作成して checkout、`adopt-branch` は既存 branch の ref・OID・使用状況を照合して checkout する。 | 不整合は作成・checkout 前に拒否する。起点照合で fetch 後に拒否しても照合用 ref の更新は残り得る。[起点 facade](../../../branch_source/policy.py) · [CLI](../../../gitgate/cli.py) · [起点テスト](../../../tests/unit/test_branch_source_refactor_g05.py) |
| `P0-04` D2、Git 操作 D3 | 工程担当が IR/VD/CP/TestDesign 等の成果物と handoff を作成。branch を継承する作者は commit・push し、後続作者は回収・解放済み receipt とリモート branch の exact OID を照合する。実装担当は検証・commit・push の後に draft PR を開き、その head が実装レビューの照合対象になる。 | push や draft PR の作成に失敗した場合は、存在を確認できた ref・PR と停止理由を主文脈へ渡す。後続の採用は承認された OID と所有状態が前提。[工程契約](../../../.ai/skills/issue-pipeline/SKILL.md) · [実装担当](../../../.ai/agents/issue-implementer.md) · [push テスト](../../../tests/unit/test_gitgate.py) · [後続の adopt テスト](../../../tests/unit/test_gitgate_worktree.py) |
| `P0-05` D2、回収・解放 D3 | Stop フックが担当本人の handoff を検出すると台帳を `stopped` に進め、回収・解放を試みる。STOP の報告も回収対象になる。後続工程は束縛に合う `ready` かつ未解消の指摘・未決の判断がない入力を受理し、後続作者の起動は前担当の `released` と回収済み receipt を検証する。 | 手掛かりとなる handoff がない場合は `running` のまま保留する。担当が続行できる一時停止なら後の Stop で回収できるが、実行が終了したままなら回収・後続 dispatch が拒否される。回収失敗は `stale`、回収後の物理削除待ち `release_pending` は次の gate が再試行。fixer の Stop がカルテ検査でブロックされた場合は回収・解放段に進まない。同じ role の再投入は検証済みの実行上限 STOP receipt を扱う別の継続経路。[Stop](../../../issue_start/subagent_hooks.py) · [工程入力](../../../issue_envelope/handoff.py) · [作者の継続](../../../issue_start/author_continuation.py) · [解放待ち](../../../issue_start/gate_residue.py) · [停止・回収テスト](../../../tests/unit/test_subagent_hooks.py) · [running 残留テスト](../../../tests/unit/test_claude_limit_running_stall.py) |
| `P0-06` D1、レビュー依頼は主文脈 | 主文脈は `karte activate` で取込期待値を記録してから独立レビューを依頼。現行の Claude Code の `pr-reviewer` は、主 checkout にある `tmp/_handoff/pr-reviewer--<key>.md` の絶対パスへ原本を新規保存し、本人が `ingest-reviewer` で取り込む。CLI が専用パス・ヘッダ・round を検証し、scope 申告原本、カルテ、来歴の確定、進行ポインタの順に保存する。 | 期待値不一致・空レポート（[#801](https://github.com/hiratashinnya/review-system/issues/801)）はカルテ等の書込前に拒否。保存途中のエラーと、要再掲の指摘を引き継いだ「取込済み・未完了」は下表の回復へ。取込完了後の是正・完了は主文脈がカルテから判断する。[レビュー担当](../../../.ai/agents/pr-reviewer.md) · [受入 CLI](../../../karte/reviewer_cli.py) · [保存処理](../../../karte/ingest_review.py) · [受入・回復テスト](../../../tests/unit/test_karte_reviewer_ingest.py) |
| `P0-07` D1 | 通知フックは対象 verb の後に `status` を読み、既読記録に応じて `systemMessage` を返す。GitHub への指摘の発行は専用 verb。 | 通知用 status を取得できない場合はスキップ。既読記録の保存に失敗しても通知は返し得る。[通知](../../../karte_notify/hook.py) · [通知テスト](../../../tests/unit/test_karte_notify_fail_open.py) |
| `P0-08` D5 | 検査は単独実行できる。Actions が blocker snapshot を発行。Project 同期 CLI は有効な snapshot と Project の状態から計画を作り、apply 指定時に許可された変更を反映。workflow は CLI がローカルに保存した `report.json` を、終了コード 0 または 20 のとき `project-status-sync-report` ブランチへ発行する。 | dry-run では Status を更新せず、snapshot 不正・degraded・鮮度超過の中断では Project API を呼ぶ前に診断を作る。いずれも workflow のレポート発行対象になり得る。CLI が中断・警告の 20 を返すと、発行後に job が失敗し、レポート保存不能などの他の非 0 は発行前に job が失敗する。blocker の部分 snapshot は発行後に異常を報告でき、parity の `STALE` は診断。[snapshot workflow](../../../.github/workflows/blocker-snapshot.yml) · [Project CLI](../../../project_status_sync/cli.py) · [Project workflow](../../../.github/workflows/project-status-sync.yml) · [同期テスト](../../../tests/unit/test_project_status_sync.py) · [parity 仕様](../../../asset_parity/README.md) |
| `P0-09` D4 | 判断を既存 CLI で記録し、索引を導出する。ADR の明示的な `file-issue --create` では外部 Issue 作成を伴う。 | 検査が schema 不正や既存原本の不適切な変更を報告する。Issue 作成後に追跡番号の書戻しが失敗した場合は番号から復旧。[ADR の使い方](../../../adr/README.md) · [ADR テスト](../../../tests/unit/test_adr.py) · [台帳の検査](../../../feedback_ledger/check.py) · [台帳テスト](../../../tests/unit/test_feedback_ledger.py) |

`P0-06` の保存到達点と回復は [カルテの取込契約](../../../karte/README.md) に従う。

| 取込結果 | 保存到達点と次の担当 |
| --- | --- |
| 検証拒否（4） | カルテ・scope 申告原本・ポインタは更新前。主文脈とレビュー担当が期待値や原本の不適合を確認する。 |
| scope 保存後、カルテ書込失敗（4） | カルテより先に保存された scope 申告原本と来歴の処理中記録が残り得る。カルテの round と期待値は据え置き。原因を解消してからレビュー担当が同じ原本で再取込する。 |
| カルテ保存後、来歴確定・ポインタ書込の失敗（4） | カルテには当該 round があり、ポインタは進んでいない。主文脈が `render` で保存済み round を確認して `activate` でポインタを回復する。 |
| 取込済み・未完了（5） | 再掲漏れの対象指摘を引き継いで round を保存し、期待値を消費済み。主文脈が次 round の期待値を記録し、レビュー担当が再掲する。 |
| 取込完了（0） | 主文脈がカルテを読み、是正・完了を判定する。 |

## DFD — D0 開発基盤のデータ境界

```mermaid
flowchart LR
    Owner[依頼者・主文脈]
    Workers[工程担当]
    Reviewer[独立レビュー担当]
    PF[PF hook・Actions・MCP クライアント]
    GH[GitHub Issues・PR・Project・remote refs]
    H([D0 開発基盤])
    S1[(S1 Git refs・worktree・所有台帳)]
    S2[(S2 工程成果物・handoff)]
    S3[(S3 レビュー原本・カルテ・scope 原本・進行ポインタ)]
    S4[(S4 ADR・FBK・FBP・TRG)]
    S5[(S5 規範・設定・schema・baseline)]
    S6[(S6 スナップショット・診断レポート・生成 guidance)]
    S7[(S7 通知既読・MCP cooldown)]
    Owner -->|Issue 識別・対象・承認・判断・取込期待値| H
    H -->|判定・診断・通知・索引| Owner
    Workers -->|工程成果物・handoff・公開する branch と draft PR 情報| H
    H -->|束縛済み作業入力・検証結果| Workers
    H -->|レビュー入力・照合ヘッダ・取込結果| Reviewer
    Reviewer -->|レビュー原本・取込要求| H
    PF -->|hook イベント・検査や同期の要求・MCP 要求| H
    H -->|allow/block・結果 JSON・終了コード・レポート| PF
    GH -->|Issue 依存・PR 差分と head・remote OID・snapshot・Project 状態| H
    H -->|作者が push する branch ref・実装担当の draft PR| GH
    H -->|新規 Issue・コメント・適用する Project Status| GH
    H -->|Actions が発行する snapshot・同期レポート| GH
    S1 -->|ローカル ref・台帳状態| H
    H -->|照合用 ref・作成や採用の Git 状態・更新後の所有状態| S1
    H -->|工程成果物・回収済み handoff| S2
    S2 -->|成果物・受領済み handoff| H
    H -->|取込期待値・レビュー原本・scope 原本・来歴・カルテ・進行状態| S3
    S3 -->|レビュー原本・取込期待値・進行状態・カルテ| H
    H -->|設計判断・オーナー判断・追跡状態| S4
    S4 -->|判断原本・置換関係・参照 ID| H
    S5 -->|入力契約・規範・比較基準| H
    H -->|明示更新用の baseline JSON| PF
    H -->|発行用 snapshot と report.json・生成 guidance| S6
    S6 -->|検証対象 snapshot・発行用 report.json・生成済み guidance| H
    H -->|既読記録・cooldown| S7
    S7 -->|既読状態・再試行可能時刻| H
```

| ストア | 原本・生成物、更新主体 | 根拠 |
| --- | --- | --- |
| `S1` D2/D3 | Git がローカル ref と worktree を保持。起点の検証が照合用 ref を更新し、作成・採用が branch の checkout を変える。`tmp/_worktree/ledger.json` は main worktree にある所有情報の原本で、工程ゲート、フック、`gitgate` が `issue_start` の台帳 API を使って更新する。作者の push 済み remote ref と draft PR の head は GitHub/Git から照会する。 | [起点検証](../../../branch_source/policy.py) · [所有台帳](../../../issue_start/worktree_ledger.py) · [台帳テスト](../../../tests/unit/test_worktree_ledger.py) |
| `S2` D2/D3 | 工程担当が所定のディレクトリに canonical TOML と工程 handoff を作成し、回収処理が回収物を主 checkout に保存する。dispatcher の承認・期待値・Git OID を成果物の申告と照合する。 | [配置規則](../../../issue_envelope/placement.py) · [工程 handoff](../../../issue_envelope/handoff.py) · [回収](../../../gitgate/worktree_collect_handoff.py) · [配置テスト](../../../tests/issue_envelope_tests/test_artifact_paths.py) |
| `S3` D1 | 主文脈が `activate` で取込期待値を `tmp/_karte/active.json` に記録する。独立レビュー担当は主 checkout の `tmp/_handoff/pr-reviewer--<key>.md` にレビュー原本を直接保存する。`karte` の取込処理が scope 申告原本・来歴、`tmp/_karte/issue-<N>.md`、進行ポインタを更新し、`status` の表示は導出する。 | [レビュー原本パス](../../../karte/handoff_path.py) · [カルテの保存境界](../../../karte/README.md) · [来歴](../../../karte/scope_origin_store.py) · [来歴テスト](../../../tests/unit/test_karte_scope_origin.py) |
| `S4` D4 | `<tool>/adr/*.toml` は道具別設計判断の追跡原本。`.ai/feedback/{ledger,queue,triage}/*.toml` はオーナー判断・改訂案・棚卸しの記録。各 CLI が保存し、索引と表示はそこから導出。 | [ADR schema](../../../adr/schema.py) · [台帳パス](../../../feedback_ledger/paths_layout.py) · [ADR README](../../../adr/README.md) · [台帳 README](../../../feedback_ledger/README.md) |
| `S5` D5 | 版管理された規範・schema・例外・`maintainability_lint/baseline.json` が判定入力。lint の baseline は明示生成できる負債集合。`.ai/guidance/` と共通原則 Skill の原稿は guidance の入力正本。 | [baseline の読み書き](../../../maintainability_lint/baseline.py) · [guidance の入力・出力パス](../../../guidance_sync/sources.py) · [guidance テスト](../../../tests/unit/test_guidance_sync.py) |
| `S6` D5 | `blocker_gate` が Issue 依存から snapshot JSON を生成し、Actions が `blocker-snapshot` ブランチへ発行する。gate と Project 同期は完全性や鮮度を用途別に検証する。Project 同期 CLI はローカルに `report.json` を保存し、Actions が `project-status-sync-report` ブランチへ発行する。`AGENTS.md` と `.github/copilot-instructions.md` は `guidance_sync` が原稿から導出する展開先。 | [snapshot 発行](../../../.github/workflows/blocker-snapshot.yml) · [鮮度の検証](../../../project_status_sync/snapshot_check.py) · [レポート発行](../../../.github/workflows/project-status-sync.yml) · [guidance 同期](../../../guidance_sync/sync.py) |
| `S7` D1/D2 | 通知フックが `tmp/_karte/notified/issue-<N>.json` に既読状態を保持。レビュー MCP は `${XDG_STATE_HOME:-~/.local/state}/claude-review-mcp/rate-limit.json` に自身の cooldown を保持。カルテ原本への更新と、レビュー原本の受入はそれぞれ `karte` が担当する。 | [通知状態](../../../karte_notify/notify.py) · [MCP の保存と参照](../../../.codex/mcp/claude_review/server.py) · [MCP テスト](../../../tests/unit/test_claude_review_mcp.py) |

Level 1 の引き渡しは D1 が `P0-06`・`P0-07`／`S3`・`S7` の通知側、D2 が `P0-01`・`P0-02`・`P0-04`・`P0-05`／`S1`・`S2`・`S7` の MCP 側、D3 が `P0-03`・`P0-05`／`S1`・`S2` の Git 側、D4 が `P0-09`／`S4`、D5 が `P0-02` の依存判定と `P0-08`／`S5`・`S6`。共有境界では変更主体と読取側を双方の図で照合する。[後続の図・根拠の規則](README.md#f1-に渡す図根拠の規則)
