**深刻度**: WARNING（ランタイム破壊なし。設計層のみの陳腐化で、参照している `spec_inspector/` パッケージ自体がまだリポジトリに存在しない＝計画段階の設計記述であり稼働コードには影響しない）

**対応状況**: open（本 issue #118 の PR では処置しない新規発見。処置はオーナーのスケジュール判断後）

**内容**:
issue #118 でオーナーが doc-system-v2 自身の検査抑制機構を「①scheduled ②ステージ発火 ③suppress の三軸」から **suppress 軸を廃止して二軸** に変更する決定を下し、本 PR で要件層（FR「三軸の検査抑制機構」→二軸・axis③ 子孫 SPEC 群の廃止表記）・検証層（VERIFY 5件の `suppress` 除去）・コード（schema/validate.py/query.py/config.yml 等）まで追随した。しかし doc-system-v2 の自己記述である **分析層 DFD と設計層モデル** が依然 suppress を三軸の一つとしてモデル化したまま残っており、#118 後の二軸の実像と乖離している。

陳腐化している具体ノード:

- **03-analysis（分析層 DFD）**
  - **P-2-5「抑制・発火フィルタ」**（`抑制・発火フィルタ`・v0.1.0）: 「scheduled 完全サイレント／ステージ発火／always-error 規則／属性検査ビュー」を束ねる抑制プロセスとして三軸を前提に分割されている。suppress 軸廃止に伴い、抑制固有のスライスは退役/併合が必要。
  - **D-4「構造化ノードセット」**（`構造化ノードセット`・v0.2.0）: NodeRecord に相当する構造化集合の定義が `suppress` を保持フィールドとして言及している。
  - **D-12「always-error 規則」**（`always-error-規則`・v0.1.0）: suppress に載せても抑制されない always-error ルール群という、suppress 機構の存在を前提としたデータ。suppress 廃止後は「always-error」概念自体が意味を失う（全ルールが無条件発火）。
  - **D-18「属性検査ビュー」**（`属性検査ビュー`・v0.1.1）: 抑制フィルタが射影する属性ビューのうち suppress 関連スライスが陳腐化。
  - **P-7「RULE 検査」**（`rule-検査`・v0.3.0）: RULE 検査プロセスが抑制フィルタと連動する前提で記述されており、無条件発火への一本化に未追随。
- **05-design（設計層）**
  - **DM-1「NodeRecord 型」**（`noderecord型`・v0.1.1）: `@dataclass(frozen=True)` の NodeRecord 型仕様が **`suppress: list[str]`** フィールドを含む。#118 で schema/validate から suppress が除去されたため、この型フィールドは実装対象消滅。
  - **MOD「filter」**（`filter`・v0.1.0）: `spec_inspector/filter.py` として `apply_suppression(violations, config) -> list[ViolationRecord]` を公開 I/F に持ち、P-2-5 を実現するモジュールとして定義。suppress 廃止で `apply_suppression()` は不要になる。なお `spec_inspector/` パッケージは Glob/Bash で確認した限りリポジトリに未実装（設計層のみの記述）で、稼働コードへの影響はない。

**指摘時 ref_version**（DD-3 制度化・辺逆転後も指摘時の版を追跡できるよう本文に記録）:
- 抑制・発火フィルタ "0.1"（抑制・発火フィルタ.yaml v0.1.0 時点）
- 構造化ノードセット "0.2"（構造化ノードセット.yaml v0.2.0 時点）
- always-error-規則 "0.1"（always-error-規則.yaml v0.1.0 時点）
- 属性検査ビュー "0.1"（属性検査ビュー.yaml v0.1.1 時点）
- rule-検査 "0.3"（rule-検査.yaml v0.3.0 時点）
- noderecord型 "0.1"（noderecord型.yaml v0.1.1 時点）
- filter "0.1"（filter.yaml v0.1.0 時点）

**推奨**:
後続の issue/スプリント項目として、分析層 DFD と設計層モデルを二軸の実像に作り替える:
- 分析層: P-2-5「抑制・発火フィルタ」の suppress 固有スライスを退役/併合し、D-12「always-error 規則」と D-18 の suppress 関連スライスを撤去、D-4「構造化ノードセット」の suppress 言及を簡素化、P-7「RULE 検査」を無条件発火前提に改訂。
- 設計層: DM-1「NodeRecord 型」から `suppress: list[str]` フィールドを除去、MOD「filter」の `apply_suppression()` を撤去/縮退（本 PR で除去済みの query.py 実像に合わせる）。

ただし DFD 分解（Warnier-Orr プロセス分割から抑制軸を外す作業）と DM 型仕様の作り替えは相応の後続設計タスクであり、本 PR の限定スコープ（dsv2 コード＋FR/SPEC 要件層＋VERIFY 検証層＋config＋テストの 9 ステップ）を超える。**実施スプリントはオーナーのスケジュール判断に委ねる**（CLAUDE.md「スケジュール独断禁止」に従い `scheduled` は空のまま）。今スプリント即時実施も、次スプリント以降への繰り越しも選択肢として提示し、判断を仰ぐ。
