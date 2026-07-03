**status: decided**（2026-06-14 反映完了）

**指摘時 ref_version**: FND-78 "0.1"（findings.md v0.1 時点）

**論点**: FND-78 で指摘。`config.yaml` の `phases` に `post-mvp` が含まれており、SPEC-28/40 が `scheduled: "post-mvp"` を使用、SPEC-50/51 は `labels: [post-mvp]` だが `scheduled: ""` と表現が不統一。`scheduled` の値ドメインが phases と独立しており、phases 外の文字列を無効化するルールが存在しなかった。

**選択肢**:
- **A（post-mvp 除去＋RULE 新設）**: `phases` から `post-mvp` を除去し、RULE-029「scheduled が非空かつ phases 外の値」= ERROR を新設。SPEC-28/40/50/51 の scheduled を実スプリント（sprint-2）へ設定。phases = [sprint-1, sprint-2, sprint-3] に整理。
- **B（post-mvp 残存）**: post-mvp を phases に残し、scheduled の空許容を維持。scheduled の不統一は許容。

**推奨**: A。理由：`post-mvp` は実スプリントではなく優先度ラベルの概念であり、phases（スプリント計画）と混在することで scheduled の意味論が曖昧になる。実施時期は sprint-N で表現し、post-mvp 扱いは `labels: [post-mvp]` に集約すべき（scheduled と labels の責務分離）。

**決定**: A を採用（オーナー承認・2026-06-14 FND-78 決定B）。

**影響範囲（2026-06-14 即時実施完了）**:
- `docs/doc-system/config.yaml`: `phases` を `[sprint-1, sprint-2, sprint-3]` に変更（post-mvp 除去）。✅ 完了
- `docs/doc-system/05-verification.md`: 段階 0 テーブルに RULE-029 を追加（`scheduled` 値ドメイン検証・非空かつ phases 外 → ERROR）。✅ 完了
- `doc-system/02-what/03-spec.md`: SPEC-28（v0.2→0.3）・SPEC-40（v0.1→0.2）を `scheduled: "sprint-2"` へ変更。SPEC-50（v0.1→0.2）・SPEC-51（v0.1→0.2）を `scheduled: "sprint-2"` へ変更。各ノードに `→FND-78` バックリファレンス付与。✅ 完了
- `doc-system/04-verification/02-findings.md`: FND-78 を `resolved` へ更新。✅ 完了（本 DD 適用で）
- RULE-029 の suppress 可否: `always_error` には含めない（suppress 可能とし、後フェーズ専用 SPEC など合理的理由がある場合は免除を許容）。
