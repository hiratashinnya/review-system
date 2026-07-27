**改訂理由（v0.1.0 → v0.2.0・2026-07-26・PR #257 の Codex AI agent 再レビュー指摘）**: 「原則との突き合わせ」節が「7件のERRORはノード側の欠落ではなく規則側の粒度不足である」と一括で総括していたが、これは後段の選択肢②③・段階案（傘2件は既存の子SCM辺で規則修正のみで解消する一方、成果物5件はO/I→SCM辺が1本も存在せず新規著作を要する）と矛盾していた。本改訂で総括を「傘2件＝true false positive／成果物5件＝規則修正後も辺の実著作を要する」と区別する記述に是正する。内容変更のため MINOR バンプ。

**深刻度**: ERROR（`severity: error` × `activate_stage: design` で**現在発火中**。live 違反 7 件が検証ゲートを常時赤にしており、他の設計段 ERROR の検出を埋没させる）

**対応 Issue**: #253（必須辺検証ルールの見直し・修正 ① `scm←cfg`）

## 内容

`must_be_linked_from` の規則
`{ node: scm, source: [cfg], activate_stage: design, severity: error, reason: "スキーマは設定インスタンスで具体化される（SCM←CFG・DD-9）" }`
は SCM 型 11 件を一律に「CFG から入辺を受けること」で判定する。しかし SCM 11 件の入辺を全数照合すると、**下流連続性の担い手が異なる 3 つの部分集団**に分かれており、規則が想定しているのは第1集団だけである。

| 部分集団 | 件数 | 実際の下流連続性の担い手 | 現状の入辺 | 判定 |
|---|---|---|---|---|
| config スキーマ | 4 | CFG インスタンスが具体化 | CFG 14 件から被参照あり | PASS |
| 成果物スキーマ | 5 | O/I の実インスタンスが適合 | 入辺なし | **ERROR** |
| 傘スキーマ | 2 | 子 SCM が詳細化 | 子 SCM から入辺あり | **ERROR** |

- config スキーマ 4 件: `config.yaml-スキーマ` / `ステージ／語彙／カバレッジ／スコープスキーマ` / `ライフサイクル／決定スパインスキーマ` / `接続ルールスキーマ`
- 成果物スキーマ 5 件: `rule-違反レポート行形式` / `カバレッジ結果形式` / `ノード-yaml-ブロックスキーマ` / `ノードファイル記法スキーマ` / `キャリア属性-carrier-スキーマ`
- 傘スキーマ 2 件: `出力フォーマットスキーマ` / `ノードフォーマットスキーマ`
- 実在する SCM→SCM 詳細化辺（4 本）: `rule-違反レポート行形式 → 出力フォーマットスキーマ` / `カバレッジ結果形式 → 出力フォーマットスキーマ` / `ノード-yaml-ブロックスキーマ → ノードフォーマットスキーマ` / `ノードファイル記法スキーマ → ノードフォーマットスキーマ`

**原則との突き合わせ**: 成果物スキーマ・傘スキーマは「CFG で具体化されない」のであって「下流が無い」わけではない。規則が要求する具体化元（CFG のみ）が3部分集団の実態（CFG／O・I／子 SCM）を反映していない点は**規則側の粒度不足**である（PR1「もの＋発生源で分ける」——同じ SCM 型でも具体化元が CFG／O・I／子 SCM と異なるものを 1 規則に束ねている）。**ただし規則を直すだけで7件全てが解消するわけではない**——傘 2 件は既存の子 SCM 辺で規則修正のみで解消する true false positive だが、成果物 5 件は O/I→SCM の辺そのものが現状 1 本も存在せず、規則側に `must_link_to: o|i→scm` を追加しても対応する辺の新規著作を要する実際のグラフ未充足である（詳細は下記選択肢③・段階案）。この状態を放置すると、規則を満たすためだけの意味のない CFG 辺を張る誘因が生まれ、DD-9 が守ろうとした価値経路の下流連続性の保証（PR6）がむしろ形骸化する。

**先例（同型の構図）**: `spec←td` は傘 SPEC 54 件を `applies_when: condition_present` で除外済み（`dsv2/query.py` の `find_missing_inbound()` に実装あり）。すなわち「型は同じだが部分集団で必須辺が異なる」問題は既に限定子機構で解いた前例がある。また `doc-system-v2/schema/sidecar.schema.json` は `carrier` enum（`[skill, agent, command, instructions, hooks, code]`）を「設計要素の実現担体」として持ち、PROMPT 15 件で運用されている＝**サイドカー属性で部分集団を宣言する先例**も存在する。

## 選択肢

**① 傘・成果物を除外する限定子を足す（規則1本のまま）**
`scm←cfg` に `applies_when` を付け、傘（子 SCM から入辺を受けるもの）と成果物を対象外にする。
- 長所: 変更が config.yml と施行器の限定子 1 種で済み、ERROR 7 件を最短で解消。
- 短所: 除外した 5 件＋2 件の下流連続性が**無検査**になる（DD-9 の意図を部分的に放棄）。また「傘か否か」を入辺の有無で判定すると自己言及的（入辺が無い成果物と区別できない）ため、結局判別子が必要になる。

**② `source` を OR 拡張する（`source: [cfg, scm, o, i]`）**
- 長所: config.yml 1 行の変更のみ。傘 2 件は既存の子 SCM 辺で即 PASS。
- 短所: OR は最弱リンクで通るため、config スキーマが SCM 辺 1 本だけで誤充足する**ループホール**を作る（`SPEC→[FR, NFR, SPEC]` の OR で既に同型の指摘＝FND「config の `SPEC→[FR, NFR, SPEC]` OR 規則のループホール」がある）。さらに成果物 5 件は O/I→SCM 辺が 1 本も無く `must_link_to` 側にも `o|i → scm` 規則が無いため、拡張しても ERROR は解消しない。

**③ SCM に部分集団の判別子を持たせ、規則を 3 本に分割する**
サイドカースキーマに `carrier` と同型の enum（例: `schema_kind: [config, artifact, umbrella]`）を追加し、`applies_when` で規則を分ける。
- `{ node: scm, source: [cfg], applies_when: schema_kind=config, severity: error }`
- `{ node: scm, source: [o, i], applies_when: schema_kind=artifact, severity: error }`（対称に `must_link_to` へ `o|i → scm` を追加し、成果物 5 件に O/I からの適合辺を著作する）
- `{ node: scm, source: [scm], applies_when: schema_kind=umbrella, severity: error }`（傘は子 SCM の詳細化辺で充足＝既存 4 辺で PASS）
- 長所: 3 集団それぞれの下流連続性を**別々に**機械保証でき、DD-9 の意図を落とさない。判別子はサイドカーの明示属性なので観測可能（PR4）で、限定子の自己言及も起きない。`carrier` という先例があり、スキーマ拡張の型も既知。
- 短所: 変更点が最も多い（sidecar.schema.json ＋ SCM 11 件のサイドカー ＋ config.yml 3 行 ＋ 施行器の `applies_when` 汎化 ＋ `must_link_to` 対称化 ＋ O/I→SCM 辺の著作）。`applies_when` を現行の固定値 `condition_present` から `key=value` 形式へ一般化する必要がある。

**④ `severity` を warning へ降格する**
- 長所: 即座にゲートが通る。
- 短所: 判定基準を変えずに閾値だけ下げるもので、規則の粒度不足という原因は残る（PR2「機械判定と運用ルールを混ぜない」に照らして、機械判定として正しくない規則を弱い機械判定として残すのは筋が悪い）。恒久策にはならない。

## 推奨

**③ を本線とする。**理由は 3 集団の「具体化元」がそれぞれ別のものであり、規則を分けることが PR1 に沿う唯一の案であること、および ①②④ がいずれも下流連続性の保証を弱める（＝DD-9 を後退させる）ためである。

sprint-1 の工数が③の全量を吸収できない場合の**段階案**（いずれもオーナー判断を仰ぐ）:

- **段階 A（判別子の導入まで）**: `schema_kind` をサイドカーに追加し、施行器の `applies_when` を `key=value` へ一般化。傘規則（`scm←scm`）まで入れれば傘 2 件の ERROR は解消し、既存 4 辺で PASS する。
- **段階 B（成果物の下流著作）**: `must_link_to` へ `o|i → scm` を追加し、成果物 5 件に O/I からの適合辺を著作。ここまでで live ERROR 7 件が解消する。
- 段階 B を後続スプリントへ回す場合でも、`schema_kind=artifact` の規則を**削除するのではなく** `severity: warning` で暫定運用し、恒久的に error へ戻す前提を config.yml のコメントに残すことを推奨する（消さない＝PR8）。

段階分割・実施スプリントの決定は**オーナー判断**を仰ぐ（本 FND は `scheduled: "sprint-1"`＝既定のまま。繰り越しは独断で行わない）。

## 接続規則変更の伝播チェック

本 FND は `must_be_linked_from`（および ③ 採択時は `must_link_to`）の**接続規則変更を提案する**ものだが、**起票時点では `doc-system-v2/config.yml` を変更していない**ため、著作資産への同期は行っていない（同期不要と判断した根拠＝規則そのものが未変更）。処置（規則変更）を実施する時点で、以下の out-of-graph 資産を必ず同期すること:

- `docs/doc-system/03-connection-matrix.md`（L47-48 の mermaid `SCM --> SPEC` / `CFG --> SCM`、L93-94 の接続要否マトリクス行、L182 の依存先表）
- `docs/doc-system/01-document-items.md`（SCM / CFG / O / I の上流参照列）
- `.claude/agents/design-author.md` ＋ `.github/agents/design-author.agent.md`（L73-74 の SCM / CFG 必須辺表。③ 採択時は `schema_kind` の記載も追加）
- `.claude/agents/analysis-author.md` ＋ `.github/agents/analysis-author.agent.md`（③ で `o|i → scm` を追加する場合の O / I 必須辺）
- `.claude/skills/architecture-design/SKILL.md`（SCM / CFG の接続記述）
- `doc-system-v2/schema/sidecar.schema.json`（③ 採択時の `schema_kind` enum 追加）

**指摘時 ref_version**: must_be_linked_from "0.1"（must_be_linked_from.yaml v0.1.1 時点）
