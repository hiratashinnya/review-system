**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→I-1 "0.1"`・`→FR-1 "0.3"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 I-1 から `→FND-18`・FR-1 から `→FND-18` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: I/O ノード（I-1〜I-7・O-1〜O-3）の本文 `**形式**:` フィールドはすべて非公式な散文記述にとどまっており、SPEC ノードとして機械検証可能なフォーマット定義が存在しない。

具体的な欠落:
- **I-1 入力フォーマット（最重要）**: ノードファイルの有効な YAML frontmatter に含まれる全フィールド（`id`・`type`・`labels`・`scheduled`・`suppress`・`edges`・`condition`・`result`・`log_ref`）の型・必須/任意・値制約を正式定義する SPEC がない。SPEC-1/2・SPEC-31〜35 はパース動作とエラーケースをカバーするが、完全フィールドスキーマは未仕様。02-meta-schema.md が事実上の定義源だが out-of-graph（trace_scope 除外）であり RULE 対象外。
- **O-2 出力フォーマット**: SPEC-14 はカバレッジ点検の内容を規定するが、カバレッジテーブルの具体的な出力形式（列名・行フォーマット・ソートキー）が未定義。
- **I-7 テンプレートフォーマット**: SPEC-26 は著作プロセス（P-7 が I-7 を参照すること）を規定するが、テンプレートファイル自体が満たすべき構造（型・必須セクション・プレースホルダ形式）が未仕様。

影響: フォーマット違反のノードファイルやテンプレートを spec-inspector が検出できない。仕様の唯一ソースが out-of-graph ドキュメントに依存し続ける。
**対応状況**: resolved（重複不可方針で再処置・2026-06-13）

**経緯①（初回処置を差し戻し）**: 初回処置で SPEC-41（I-1 完全スキーマ）・SPEC-42（O-2 カバレッジ出力）・SPEC-43（I-7 テンプレート構造）を著作したが、オーナーレビューで**テスタブルな粒度に達していない**として差し戻し（spec.md v0.3.3 で 3 SPEC 撤去）。粒度違反:
- **SPEC-41**: 「必須フィールド存在」「型チェック4種」「未知キー→WARNING」を 1 ノードに束ね・normal/failure 混在。
- **SPEC-43**: 「id/type/edges/型別必須フィールド」を束ね・normal/error 混在。
- **SPEC-42**: ヘッダ/行/ソート/gap を束ね・gap は既存 SPEC との重複疑い。

**経緯②（重複不可方針で再処置・採用）**: 既存 SPEC を精査し、**重複を作らず真の欠落のみ**を 1 アサーション 1 SPEC で再著作（spec.md v0.3.4）:
- **I-7 テンプレート構造 → 新規ゼロ（重複回避）**: 既存 **SPEC-26**（FR-11・normal・テンプレが id/type/labels/scheduled/edges/本文4項目を含む）＋ **SPEC-36**（FR-11・failure・テンプレ由来必須欠如→RULE-025/026）が既に充足。当初の「I-7 未仕様」判断は誤りで、既存カバレッジを見落としていた。新規 SPEC は起票しない。
- **I-1 完全スキーマ → SPEC-52（FR-1・normal）＋ SPEC-53（FR-1・failure・RULE-028）**: id/type 欠如（SPEC-33/34）・ref_version 欠如（SPEC-35）は既出のため重複回避し、**残る共通必須フィールド `labels`/`scheduled`/`edges` の存在と型**を新 RULE-028 で検証。SPEC-52 が完全スキーマ適合（normal）、SPEC-53 が型不正・欠如検出（failure）。RULE-028 を `docs/doc-system/05-verification.md` 段階0（パース検証・ノード単位 fail-close）に追加。
- **O-2 出力フォーマット → SPEC-14-1（SPEC-14 の -N 分割・normal）**: 親 SPEC-14（FR-6・カバレッジレポート生成）の出力フォーマットを精緻化（ヘッダ列名・行フォーマット・FR-id 昇順ソート）。gap 出力は SPEC-14 本体／RULE-017/018 の責務として**重複回避**。当初 FR-3 配下に置こうとしたが、カバレッジの正当な親は FR-6（SPEC-14）と判明。

**処置対象ノードへの backref**: I-1・FR-1（指摘対象）・SPEC-14（O-2 フォーマット精緻化先）に `→FND-18` を付与。

**指摘時 ref_version**: I-1 "0.6"（io.md v0.6.2 時点）、FR-1 "0.2"（fr.md v0.2.2 時点）
