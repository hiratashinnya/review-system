**status: decided**（2026-06-14 反映完了）

**指摘時 ref_version**: FND-84 "0.1"（findings.md v0.1 時点）

**論点**: FND-84 で指摘（ERROR）。DD-8（2026-06-14 確定）でファイルレベル YAML frontmatter `version:` フィールドは全廃されノードバッジ x.y が版管理の唯一の真実源となった。しかし SPEC-47 は「全 in-graph ファイルの frontmatter に `version` フィールドが存在する」ことを ERROR 要求し（廃止済みの仕組みを要求）、NFR-1 本文は「プレーン Markdown＋YAML フロントマター」と記述しファイルレベルフロントマターの存在を前提としていた。

**選択肢**:
- **A（SPEC-47 内容置換・NFR-1 本文訂正）**: SPEC-47 を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証へ置換。NFR-1 本文から「YAML フロントマター」の記述を除去し、インライン YAML ブロック埋め込み形式に訂正。
- **B（SPEC-47 廃止）**: SPEC-47 を削除（孤立ノード化するため suppress かラベルで無効化）。NFR-4 のノードバッジ検証は別途 SPEC を著作。
- **C（現状維持）**: DD-8 矛盾を許容し SPEC-47 を凍結する。

**推奨**: A。NFR-4（ファイル単位バージョニング・1 ファイル 1 責務）は DD-8 後もノードバッジでの版管理として有効であり、SPEC-47 はその検証 SPEC として機能する。検証対象を frontmatter → ノードバッジに切り替えることで DD-8 準拠を達成できる。B は検証カバレッジの穴を生む。C は ERROR 違反の放置で不採用。

**決定**: A を採用（オーナー承認・2026-06-14 FND-84 決定）。

**影響範囲（2026-06-14 即時実施完了）**:
- `doc-system/02-what/03-spec.md`: SPEC-47（v0.1→0.2）を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証内容へ置換。`→FND-84` バックリファレンス付与。✅ 完了
- `doc-system/02-what/02-nfr.md`: NFR-1（v0.3→0.4）本文の「YAML フロントマター」記述を「インライン YAML ブロック（`<details>` 内埋め込み）」に訂正。`→FND-84` バックリファレンス付与。✅ 完了
- `doc-system/02-what/03-spec.md`: SPEC-44（v0.1→0.2）の NFR-1 への `ref_version` を `"0.3"`→`"0.4"` に更新（NFR-1 MINOR バンプに伴うドリフト解消）。✅ 完了
- `doc-system/04-verification/02-findings.md`: FND-84 を `resolved` へ更新。✅ 完了（本 DD 適用で）
