**深刻度**: ERROR（`activate_stage: design` かつ現 `current_stage: design` のため**発火中**。`p←mod` の live ERROR は **42 件**で、`python3 doc-system-v2/validate.py` の ERROR 53 件の大半を占める最大の塊）

**対応 Issue**: #254（必須辺検証ルールの見直し・修正 ② `p←mod`）

**内容（1アサーション）**: `must_be_linked_from` の `{ node: p, source: [mod] }` は **P 型の全ノード**（子 P を持つ傘＝non-leaf P を含む）に実装モジュールの入辺を要求しており、暗黙に「1 プロセス = 1 モジュール」を仮定している。しかし MOD 側の粒度は DD-13「MOD 粒度の選択」（`mod-粒度の選択` v0.3.0・選択肢C）が **混合粒度**（「孫プロセス（L3 以深）あり OR 責務が明確に別 → L2 単位で分割。孫なし＋同一責務圏 → L1 維持」）で確定済みであり、規則の仮定と設計決定が両立しない。

**観測事実**:

- 規則（`must_be_linked_from`・`doc-system-v2/config.yml` L139）:
  `{ node: p, source: [mod], activate_stage: design, severity: error, reason: "プロセスは実装モジュールを持つ（P←MOD・DD-9）" }`
  対象の絞り込み子（`applies_when`）を持たないため、P 型の 56 件すべてが判定対象になる。
- DD-13（v0.3.0・2026-06-17 改訂）は **選択肢A「L2/L3 リーフ全単位（34+ モジュール）」を明示的に却下**し、選択肢C（中間粒度）を採用している。却下理由は「リーフ全 1:1 はモジュールが爆発して管理不能」。想定 MOD 総数は 12 → 18。
- 実測（`doc-system-v2/meta.json` の P→P 親辺で全数判定）:

  | 区分 | 件数 | うち MOD 保有 |
  |---|---|---|
  | P 総数 | 56 | 14 |
  | **leaf P**（子 P なし） | **41** | **2**（`抑制・発火フィルタ` / `検査ビュー射影`） |
  | non-leaf P（傘） | 15 | **12** |

- MOD を持つ non-leaf P 12 件の子数: `ノード受付・パース` 6、`rule-検査` 配下の各 L2 が 2〜4 など。
- MOD を持たない non-leaf P 3 件: `rule-検査`（子 5）／`カバレッジ点検`（子 2）／`ノード著作・反映プロセス`（子 2）。
- **SPEC との同型性**（実測）:

  | 型 | 総数 | 傘 | leaf | 現行の leaf 限定規則 |
  |---|---|---|---|---|
  | SPEC | 240 | 54 | **186** | `spec←td` の `applies_when: condition_present` |
  | P | 56 | 15 | **41** | なし |

  SPEC の `condition` 保有 186 件と leaf 186 件は**完全一致**しており、`condition_present` は実質 leaf 判定として機能している。すなわち「傘には下流実体を要求せず leaf にのみ要求する」構造は SPEC 側に既存であり、P 側だけがその機構を欠いている。
- 実装箇所: `applies_when: condition_present` は `dsv2/query.py` の `must_be_linked_from_gaps()` に `rule.get("applies_when") == "condition_present"`（L152）としてハードコードされている。
- 参考実測（**採用方向ではない**・比較材料として記録）: 推移的被覆（祖先/子孫の MOD で被覆とみなす）を仮に適用すると、42 件中 37 件が祖先 P 経由・3 件が子孫 MOD で被覆され、真の未被覆は `依存グラフ出力処理` / `参照関係複雑度計算処理` の 2 件（いずれも `labels: [post-mvp]`・`scheduled: sprint-2`）に減る。

**帰結**:

1. 現行規則の下では、DD-13 の混合粒度をどう実現しても違反が残る。L1 維持を選べば配下 leaf P が MOD 無しになり、L2 分割を選べば親の傘 P が MOD 無しになるためで、42 件の ERROR は「実装が足りない」ではなく**規則が仮定する粒度が確定済み設計決定と異なる**ことに起因する。
2. 42 件が恒常的に赤のまま残ると、機械検証のシグナルが劣化する（真に処置すべき違反が定常ノイズに埋もれる）。PR2 の「機械判定でゲートする」という前提が `p←mod` については実質的に失われている。
3. MOD 保有 P 14 件のうち **12 件は non-leaf P を指している**。規則を leaf 限定にすると、この 12 本の `MOD→P` 辺は規則の要求対象から外れる（＝辺の張り替えが必要になる）。

**修正方向（オーナー確定・2026-07-26／本 FND では再検討しない）**:

1. **修正の方向は「leaf のみが MOD を要する」**とする。
2. そのために**必要であれば DD-13 も変更する**。
3. **SPEC と方向性が同一**との認識であり、これら leaf 限定規則を**通常の `must_link_to` / `must_be_linked_from` 属性から分離すること**も視野に入れる（決定ではなく方向性）。

**確定方向を適用した場合の実測帰結（判断材料）**:

- 新たに MOD を要求される leaf P は **39 件**（leaf 41 件 − 既存 MOD 保有 2 件）。ERROR は **42 → 39** となり、**件数上の改善はほぼ無い**。
- 既存 MOD 保有 12 件は non-leaf P を指しているため**規則の要求対象から外れ**、指し先の張り替えが必要になる。
- 1 leaf = 1 MOD を前提に充足させる場合、規模は **DD-13 が却下した選択肢A（34+ モジュール）と実質同等**（MOD 12 → 39 超）になる。
- したがって処置は「判定ロジックの修正」だけでは収まらず、**DD-13 改訂＋MOD 再編**を伴う。
- **#253 との設計方針競合（事実）**: #253 は `applies_when` を `<field>=<value>` の汎用述語へ一般化する案を同じ `must_be_linked_from_gaps()` に予定している。一方 leaf 性は「同型ノード間の親子辺の**不在**」というグラフ述語であり、ノード単体のフィールド値では表現できない。「専用ブロックへ分離」する案（方向性3）と汎用述語一般化案は同一箇所を別方向へ動かすため、**両者の関係整理が先に必要**である。
- **#160 との連動**: #160 の「設計実装の整合」(c) 10 件（実装は在るが名前・分割が設計と別）は MOD 再編と同一対象に触れる。

**選択肢（確定方向の実装方法・および DD-13 改訂の具体案。「leaf-only にするか否か」は確定済みのため対象外）**:

*(a) 規則側の表現方法*

1. **既存 `applies_when` に leaf 述語を追加する** — `applies_when: leaf`（仮称・`children_absent` 等）を新設し `p←mod` に付与する。実装は `must_be_linked_from_gaps()` に `condition_present` と並ぶ分岐を足すだけで済み最小。ただし `applies_when` にフィールド述語（#253 の `<field>=<value>`）とグラフ述語（leaf）が同居し、限定子の意味論が二種類混在する。
2. **leaf 限定規則を専用ブロックへ分離する**（オーナーが視野に入れている方向） — `must_link_to`/`must_be_linked_from` とは別のキー（例 `leaf_scoped_rules`）に leaf 限定の必須辺規則を集約し、`p←mod` と `spec←td` を同じ機構へ寄せる。`applies_when` はフィールド述語専用として #253 の一般化に明け渡せるため方針競合が解消する。`config.yml` スキーマ（`接続ルールスキーマ`）・`validate.py`・`dsv2/query.py` の変更が必要。
3. **① を暫定で入れ、#253 の一般化と同時に ② へ移す二段階** — 42 件の ERROR を先に鎮めた上で機構整理を後段に回す。中間状態で限定子の意味論が混在する期間が生じる。

*(b) DD-13 改訂の粒度案*

- **案X: 1 leaf = 1 MOD（選択肢A 相当）** — MOD 12 → 39 超。leaf-only 規則を素直に満たすが、DD-13 が「管理不能」として却下した規模に戻る。
- **案Y: MOD 総数は DD-13 の中間粒度（18 前後）を維持し、1 MOD が担当する leaf P 全てを指す** — `must_link_to` の `{ node: mod, target: [p, d] }`（`config.yml` L86）は「1 本以上」で本数上限を持たないため、1 MOD が複数 leaf P へ辺を張ることは規則上許容される。例: `parser.py` の指し先を傘 `ノード受付・パース` から配下 leaf 5 件へ張り替える。MOD 爆発を起こさずに leaf-only 規則を充足できる。DD-13 には「MOD は担当する leaf P すべてを指す」という辺の張り方の規定を追記する改訂が必要。
- **案Z: 案Y を採りつつ post-mvp の leaf（`依存グラフ出力処理` / `参照関係複雑度計算処理` 等）を段階適用の対象外にする** — sprint-1 の処置量を絞れるが、除外の表現手段（`labels: post-mvp` を判定へ持ち込むか）を別途決める必要がある。

**推奨**: 規則側は **選択肢②（専用ブロックへ分離）**、粒度は **案Y（MOD 総数を維持し担当 leaf 全てを指す）**。根拠は 3 点。

- leaf 性はグラフ述語であり `<field>=<value>` の汎用述語（#253）では原理的に表現できない。同じ `applies_when` に同居させると限定子の意味論が二種類混在し、#253 の一般化のたびに leaf 分岐が特例として残る。分離すれば競合が構造的に解消し、`spec←td` の `condition_present` も同じ機構へ寄せられる（SPEC の同型性を機構レベルで回収できる）。
- 案Y は leaf-only 規則を満たしつつ MOD 総数を DD-13 の中間粒度に保つため、DD-13 が却下した規模（選択肢A・34+）へ戻らずに済む。DD-13 の改訂は「粒度の再選択」ではなく「辺の張り先を傘から配下 leaf 群へ変更する」規定追加に留まり、覆る場合の影響範囲も小さい。
- 案X は 12 → 39 超の MOD 新設を伴い、#160 の (c) 10 件と同一対象へ大規模に触れるため、sprint-1 で処置しきれないリスクが高い。

**未決事項（決定側で確定させる）**: (1) 選択肢② を採る場合の #253 との実施順序（分離が先か汎用述語一般化が先か）、(2) 案Y における MOD→leaf 辺の粒度規定を DD-13 改訂（MINOR）で行うか新規 DD を起こすか、(3) MOD を持たない non-leaf P 3 件（`rule-検査` / `カバレッジ点検` / `ノード著作・反映プロセス`）を leaf-only 化後に無 MOD のまま許容する扱いの明文化。

**指摘時 ref_version**: must_be_linked_from "0.1"（must_be_linked_from.yaml v0.1.1 時点）

**接続規則変更の伝播チェック**: 本 FND は**起票時点では `doc-system-v2/config.yml` の接続規則を変更していない**（指摘と選択肢提示のみ）ため、著作資産への同期は不要。ただし確定方向（leaf-only）を反映する決定を下した時点で `must_be_linked_from` の `p←mod` 規則が変更されるため、決定側（DD）で以下への伝播を実施すること: `docs/doc-system/03-connection-matrix.md`（接続要否マトリクス・mermaid 図）・`docs/doc-system/01-document-items.md`（P/MOD の上流参照列）・`.claude/agents/analysis-author.md` および `.github/agents/analysis-author.agent.md`（P の必須辺記述）・`.claude/agents/design-author.md` および `.github/agents/design-author.agent.md`（MOD の必須辺記述）・`.claude/skills/architecture-design/SKILL.md`（MOD 粒度と MOD→P 辺の張り方）・CFG ノード `must_be_linked_from`（および選択肢②を採る場合は `must_link_to`）本文・SCM ノード `接続ルールスキーマ`（選択肢②では新ブロックのスキーマ追加）・`dsv2/query.py` の `must_be_linked_from_gaps()` docstring の依存仕様アンカー。旧ルールの記述を残すと次回著作時に傘 P 向け MOD が再生産される（FND-99 パターン）。

**実施時期**: `scheduled: "sprint-1"`（起票時点＝current_phase）。実施 sprint の繰り越しは独断で行わずオーナー判断に委ねる。
