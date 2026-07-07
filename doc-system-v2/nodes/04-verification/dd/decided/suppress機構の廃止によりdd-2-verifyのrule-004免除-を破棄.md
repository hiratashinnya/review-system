**status: decided**（issue #118・2026-07-07 反映）

**論点**: DD-2（`verify-の-rule-004-免除・fnd-は再検証シグナルとして据え置き-q-1-から昇格`）は、VERIFY ノードの凍結スナップショット（過去のレビュー事実）を RULE-004 ドリフト WARNING から免除するため `suppress: [RULE-004]` を付与する suppress 機構を制度化した（DD-2 オプションA）。しかし issue #118 でオーナーが **suppress 機構自体の廃止** を決定した（「依存先ノードが更新されたら自ノードへ影響有無の確認は必須。その契機を作るための ref_version を抑制する発想が意味わからん」）。DD-2 の決定と #118 のオーナー方針が両立しないため、DD-2 を明示的に破棄する必要がある。

**決定**:
- DD-2 のオプションA（VERIFY に `suppress: [RULE-004]` を付与し凍結免除）を **破棄** する。
- 今後 VERIFY 等の凍結スナップショット辺も **無条件で drift 判定の対象** になる（ref_version が古いままなら常に RULE-004 の ERROR/WARNING が発火する）。ドリフト発火は「記録が陳腐化 → 依存先変更の影響確認 → 必要なら再検証」の契機として機能させる（DD-2 で FND に採用していた選択肢C の考え方を全記録系へ一般化する）。
- 過去のスナップショット事実（どの版を・いつレビューしたか）は、**生きた依存辺としてではなく各 VERIFY 本文の out-of-graph 記録（YAML コードブロック）** として保持する（PR8「消さない」・本 issue #118 の PR で実施済み）。suppress 機構そのものを指していたメタ辺（DD-2・当該 FND・当該 Q への辺）は edges から除去し、本文へ退避した。

**影響範囲**:
- コード側は本 PR で処置済み：`doc-system-v2/schema/sidecar.schema.json`・`doc-system-v2/validate.py`・`dsv2/query.py`（`_suppresses_drift()` 撤去でドリフト無条件発火）・`dsv2/meta.py`・`dsv2/viewer.py`・`doc-system-v2/config.yml`（`always_error:` 撤去）・`doc-system-v2/FORMAT.md`・`doc-system-v2/notation.md`・関連テストから suppress 機構を除去。
- コーパス側も本 PR で追随：VERIFY 5件（`suppress: [RULE-004]`）と FR 5件（`suppress: [RULE-018]`）から suppress フィールドを除去。suppress 軸を要件層でモデル化していた FR「三軸の検査抑制機構」→「二軸」改訂＋その axis③ 子孫 SPEC 群を廃止表記（対象消滅）に更新。
- 本 DD の `edges:` は DD-2 と FND「分析層の版上げに伴う ref_version ドリフト群」への被参照 in-degree を維持し、VERIFY 側 backref 除去後もこれらが孤立ノード（RULE-005）にならないようにする役割を持つ。
- **残ギャップ（別 FND で起票・本 PR スコープ外）**: 分析層（P-2-5「抑制・発火フィルタ」／D-4／D-12／D-18／P-7）と設計層（DM-1 NodeRecord 型の `suppress` フィールド／MOD `filter.md` の `apply_suppression()`）は依然 suppress を三軸の一つとしてモデル化したままで、本 issue の要件/検証層退役に未追随。DFD 分解・DM 型仕様の作り替えは相応の後続設計タスクのため本 PR の限定スコープ（dsv2 コード＋FR/SPEC 要件層＋VERIFY 検証層＋config＋テスト）から外し、別途 FND として起票してオーナーのスケジュール判断を仰ぐ。
