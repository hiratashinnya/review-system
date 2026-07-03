**対応状況**: resolved（2026-06-24・本 PR #38 内で処置完了）

**深刻度**: ERROR

**指摘対象**: `docidx/query.py` の `_drift` 関数（実装）

**指摘時 ref_version**: 付与先なし（指摘対象 `docidx/query.py` は out-of-graph のためノード版なし）

**内容**:

`_drift` の比較ロジック（行 46）`return ref_version != target.version` がフル x.y.z 文字列を比較する。仕様（04-notation.md §2・§3・DD-8 §4）は「z は伝播判定に不問（z バンプはドリフト非誘発）」と定める。参照先が z バンプした場合、依存辺の ref_version が x.y.0 のままでも drift=True が返り、RULE-004 違反として誤検出される。

また `_drift` の docstring「ref_version が参照先バッジ **x.y** と不一致なら True」は x.y 比較を示すが、実装はフル x.y.z 比較のため docstring とも乖離している。`tests/unit/test_docidx_query.py` に z のみ異なる場合の非ドリフトテストが欠落しており、このバグがテストをすり抜けていた。

FND-107（PR #38 処置中）がデータ側の x.y.z 化を完了させた一方、ドリフト判定ロジックが z-不問に未対応のため、z-bump 機構が実質まだ機能しない状態が残存する。

**再現手順**: 参照先ノード FR-1 を version 0.3.1、依存辺 ref_version: "0.3.0" として `query.deps(...)['drift']` を呼ぶと True が返る（期待値: False）。

**推奨処置（オーナー承認で即時実施）**:
1. `_drift` の比較を x.y 正規化比較に変更：`ref_version.rsplit(".", 1)[0] != target.version.rsplit(".", 1)[0]`（ただし空文字・1部分形式の安全性を確認して実装）
2. `_drift` docstring を実装に合わせて修正
3. `test_docidx_query.py` フィクスチャを x.y.z 化・z-不問ケースを追加

### 処置記録（2026-06-24）

コミット `dfc0bdb`（本 PR #38 内）。

- `docidx/query.py`: `_xy()` ヘルパーを追加し x.y 部分のみ抽出して比較。docstring を x.y 比較に更新（FND-108・DD-8 §4 参照追加）。
- `tests/unit/test_docidx_query.py`: フィクスチャを x.y.z 化、`test_z_bump_no_drift`（z のみ差分→drift=False）・`test_minor_bump_drift`（y バンプ→drift=True）追加。163 tests PASS。
- バックリファレンス付与先なし（指摘対象 `docidx/query.py` は out-of-graph）。仕様ノード SPEC-9 に `→FND-108` 辺を付与（仕様↔実装乖離のトレース）。
