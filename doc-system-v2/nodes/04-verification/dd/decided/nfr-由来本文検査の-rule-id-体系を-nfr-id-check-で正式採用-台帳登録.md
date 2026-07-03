**status: decided**

**指摘時 ref_version**: FND-86 "0.1"（findings.md v0.1 時点）

**論点**: FND-86 で指摘（INFO）。NFR 由来の本文検査（SPEC-44〜49 が検証する NFR-1〜6）の出力行3列目 rule-id が `{NFR-id}-check`（例 `NFR-1-check`）で記載されているが、正準ルール台帳（`docs/doc-system/05-verification.md` の `RULE-NNN`）に登録がなく、全 rule-id を台帳から一覧できない。出力契約（O-1 RULE 違反レポート）における違反 ID の名前空間が二重化しており、消費側（reconciliation・spec-inspector）の解釈がぶれる。

**選択肢**:
- **A（RULE-NNN 採番）**: RULE-030〜035 を新設し、SPEC-44〜49 の出力例6件を `{NFR-id}-check` → `RULE-NNN` へ差し替える。
- **B（`{NFR-id}-check` 正式採用）**: `{NFR-id}-check` を NFR 由来検査の正式 rule-id 体系として台帳に1家族（NFR-1〜6 各1検査）として登録。SPEC 例は据置。
- **C（現状維持）**: 台帳未登録のままとする。

**推奨**: B。理由: (1) DD-5 が NFR→SPEC 導出で「番号付き RULE は新設せず config 駆動」を既に採用済みで、`{NFR-id}-check` 据置はこの方針と整合。(2) `NFR-1-check` は対応 NFR へ直接トレース可能（`RULE-030` は不透明）。(3) SPEC 例の churn ゼロ。C は台帳の網羅性穴を残すため不採用。

**決定**: B を採用（暫定・設計フェーズ）。`docs/doc-system/05-verification.md` の RULE 台帳に「NFR 由来本文検査: rule-id = `{NFR-id}-check`（NFR-1〜6 各1検査・SPEC-44〜49）」を1家族として登録する。

**影響範囲**:
- `docs/doc-system/05-verification.md`（out-of-graph）に台帳行を追加（reconciliation 反映後に主文脈で実施）。
- SPEC-44〜49 の出力例は変更なし。
- `doc-system/04-verification/02-findings.md`: FND-86 を `resolved` へ更新。
- **覆る場合**: 将来 A（RULE-NNN 採番）へ切替えるなら SPEC-44〜49 の出力例6件＋台帳行＋関連 TC を一括改修（影響は spec 層6ノードの 例 と台帳に限定）。
