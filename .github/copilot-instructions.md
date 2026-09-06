<!-- generated-by: python3 -m guidance_sync render; edit-source-only -->
<!-- common-source: .ai/guidance/common.md; sha256: ce8ddc2c5c76c14b8764f1e2bfe00dc3ff51f40daa74fd1de305b1e382bc0bbd -->
<!-- principles-source: .ai/skills/spec-principles/SKILL.md; sha256: 17df1f5cce696a3a65181f465a2eba0a38afe65ed6a298acea0f230edaff64d9 -->
<!-- platform-source: .ai/guidance/platforms/copilot.md; sha256: d1ac7ffe3ad9d5a9a9724c16c567539e975ab7923f443fa255411092a0a3afb0 -->

# プロジェクト共通 guidance

この文書は Claude Code、Codex、GitHub Copilot に共通する意味内容の Source of Truth である。PF 固有の loader、tools、model、hook、dispatch、worktree などの実行機構はここへ混ぜず、各 PF の設定・原稿に残す。

## 言語・対外記録

- すべての説明・報告・質問は、ユーザーが明示的に別言語を指定しない限り日本語で行う。main thread、subagent、レビュー報告、PR 本文・コメントも同様とする。
- AI が PR 本文、PR コメント、レビューコメント、merge コメントを投稿する場合は、本文冒頭または件名で利用した AI agent 由来であることを明記する。
- オーナー判断が必要な矛盾・スコープ判断・据え置き可否はチャットで報告する。PR コメントやノードは永続化のための副次記録であり、それだけで報告済みとはみなさない。
- 節番号（§N）で文書を参照するときは、初出でそのファイルのパスを併記する。チャット報告、Issue 本文、PR コメントも同様とする。同一報告内の2回目以降は §N だけでよい。理由は、規範文書が多数あり節番号は文書間で重複するため、番号だけでは読み手がどの文書の話か特定できないからである。

## 作業分離・判断境界

- main thread は作業分解、実行主体の選定、進行管理、ユーザー報告を担い、実装・レビュー・是正は利用可能な別コンテキストへ分離する。
- レビュー担当と修正担当を分け、修正後は元レビューと別の文脈で再レビューしてから完了判断する。レビュー finding は記録し、対応内容・検証・最終結果も追跡可能にする。
- 矛盾・情報不足・オーナー判断必須で停止するときは、事実、選択肢、メリット／デメリット、理由付き推奨を示す。空の停止や AI による独断的な「対応不要」は禁止する。
- merge、push、force 系操作、外部への投稿など、取り消しにくい・共有状態に影響する・他者に見える操作は、実行前にチャットでオーナーへ報告して確認を得てから行う。clean 判定や過去に一度得た承認を、その後の実行の事前確認の代わりにしない。完了後にまとめて報告することは事前報告の代替にならない。
- スケジュールや後続スプリントへの繰越は、オーナーの明示指示なしに決めない。
- CI や外部サービスは無課金で実現できる方法を優先する。課金が避けられない場合は実装前にオーナーの明示認可を得る。
- 設計で仕様から一意に決まらない点は、論点・選択肢・推奨・暫定決定・影響範囲を判断記録へ残して前進する。
- 決定履歴・却下案・経緯・例外理由は rationale へ移設して保持し、現行手順・契約は古い記述を積み上げず現在の正しい内容へ更新する。
- rate limit や session 上限を理由に、model／reasoning effort／必要な役割分離を品質降格しない。同じ構成で再開する。
- 新しい AI 資産を作る前に既存資産の重複・競合を点検する。
- 実装設計では、module、interface、protocol、persistence、orchestration、prompt、log/version、test strategy の凍結セットを総点検してから実装へ進む。

## 仕様設計・点検の原則

<!-- principles-source: .ai/skills/spec-principles/SKILL.md; sha256: 17df1f5cce696a3a65181f465a2eba0a38afe65ed6a298acea0f230edaff64d9 -->

この節は `.ai/skills/spec-principles/SKILL.md` の常駐 guidance 用の意味保存写しであり、原則の正本ではない。正本を変更したら、この節と上記 hash を同時に更新する。

- PR1 もので分ける：入出力は「もの（実体）＋発生源（外部アクター）」で分け、使い道や内部発生プロセスでは分けない。
- PR2 判定軸を混ぜない：機械判定できる機構と、人が妥当性を確認する運用ルールを分ける。
- PR3 系外は非イベント：システムを介さない変更はイベント化せず、必要な検査は処理時に行う。
- PR4 観測できないものは持たない：顛末を観測できない事象に対する機能は作らない。
- PR5 状態の要否：毎回作り直せる導出物は状態化せず、過去を覚えなければ成立しない情報だけを状態にする。
- PR6 価値経路を遮断しない：すべての入力をプロセスから価値ある出力まで連続させる。
- PR7 矛盾は停止して打ち上げる：既存決定と両立しない事実は勝手に解決せず止めて確認する。ただし空で止めず、原案・比較・理由付き推奨を必ず添える。仕様設計・点検で止める前に、未決論点・質問は Q ノード（`type: Q`、決定時に DD へ昇格）、既存ノードへの指摘・矛盾は FND ノードとして起票する。必ず ①Q/FND ノード起票、②対象プロジェクトのダッシュボード更新（Q/FND とも必須）、③推奨を添えて停止、の順にし、チャットだけの未起票停止は禁止する。FND を resolved にしたら処置対象へ `→FND-x` 辺を付け、FND 起票時の `edges[].ref_version` を本文にも記録する。要件フェーズでは暫定で進めず他を進め、設計フェーズでは推奨案を DD に暫定決定として記録する。
- PR8 フル論理設計に MVP 印を付ける：論理は完全に作り、MVP 外を削除せず印で残す。
- PR9 DFD レベリング：階層をまたいで上位と下位を直結しない。
- PR10 認識合わせ先行：重い作業ほど、手順・成果物・未決事項・停止条件を先に揃える。

## 正本・実装規約

- 本リポジトリには doc_system と review_system が同居する。doc_system の正本は `doc-system-v2/` と関連する方法論・AI 資産、review_system の仕様・設計の正本は `docs/`（`docs/doc-system/` を除く）であり、混同しない。
- corpus ノード（`doc-system-v2/nodes/**`）は対応する `*-author` が一時出力し、`reconciliation-validator` の read-only 検証後に `reconciliation` が反映する。主文脈や他ロールは直接編集しない。
- review_system 本体の実装は Python を使用し、原則として標準ライブラリだけに依存する。
- 共通 AI 資産の正本は `.ai/` 配下に置く。PF の実行入口は正本そのものではなく、公式 import または追跡対象の生成物として接続する。
- 版付き文書（`policy_version` 等の `MAJOR.MINOR` を持つ文書）の記述が実態とずれていたら、版の bump が定数・設定・fixture へ波及することを理由に修正を見送らない。既定は直して版を上げることであり、据え置きが正当化されるのはオーナーが明示的にそう判断した場合だけである。版番号の仕組みは、内容を変えたときに追随すべき箇所を機械的に特定するために存在する。
- 逆に、1回の PR で版を複数回上げない。未 merge の一つの版遷移の途中にレビュー是正が入っても、その是正だけを理由にもう一度版を動かさない。是正を理由に版を動かしてよいのは、(1) MAJOR/MINOR の種別変更（直前に付けた版区分自体が誤りだったと判明した場合）、(2) 上げ忘れの補填、(3) 文書間の版リテラルのズレ是正 の3つに限る。据え置く場合はその理由を文書本文に記録し、黙って据え置かない。worked example は `docs/methods/blocker-gate-pre-use-policy.md` §11「ログ3チャネルと版」の「同一 PR 内での再 bump 要否」。

# GitHub Copilot 固有 guidance

この節は GitHub Copilot の loader と利用可能資産を記録する。共通の規範は直前の共通 guidance を正とする。

## PR7 の Copilot 実行契約

- 仕様設計・点検中の矛盾は、共通 guidance の PR7 にある ①Q/FND ノード起票、②対象ダッシュボード更新、③原案・比較・理由付き推奨を添えて停止、の順を省略しない。チャットだけで停止しない。
- ノード著作は利用可能な `verification-author`、検証・反映は `reconciliation-validator` → `reconciliation` を使う。これは Copilot で共通の意味を実行するための能力対応であり、Claude／Codex 固有の hook、command gate、worktree を持ち込まない。

## Skills（用途に応じて自動選択）

| Skill | 用途 |
|---|---|
| `align` | 着手前の認識合わせ |
| `value-trace` | イベントから出力までの価値経路・DFD レベリング検証 |
| `mvp-scope` | 価値ベースの MVP スコープ決定 |
| `schema-design` | 外部設定・基準ファイルのスキーマ設計 |
| `domain-model` | データ辞書から型安全なドメインモデルを導出 |
| `architecture-design` | 論理 DFD とドメインモデルから物理アーキテクチャを設計 |
| `orchestration-design` | runtime 制御フローを設計 |
| `prompt-design` | LLM システムプロンプトを設計 |
| `test-strategy` | review-system のテスト戦略 |
| `bloom-model-tier` | Bloom 分類で agent の model tier を選定 |
| `docidx` | v1 archive 専用ノード検索 |
| `coverage-html` | unittest と coverage HTML の確認 |
| `issue-pipeline` | Issue 実装から close までの進行管理。専用 Agent がない工程は利用可能な実行手段へ読み替え、役割分担・順序・STOP 契約は維持する |

## Prompts（ユーザーが `/` で明示起動）

- `/asset-lateral-deploy`: PF 間の資産移植
- `/asset-pipeline`: 手法から skill／agent への資産化
- `/impl-design-pipeline`: 実装設計の凍結セット作成
- `/spec-pipeline`: 要件から MVP scope までの仕様設計

## Agents

- ノード著作: `requirements-author`、`spec-author`、`analysis-author`、`design-author`、`verification-author`
- 一括著作: `authoring-fanout`
- 検証・反映: `reconciliation-validator` → `reconciliation`
- 点検・分析: `spec-inspector`、`structured-analysis`、`asset-auditor`
- ノード検索: `dsv2-lookup`
- 設定操作: `doc-system-config-operator`
- 共通参照: `doc-system-v2-authoring`（単独起動しない）

## Copilot 固有の非移植

- `/agy-delegate`、`/codex-review`、`/gh-create-issue` はローカル CLI、認証、対象 PF の明示スコープに依存するため移植しない。
- `issue-implementer`、`issue-fixer`、`pr-reviewer` の Copilot Agent 版は、project hook、worktree bind、ロール別 command gate の等価物がないため配置しない。
- Copilot は Prompt の明示起動と Agent の選択・委譲を使い、Claude／Codex 固有の hook や worktree 実行機構を持ち込まない。
