**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-47 "0.1"`・`→DD-8 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-47 から `→FND-84` の backward 辺を受ける（backref 付与）。DD-8 は provenance（本文記録のみ・backref なし）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: DD-8（2026-06-14 確定・反映済）でファイル frontmatter `version:` は全廃され、版管理はノードバッジ x.y に移行済みである（config.yaml 冒頭・FND-39・ダッシュボードで確認）。しかし SPEC-47 は「全 in-graph ファイルの frontmatter に `version` フィールドが存在する」ことを ERROR 要求し、SPEC-44（NFR-1）も「YAML フロントマター」を前提にしている。廃止済みの frontmatter を必須化する仕様が残存しており、DD-8 と直接矛盾する。さらに「観測できないものを持たない」原則（PR4）にも反し、検証ツールが存在しない frontmatter version を ERROR 報告してしまう。
**推奨**: SPEC-47 を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証へ置換、または廃止する。SPEC-44 の本文から frontmatter 前提を除去し、プレーンテキスト/UTF-8 検証に限定する。NFR-1 本文（フロントマター言及）の見直しも要。DD 昇格が望ましい。
**対応状況**: resolved（DD-10 / 2026-06-14）
**指摘時 ref_version**: SPEC-47 "0.1"／DD-8 "0.1"（いずれもノードバッジ x.y 基準・DD-8）
