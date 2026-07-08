**深刻度**: WARNING（ランタイム破壊なし。設計層のみの陳腐化で、参照している `spec_inspector/` パッケージ自体がまだリポジトリに存在しない＝計画段階の設計記述であり稼働コードには影響しない）

**対応状況**: resolved

**内容**:
issue #118 で doc-system-v2 自身の検査制御は「①scheduled ②ステージ発火 ③suppress の三軸」から **suppress 軸を廃止した二軸** に変更された。一方で、分析層 DFD と設計層モデルには旧 suppress 軸を前提にした記述が残っていた。

陳腐化していた具体ノード:

- **03-analysis（分析層 DFD）**
  - **P-2-5「抑制・発火フィルタ」**（`抑制・発火フィルタ`・v0.1.0）: 「scheduled 完全サイレント／ステージ発火／always-error 規則／属性検査ビュー」を束ねる抑制プロセスとして三軸を前提に分割されていた。
  - **D-4「構造化ノードセット」**（`構造化ノードセット`・v0.2.0）: NodeRecord に相当する構造化集合の定義が `suppress` を保持フィールドとして言及していた。
  - **D-12「always-error 規則」**（`always-error-規則`・v0.1.0）: suppress に載せても抑制されない always-error ルール群という、suppress 機構の存在を前提とした説明になっていた。
  - **D-18「属性検査ビュー」**（`属性検査ビュー`・v0.1.1）: 属性ビューに suppress 関連スライスが残っていた。
  - **P-7「RULE 検査」**（`rule-検査`・v0.3.0）: RULE 検査プロセスが抑制フィルタと連動する前提で記述されていた。
- **05-design（設計層）**
  - **DM-1「NodeRecord 型」**（`noderecord型`・v0.1.1）: `@dataclass(frozen=True)` の NodeRecord 型仕様が **`suppress: list[str]`** フィールドを含んでいた。
  - **MOD「filter」**（`filter`・v0.1.0）: `spec_inspector/filter.py` として `apply_suppression(violations, config) -> list[ViolationRecord]` を公開 I/F に持っていた。なお `spec_inspector/` パッケージは未実装の設計記述であり、稼働コードへの影響はない。

**対応内容**:
- P-2-5 と MOD `filter` を、suppress 適用関数ではなく `scheduled` / `activate_stage` / `always_error` による発火確定・重症度確定責務へ縮退した。slug は既存参照の広範囲変更を避けるため維持した。
- D-4・D-18・DM-1・InspectionViews から `suppress` フィールド/スライスを除去し、`scheduled` は現行のフェーズ限定発火指定として残した。
- D-12 / CFG `always_error` は完全消滅ではなく、RULE-005/007 などを scheduled/ステージ制御に関わらず常時 ERROR 発火させる fail-close 指定として意味を縮退した。
- P-2-1〜P-2-4 系の親検査ノードについて、「各検査子は候補を出し、P-2-5 が抑制適用」という旧表現を「発火確定・重症度確定」に置換した。
- `dsv2/README.md` と、同じ分析/設計層内の直接矛盾する短い記述を現行化した。
- `rtk python3 -m dsv2 reverse --root doc-system-v2 --apply ...` により、FND の forward 辺を削除して `open/` から `resolved/` へ移動し、処置対象 7 ノードへ backref を付与した。

**指摘時 ref_version**（DD-3 制度化・辺逆転後も指摘時の版を追跡できるよう本文に記録）:
- 抑制・発火フィルタ "0.1"（抑制・発火フィルタ.yaml v0.1.0 時点）
- 構造化ノードセット "0.2"（構造化ノードセット.yaml v0.2.0 時点）
- always-error-規則 "0.1"（always-error-規則.yaml v0.1.0 時点）
- 属性検査ビュー "0.1"（属性検査ビュー.yaml v0.1.1 時点）
- rule-検査 "0.3"（rule-検査.yaml v0.3.0 時点）
- noderecord型 "0.1"（noderecord型.yaml v0.1.1 時点）
- filter "0.1"（filter.yaml v0.1.0 時点）
