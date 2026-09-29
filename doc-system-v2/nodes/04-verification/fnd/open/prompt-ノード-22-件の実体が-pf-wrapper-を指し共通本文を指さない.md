**深刻度**: WARNING（実害で判定する。判定根拠は後述）

**対応 Issue**: #562（全スキル・全カスタムエージェントの契約から経緯を rationale へ移す是正）の作業中に見つけた隣接指摘。Issue #562 のスコープそのものではない。

**指摘**: `doc-system-v2/nodes/05-design/prompt/` の PROMPT ノード **22 件すべて**が、本文の「実体」を PF（プラットフォーム）の wrapper ファイルとして記述している。共通本文の SoT である `.ai/skills/<name>/SKILL.md`／`.ai/agents/<name>.md` を指すノードは **0 件**である。Issue #406 の `.ai/` 移行が、在グラフの設計ノードに反映されていない。

## 実測（2026-09-29）

| 区分 | 件数 | 本文の「実体」 | 実際の中身 |
|---|---|---|---|
| skill 軸 PROMPT（`carrier: "skill"`・SPEC-61 系） | 13 | `.claude/skills/<name>/SKILL.md` | 「共通本文は `../../../.ai/skills/<name>/SKILL.md` にあります。必ず読み…」だけを持つ Claude wrapper |
| skill 軸 PROMPT `docidx` | 1 | `.agents/skills/docidx/SKILL.md` | 同じく `.ai/skills/docidx/SKILL.md` を指す Codex wrapper |
| 著作エージェント PROMPT（`carrier` なし・SPEC-27 系） | 7 | `.claude/agents/<name>.md`（`requirements`／`spec`／`analysis`／`design`／`verification-author`・`reconciliation`・`reconciliation-validator`） | frontmatter（tools/model）と `.ai/agents/<name>.md` への参照だけを持つ Claude wrapper |
| agent 軸 PROMPT `doc-system-config-operator`（`carrier: "agent"`） | 1 | `.codex/agents/doc-system-config-operator.toml`（補助手順＝`.agents/skills/doc-system-config/SKILL.md`） | toml は `./.ai/agents/doc-system-config-operator.md` を指す Codex wrapper。補助手順の `.agents/skills/doc-system-config/SKILL.md` は本文そのもので、`.ai/` に対応物は無い |

- 22 件に対応する共通本文（`.ai/skills/` 14 件・`.ai/agents/` 8 件）は、すべて実在することを確認した。
- `doc-system-v2/nodes/05-design/prompt/` を `\.ai/` で grep した結果は 0 件である。
- 呼び出し元の事前確認では「20 件」だった。20 件は `.claude/` を指すノードの数である。本 FND では、`.agents/`（Codex の skill 入口）と `.codex/`（Codex の agent TOML）という別の PF wrapper を指す 2 件も同じ欠陥として含めた。指し先の PF が違うだけで、「共通本文ではなく PF 入口を実体と呼んでいる」点は同じだからである。

`.ai/README.md` と `.ai/rationale/README.md` は、Issue #406 の方針として次の 2 点を定めている。

- 共通本文の SoT は `.ai/skills/`・`.ai/agents/` である。
- PF wrapper（`.claude/skills/*/SKILL.md`・`.claude/agents/*.md` 等）は「Claude 固有 metadata・実行契約と共通 SoT への参照」を持つだけで、「共通本文の編集正本ではない」。

PROMPT ノードの「実体」の記述は、この定義と正面から食い違っている。

## 意図的設計かの確認（`.claude/rules/01-principles.md`「意図的設計の尊重」）

「実体＝PF wrapper」は意図的な設計ではない、と判断した。根拠は次の 3 点である。

1. PROMPT ノード 22 件のうち著作エージェント系の 7 件は SPEC-27 系、skill 系 14 件は DD-22（2026-07-01）を受けた著作である。いずれも、Issue #406 の `.ai/` 移行より前に初版が書かれたとみられる（Issue #406 は Issue #372 より後の番号）。初版の著作時点では、`.claude/**` が共通本文そのものだった。その後に z バンプされたノード（例: `design-author` v0.2.4）もあるが、それらの改訂で「実体」の記述が見直された形跡は無い（22 件とも `.ai/` を含まない）。
2. コーパス内で `#406`・`#407`・`.ai/` を grep したところ、ヒットは既存の open FND（`dsv2-lookup.md-の手順に統制下で必ず-deny-される-python3-c-例が残っている`）1 件だけだった。「PROMPT ノードは PF の入口を実体として指し続ける」と決めた DD・Q・FND は存在しない。
3. DD-22 は PROMPT ノードの `carrier`（skill／agent）を「届け方」と定義している。しかし、どのファイルを「実体」と呼ぶかは定めていない。DD-22 本文の「覆る場合の影響範囲」や後続作業の記述は、`.claude/` を実体の置き場として扱っている。ただしこれは当時の事実を書いたもので、`.ai/` 分離を想定して選んだ結果ではない。

したがって、これは覆すべき根拠が必要な既存決定ではなく、移行時の未追随（見落とし）として扱う。

## 深刻度の判定根拠（実害で判定する）

**WARNING** と判定した。

- **ERROR にしない理由**: 回復不能な損失も、live な RULE 違反も無い。wrapper は実在し、共通本文へのリンクを 1 本持っている。そのため、PROMPT ノードから wrapper を経由すれば 1 ホップで共通本文に着く。`prompt-coverage`（RULE-032）は id の接頭辞しか見ず、`drift`（RULE-004）は担体を見ないので、どちらも鳴らない。価値経路も遮断されていない。
- **INFO にしない理由**: 在グラフの設計を字義どおりに読んで作業すると、誤った成果物が出る経路が正規の手順上にある。PROMPT ノードを設計上の正本として読み、「実体」に書かれたファイルを直せば、編集は wrapper に入る。これは `.ai/README.md` の「共通本文を PF ごとに複製しない」「wrapper は編集正本ではない」に反する。FND-99／FND-104／FND-106 が WARNING とされたのと同じ類型（文書の指示に literal に従うと誤る）である。
  - 補足: この経路は抽象的なものではない。Issue #562 は含有ハーネス 22 件の担体を一斉に書き換える作業であり、PROMPT ノードと担体の照合が現に予定されている（係属中の Q 素案 `含有ハーネスの担体から経緯を-rationale-へ移す基準と-prompt-ノードとの-ssot` の論点 A ②）。
- **トレーサビリティの損害**: implementation 段で発火する `PROMPT←SRC`（DD-9：プロンプト資産は実装で実現される）は、SRC ノードの張り先が「実体」の記述に左右される。wrapper を実体とみなしたまま SRC を張ると、「実装＝共通本文」という Issue #406 の構図と在グラフが食い違う。これは将来のリスクであり、現時点の損害ではない。WARNING の根拠としては補助的に扱う。

## 選択肢（排他）

**選択肢 1: 「実体」を共通本文に書き換え、PF の入口は別の語で併記する。**

- 例: 「実体（共通本文）＝`.ai/skills/align/SKILL.md`。PF 入口＝`.claude/skills/align/SKILL.md` ほか（4 ツリーの対応は `asset_parity` が管理）」。
- 22 件とも本文の 1 文を直すだけで、辺も役割契約も変わらない。
- **利点**: Issue #406 の SoT 定義と在グラフが一致する。PF が増えたり減ったりしても、実体の記述は変わらない。
- **欠点**: 22 ノードの改版が要る。版区分の判断は下記「版の扱い」を参照。

**選択肢 2: 「実体」を共通本文だけに書き換え、PF 入口には触れない。**

- **利点**: 記述は最短になる。PF 入口の一覧は `asset_parity` と `.ai/Individually-managed-lists.md` がすでに持っているので、二重管理にならない。
- **欠点**: `carrier: "skill"` の「slash command として起動される」という届け方が、どのファイルで実現されるのかを在グラフからは辿れなくなる。

**選択肢 3: 現状を維持し、「PROMPT ノードの実体＝Claude（主 PF）の入口」と定義する DD を起こす。**

- **利点**: ノードの改版は不要になる。
- **欠点**: `.ai/README.md` の「wrapper は編集正本ではない」と在グラフの定義が逆向きになり、同じ語「実体」が文書間で別物を指す。さらに、`docidx`（`.agents/`）と `doc-system-config-operator`（`.codex/`）はすでに Claude 以外の入口を指しているので、「主 PF の入口」という定義にも合わない。

## 推奨（決定ではない。決定はオーナーが行う）

**選択肢 1 を推奨する。** 根拠は 3 点である。

1. 選択肢 1 は Issue #406 で決まった SoT の定義を在グラフへ写すだけで、新しい設計判断を持ち込まない。選択肢 3 は、書かれていない定義を後から作って食い違いを正当化することになる。しかも 22 件中 2 件にはその定義も当てはまらない。
2. 選択肢 1 と選択肢 2 の差は、PF 入口を併記するかどうかだけである。`carrier` が「届け方」を表す属性である以上、届け方が物理的にどこで実現されるかを 1 文残しておくと、DD-9 の `PROMPT←SRC` を張るときに迷わなくなる。
3. Issue #562 は、22 件の担体をすべて触るバッチである。照合のコストが最も安いのは今である。

**版の扱い（要判断・Q 素案と連動）**: DD-8 §4 に照らすと、辺も役割契約も変わらない本文の 1 文修正は **z バンプ**に当たる。一方、DD-22 の版方針は「キャリア／本文変更＝MINOR」と書いており、この「本文」が PROMPT ノードの本文を指すのかどうかは未決である（Q 素案 `含有ハーネスの担体から経緯を-rationale-へ移す基準と-prompt-ノードとの-ssot` の観測 7）。

- MINOR を採った場合、`reconciliation`・`verification-author`・`reconciliation-validator` の PROMPT ノードに入辺を持つ open FND の 7 辺が drift する。
- そのため、版区分は Q 素案の決定に従わせ、本 FND の処置は Q の決定と同じバッチで行うことを推奨する。

「対応不要」との判断はしていない。採否と実施時期はオーナーが決める（`scheduled: sprint-1`＝現行スプリント。繰り越しはオーナーの明示指示がある場合に限る）。

## 本指摘の対象外（留保）

- **PROMPT ノードの規範内容**が担体とずれている件は、指し先の件とは別の指摘として扱った（別 FND `パイプライン-skill-の-prompt-ノード-3-件が担体改訂と-dd-22-に未追随`、および既存 open FND `reconciliation-の-tmp-掃除ガードが-in-graph-prompt-と-copilot・codex-ミラーに未同期`）。本 FND は「どのファイルを実体と呼ぶか」だけを扱う。PR1 に従い、指摘対象の「もの」が違うので分けた。
- **PROMPT ノードを持たない含有ハーネス**（`spec-inspector`・`structured-analysis`・`dsv2-lookup`・`authoring-fanout`・`doc-system-v2-authoring`）の在グラフ化の要否は、本 FND では扱わない（Q 素案の観測 1）。
- 既存 open FND `reconciliation-の-tmp-掃除ガードが-…` の本文は、`.claude/agents/reconciliation.md` を「正本・実体」と記述している。これは同 FND の起票時点（2026-08-04）の事実の記録であり、本 FND の処置で書き換える対象ではない（PR8 区分 1）。

## 辺の張り先と選定理由

指摘対象の PROMPT ノード 22 件のそれぞれに forward 辺を張った。親 SPEC（SPEC-61 傘・SPEC-27）で代表させなかったのは、欠陥が個々の PROMPT ノードの本文にあり、解消時の `dsv2 reverse` によるバックリファレンスを処置した各ノードに付与する必要があるからである。処置対象の slug は、次の「指摘時 ref_version」の列挙と同じ 22 件である。

**接続規則変更の伴否**: 本指摘は `doc-system-v2/config.yml` の `must_link_to`／`must_be_linked_from`／`fnd_lifecycle` を追加・変更・削除しない（対象は PROMPT ノード本文の記述）。したがって、接続マトリクス・ドキュメント一覧・author 資産への伝播チェックは不要と判断した。

**対応状況**: open

**指摘時 ref_version**: （いずれも同 `.yaml` の version 時点）
- `align-認識合わせスキルプロンプト-着手前の段取り` "0.1"（v0.1.0）
- `value-trace-価値経路トレースskillプロンプト-イベント総点検` "0.1"（v0.1.0）
- `mvp-scope-価値ベースmvpスコープskillプロンプト` "0.1"（v0.1.0）
- `schema-design-スキーマ設計skillプロンプト-読み手から決める` "0.1"（v0.1.0）
- `domain-model-ドメインモデル設計skillプロンプト-データ辞書→型安全なクラス` "0.1"（v0.1.1）
- `architecture-design-アーキテクチャ設計skillプロンプト-論理dfd→物理モジュール-依存・if・プ` "0.1"（v0.1.1）
- `orchestration-design-オーケストレーション設計skillプロンプト-制御フロー・fail-close・ログ-版` "0.1"（v0.1.1）
- `prompt-design-プロンプト設計skillプロンプト-llmへの問い方を固める` "0.1"（v0.1.0）
- `test-strategy-テスト戦略skillプロンプト-review-system-テーラリング済` "0.1"（v0.1.2）
- `spec-principles-仕様設計・点検の原則skillプロンプト-pr1–pr10` "0.1"（v0.1.0）
- `spec-pipeline-仕様設計パイプラインskillプロンプト-オーケストレータ` "0.1"（v0.1.0）
- `impl-design-pipeline-実装設計パイプラインskillプロンプト-凍結セット化` "0.1"（v0.1.0）
- `asset-pipeline-資産化パイプラインskillプロンプト-method→skill-agent` "0.1"（v0.1.0）
- `docidx-ノード検索skillプロンプト-v1-v2照会境界` "0.1"（v0.1.1）
- `requirements-author-著作支援プロンプト-val-sr-fr-nfr` "0.2"（v0.2.3）
- `spec-author-著作支援プロンプト-spec・1アサーション1ノード` "0.2"（v0.2.3）
- `analysis-author-著作支援プロンプト-actor-i-o-d-p-e` "0.1"（v0.1.3）
- `design-author-著作支援プロンプト-orc-ds-mod-dm-port-prs-scm-cfg-prompt-term` "0.2"（v0.2.4）
- `verification-author-著作支援プロンプト-td-tc-tr-verify-fnd-dd-q-pend` "0.2"（v0.2.3）
- `reconciliation-調停支援プロンプト-検証＋本ファイル転記` "0.1"（v0.1.2）
- `reconciliation-validator-検証支援プロンプト-read-only-構造検証・validation_ok-rollback` "0.2"（v0.2.2）
- `doc-system-config-operator-doc-system-config-操作エージェントプロンプト` "0.1"（v0.1.0）

`.ai/**`・`.claude/**`・`.agents/**`・`.codex/**` は out-of-graph で版を持たない（DD-8／FND-104）ので、所在をパスで本文に記録するにとどめる。
