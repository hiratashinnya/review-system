**status: decided**（2026-07-21 オーナー確定・config.yml 反映済み）

FND `接続規則が価値経路連続性を error で機械保証していない` からの昇格決定。指摘は「提案」段階で起票されたが、オーナー確定（2026-07-21）により規則の是非は確定済みであり、本 DD をもって確定記録とする。

**論点**: doc-system-v2 の接続規則（`config.yml: must_be_linked_from`）が、価値経路の下流連続性——要件・仕様で宣言した価値が「設計 → 実装 → 検証」まで途切れずに落ちること（PR6 価値経路を遮断しない）——を error で機械保証していない。設計段の下流引き（P←MOD 等）や実装段の SRC への被依存が規則化されておらず、また一部の下流引きが warning に留まっていたため、価値経路の穴を機械的なゲート（error）で塞げていなかった。

**選択肢**:
- **A（全採用・error で機械保証）**: 設計段・実装段の下流被依存辺を `must_be_linked_from` に error として追加し、既存の一部 warning を error へ昇格。テスタブル SPEC への検証導出も error 化する。
- **B（warning 据え置き）**: 新規則を追加するが severity は warning に留め、違反を報告のみとする（ゲートしない）。
- **C（現状維持）**: 価値経路連続性は運用ルール（人の確認）に委ねる。

**推奨**: A。価値経路連続性は「順序のある属性＝機械でゲートできる」機械判定（PR2）であり、warning では価値の落ち漏れ（設計止まり・実装漏れ・検証漏れ）を構造的に防げない。B は穴を許容し続け、C は PR6 の保証を人手に戻して退行する。ただしテスタブルでない対象（傘 SPEC＝condition 無）まで一律 error にすると偽陽性を生むため、テスタブル条件で限定する。

**決定（全採用・即時 config 反映済み・2026-07-21）**:
1. `must_be_linked_from` に下流の引きを error で追加（config 反映済み）:
   - design 段: `p←[mod]`（error）, `scm←[cfg]`（error）, `ds←[prs]`（error）
   - implementation 段: `mod / dm / port / orc / prs / prompt / cfg ← [src]`（error・各1行）
2. 昇格: `nfr←[spec]` を warning→**error**（NFR は必ず SPEC へ導出＝設計へ落ちる）。
3. 昇格＋限定: `spec←[td]` を warning→**error**。ただし `applies_when: condition_present`——テスタブル（condition 有）SPEC=176 件のみ対象とし、傘 SPEC（condition 無=54 件）は非テスタブルのため除外する。
4. **SRC→設計 のシンボル適格性条件（適格性条件付きで採用）**: `mod / dm / port / orc / prs / prompt / cfg ← src` の充足は「設計種別ごとに張ってよいシンボル種別」を満たす SRC のみを有効とする。例: MOD（モジュール担体）はモジュールレベルのシンボルにのみ対応可で、モジュール内の関数を MOD 充足に流用してはならない。適格性は機械検証可能（`src.kind` × 設計種別のマッチング）に設計する。**本適格性の詳細設計（`src.kind` 語彙・設計種別×シンボル種別の対応表・検査ロジック）は別 DD に委ね、オーナー再確認待ちである**。DD-9 では「適格性条件付きで採用」とだけ確定し、詳細は後続 DD で確定する。

**影響範囲**:
- `config.yml`（out-of-graph・反映済み）: 上記 `must_be_linked_from` の新規 10 行＋severity 変更 2 行＋`spec←td` の `applies_when: condition_present` を反映済み。
- in-graph 規則モデル（本バッチで反映中）:
  - CFG `must_be_linked_from` ノードを現行 config.yml へ同期（T3・design-author）。本 DD の義務辺 `DD→must_be_linked_from` は「in-graph モデルへ未反映」を表し、同期完了後に decision_spine に従い `must_be_linked_from→DD` へ逆転させる。
  - 新規則の dedicated SPEC 群を追加＋既存 2 件（`spec←td`・`nfr←spec`）の severity 記述是正（T2・spec-author）。
- **施行タイミング**: 施行は #163（Phase B）で `must_be_linked_from` reader を実装した時点で発火する。現状 `validate.py` は `must_be_linked_from` を未読のため、宣言は inert（宣言済みだが未施行）。SRC 系は #160 の SRC 著作＋implementation stage で初めて対象化する。
- **覆る場合の影響**: 施行後に P42 / P56 等の既存の下流連続性違反が顕在化し、#160 / #161 の是正を駆動する。覆す場合は施行前に config.yml と in-graph モデルの双方を戻す必要がある。

**接続規則変更の伝播（FND-99 型ドリフト防止）**: 本 DD は `config.yml` の接続規則（`must_be_linked_from`）を変更するため、機械判定の正本（config.yml・反映済み）だけでなく、規則を人間/LLM 向けに表現する out-of-graph 著作資産（接続マトリクス `docs/doc-system/03-connection-matrix.md`・ドキュメント一覧 `docs/doc-system/01-document-items.md`・design-author / verification-author 等の author エージェント）にも同期が必要。本規則反映バッチ（DD-9 / T2 / T3）およびその後続で当該資産へ同期する。T1（本 DD 著作）はグラフ内の決定記録が責務であり、out-of-graph 資産の同期漏れは施行フェーズ（#163）着手前に FND で機械検出・処置する。

**FND 解消（別工程）**: 昇格元 FND `接続規則が価値経路連続性を error で機械保証していない` の解消（backref 付与・辺逆転）は、DD-9・規則 SPEC が揃った後に主文脈が `python3 -m dsv2 reverse` で機械実行する。本 DD の著作では解消操作は行わない。
