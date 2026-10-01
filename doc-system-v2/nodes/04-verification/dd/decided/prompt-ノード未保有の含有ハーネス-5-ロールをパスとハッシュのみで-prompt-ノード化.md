**status: decided**（オーナー指示・実施 sprint-1）

**決定の出所**: 決定者＝オーナー／日付＝2026-09-30〜2026-10-01（DD `prompt-ノードは担体のパスとハッシュだけを持ち-ssot-は担体とする-q-より昇格` と同じ一連のやり取り。日付の内訳は伝えられていない）／根拠の所在＝チャット（in-repo 痕跡なし。主文脈が本著作に伝えた）。書式は open Q `オーナー決定の出所表記を-in-repo-でどこまで検証可能にするか` の推奨（選択肢 3）に合わせた。同 Q の決定は先取りしない。

> **本 DD の位置づけ**: 昇格元の Q を持たない独立した DD である。論点の出所は、Q `含有ハーネスの担体から経緯を-rationale-へ移す基準と-prompt-ノードとの-ssot` の観測 1 にある。同 Q は「これらを在グラフに載せるかどうかは本 Q では扱わない」としていた。オーナーは、同 Q を昇格させた DD（上記。以下「方針 DD」）の適用範囲（現在の PROMPT ノード 22 件）とは**別に決める**よう指示した。そのため、本 DD を別に起票する。
> **辺の扱い**: 2 本張る。(1) 方針 DD への参照辺。本 DD は方針 DD の方針（パスとハッシュだけ）に依拠する。方針 DD に対する反映義務を表す辺ではない（先例＝DD `suppress機構の廃止によりdd-2-verifyのrule-004免除-を破棄` の DD→DD 辺）。(2) open FND `dsv2-lookup.md-の手順に統制下で必ず-deny-される-python3-c-例が残っている` への義務辺。本 DD を反映すると、同 FND が張れずにいた forward 辺の張り先が生まれる（後述）。反映先の大部分（新しい PROMPT ノード 5 件）はまだ存在しないので、辺を張れない。
> **指摘時 ref_version**: 本 DD は FND ではないので、DD-3 制度上の記録は要らない。参照先の version は末尾に記録する。

## 論点

`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」は、doc_system／review_system に含有されるハーネスとして著作・検証エージェント 12 件を列挙している。そのうち 7 件（`*-author` 5 件・`reconciliation`・`reconciliation-validator`）は PROMPT ノードを持つが、次の **5 件**は持たない。
- `spec-inspector`
- `structured-analysis`
- `dsv2-lookup`
- `authoring-fanout`
- `doc-system-v2-authoring`（著作エージェント共通契約）

この 5 件の担体を変えても、在グラフに受け皿が無い。担体に対する指摘を FND として起票しても、forward 辺を張れない。これは現に起きている。open FND `dsv2-lookup.md-の手順に統制下で必ず-deny-される-python3-c-例が残っている` は `edges: []` のままであり、同 FND 自身が「辺の欠落は張り先が実在しないことによる」と記録している。

## 決定（オーナー指示・内容を改変せずに記録する）

- PROMPT ノードを持たない含有ハーネスのロール 5 件（`spec-inspector`・`structured-analysis`・`dsv2-lookup`・`authoring-fanout`・`doc-system-v2-authoring`＝著作エージェント共通契約）を、方針 DD の方針（**パスとハッシュだけ**）に沿って PROMPT ノード化する。
- これは方針 DD の適用範囲（現在の PROMPT ノード 22 件）とは別に決める。
- 実際のノード作成は別作業で行う。本 DD は決定の記録にとどめる。

## 本 DD の整理（著作者による分析であり、決定の追加ではない）

### 現状（2026-10-01 確認）

- 5 件とも、共通本文 `.ai/agents/<name>.md` が実在する。
- rationale は 3 件（`authoring-fanout`・`doc-system-v2-authoring`・`dsv2-lookup`）が `.ai/rationale/<name>.md` に分離済みで、共通本文から rationale へのリンクを持っている。`spec-inspector`・`structured-analysis` には rationale ファイルが無い。
- PROMPT 型を選ぶこと自体は、オーナー指示で決まっている（本 DD では問い直さない）。

### 未決事項（決定に含まれていないもの。推測で埋めない）

- **N1 各ロールの親 SPEC／FR 軸**: 既存の軸は 2 本ある。
  - 著作エージェント軸: SPEC-27 `著作エージェントが外部参照なしに著作規約を提供`→FR-13 `著作エージェントと層ワークフロー`。PROMPT-1〜7 がこの軸に属する。
  - skill 軸: 傘 SPEC-61 `対象-skill-の-llm-プロンプト資産を設計層-prompt-ノードで在グラフモデル化`→FR-17。`prompt_coverage_targets` の 14 skill がこの軸に属し、`carrier` は skill か agent。

  5 件をどちらに置くか、あるいは新しい軸が要るかは決まっていない。判断材料として観測できる事実は次のとおり（帰属の推定ではない）。
  - `spec-inspector` は点検主体であり、ORC-1（inspector のオーケストレーション）と関係する。
  - `authoring-fanout` は DD-22 ①-C の「非対話の fan-out の orchestrator agent 化」の実体であり、ORC-2（著作パイプラインのオーケストレーション）と関係する。
  - `dsv2-lookup` はノードの検索・読み込みを担う。同じく検索を担う skill の `docidx` は、DD-22 で「retrieval が VAL-1 を支援する」として skill 軸に既定 IN とされた。
  - `doc-system-v2-authoring` は、著作エージェントが「必ず読む」共通契約である。SPEC-27 の「外部参照なしに」と同型の緊張を抱えている（方針 DD「既存 FND との関係」の末項）。
  - `structured-analysis` は DFD 分解を担う。

  新しい FR／SPEC が要ることになれば、要件層の追加になる。要件定義フェーズの規律（`.claude/rules/02-decision-process.md`「判断の仰ぎ方」）に従い、暫定では進めない。
- **N2 `carrier` の値**: `spec-inspector`・`structured-analysis`・`dsv2-lookup`・`authoring-fanout` はサブエージェントとして起動される。一方、`doc-system-v2-authoring` は単独では起動されず、各 author が読み込む契約である。`schema/sidecar.schema.json` の enum（`skill`/`agent`/`command`/`instructions`/`hooks`/`code`）のうちどれを当てるか、あるいは `carrier` を持たせないか（著作エージェント PROMPT 7 件は `carrier` を持たない先例）は決まっていない。なお、skill 軸に置くと、SPEC-61-3 が `carrier` に skill か agent を要求する。
- **N3 `prompt_coverage_targets`（RULE-032）に加えるか**: 現在の対象は 14 skill だけである。`prompt_coverage_gaps()` は、`carrier ∈ {skill, agent}` のノードの id が `"{name}-"` で始まるかどうかで被覆を判定する。5 件を加えるには `doc-system-v2/config.yml` の変更が要る。加えるかどうかは決まっていない。加えない場合、5 件のノードが後で消えても機械検査では検出されない。
- **N4 どのファイルのパスを持つか**: 方針 DD の未決事項 U2 と同じ論点である（共通本文か、PF wrapper か、両方か）。open FND `prompt-ノード-22-件の実体が-pf-wrapper-を指し共通本文を指さない` の決定に揃える。
- **N5 B-2（担体から rationale へリンクしない）を 5 件にも当てるか**: 方針 DD の決定 4 は、適用範囲が 22 件に限られている（同 DD 決定 6）。上記の 3 件は現に rationale へのリンクを持っている。本 DD で PROMPT ノード化するときに同じ扱いにするかどうかは、指示に含まれていない。
- **N6 実施の順序**: 推奨は、方針 DD の未決事項 U1〜U3（ハッシュの置き場・パス・算法）が決まってから、22 件の書き換えと同じバッチで 5 件を作成することである。先に作ると、ノードの書式を後でもう一度改めることになる。
- **N7 slug の命名**: N3 で `prompt_coverage_targets` に加える場合、slug を `"{name}-"` で始める必要がある（RULE-032 の判定方式）。加えない場合でも、既存 22 件の命名に揃えることを推奨する。

### 既存ノードとの関係

- **FND `dsv2-lookup.md-の手順に統制下で必ず-deny-される-python3-c-例が残っている`**: 本 DD は、同 FND の選択肢 ① のうち「`dsv2-lookup` の PROMPT ノードを在グラフ化する」部分を、オーナーの決定として確定させる。同 FND は、この部分について「`prompt_coverage_targets` の対象集合に触れる別の決定であり、AI が確定させるべきではない」として判断を留保していた。本 DD がその別の決定に当たる（ただし N3 の対象集合は未決のまま）。同 FND の本体（`.ai/agents/dsv2-lookup.md` の `python3 -c` 例の差し替え）は、本 DD では決めない。`dsv2-lookup` の PROMPT ノードができれば、同 FND は forward 辺を張れるようになり、解消時に `dsv2 reverse` を機械的に実行できるようになる。
- **DD-22**: DD-22 の対象範囲（skill 13 件と docidx）と、著作エージェント PROMPT-1〜7 の扱いは変えない。5 件の帰属先（N1）が決まるまで、既存の軸ノードに義務辺は張らない。

## 影響範囲（反映はまだ済んでいない。別作業・sprint-1）

| 反映先 | 反映内容 | 状態 |
|---|---|---|
| 新しい PROMPT ノード 5 件（`doc-system-v2/nodes/05-design/prompt/`） | `design-author` が著作し、`reconciliation-validator`→`reconciliation` の 2 段で確定する。本文は方針 DD に従い、パスとハッシュだけにする。親辺は N1、`carrier` は N2 に従う。各ノードから `→本 DD` の backref を張る | 未反映（N1・N2・N4・N6 待ち） |
| FND `dsv2-lookup.md-の手順に…` | `dsv2-lookup` の PROMPT ノードへの forward 辺を張る（open のまま）。反映が済んだら、本 DD の義務辺を FND→本 DD の参照に置き換えるか、削除する | 未反映 |
| `doc-system-v2/config.yml` の `prompt_coverage_targets` | N3 で加えると決めた場合に限り、追加する | 未決（N3） |
| 親の軸ノード（SPEC-27／SPEC-61／新設） | N1 が決まったら、必要な改版や新設を行う | 未決（N1） |

## 接続規則変更チェック（FND-99 パターン）

本 DD は、`doc-system-v2/config.yml` の `must_link_to`／`must_be_linked_from`／`fnd_lifecycle`／`decision_spine` のどれも追加・変更・削除しない。新しい PROMPT ノードには既存の `PROMPT→SPEC` 規則がそのまま適用されるので、規則そのものは変わらない。したがって、接続マトリクスとドキュメント一覧への伝播は**不要**と判断した。`prompt_coverage_targets`（N3）は接続規則ではないので、変更する場合は本チェックとは別に、`dsv2 prompt-coverage` の結果と `.claude/rules/02-decision-process.md` の含有ハーネス列挙との整合を確認する。

## 覆る場合の影響範囲

本決定を覆す場合（5 件を在グラフに載せない場合）は、作成済みの PROMPT ノードを撤去し、`prompt_coverage_targets` に加えていればそれも戻す。FND `dsv2-lookup.md-の手順に…` は、forward 辺の張り先を失う。そのため、同 FND の選択肢 ② の扱い（本文に「付与先なし」と書いて backref の代わりにする）に戻る。影響は、新設分と同 FND にとどまる。

## 辺の参照時 version（本 DD 著作時点）

- `prompt-ノードは担体のパスとハッシュだけを持ち-ssot-は担体とする-q-より昇格` "0.1"（v0.1.0・同一バッチで新規著作）
- `dsv2-lookup.md-の手順に統制下で必ず-deny-される-python3-c-例が残っている` "0.1"（v0.1.0）

本文で参照しただけのノード: `著作エージェントが外部参照なしに著作規約を提供` v0.3.0／`対象-skill-の-llm-プロンプト資産を設計層-prompt-ノードで在グラフモデル化` v0.1.1／`各-skill-prompt-ノードがキャリア属性-skill｜agent-を持つ` v0.1.0／`doc-system-設計層モデリングの-skill-展開方針を確定-q-6-から昇格・①-c-ハイブリッド／②-a` v0.1.0。`.ai/**`・`.claude/**` は out-of-graph で版を持たない（DD-8／FND-104）。
