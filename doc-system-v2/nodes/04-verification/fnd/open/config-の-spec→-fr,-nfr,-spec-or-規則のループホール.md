**深刻度**: WARNING
**内容**: FND-24 処置で config.yaml の `must_link_to: SPEC` を `target: [FR, NFR, SPEC]` に拡張した。この OR 判定では SPEC→SPEC 辺（親 SPEC への辺）だけで RULE-006 を満たせるため、`-N` 採番の子 SPEC を意図した設計だが、任意の SPEC→SPEC 辺（兄弟 SPEC・無関係な SPEC への辺）でも合格してしまい、本来必要な FR/NFR への上流接続を機械検査で強制できない抜け穴がある。現存する全 SPEC に `-N` 子パターン以外の SPEC→SPEC 辺はないため現時点は実害ゼロだが、今後 SPEC が増えると意図しない抜け穴になり得る。
**推奨**（次スプリント対応・本スプリントは起票のみ）: ① config/inspector に SPEC→SPEC の「子孫型」制約（target SPEC の ID が自ノードの `-N` 直接親であること）を追加、② SPEC-48 本文に運用ガイドとして「SPEC→SPEC 辺は `-N` 採番の直接親のみ」を明記、③ spec-inspector 実装時に SPEC→SPEC 辺の有効性を `-N` suffix で追加検証するロジックを組み込む。**推奨は ②＋③**（記法ガイドで運用ルールを明記しつつ、実装時に inspector ロジックで補完。①の config だけでは ID パターン照合が config スキーマを複雑化する）。
**対応状況**: open（**オーナー承認済み sprint-2** — 2026-06-14・独断のスケジュールではなくオーナー判断で sprint-2 に確定）
**指摘時 ref_version**: SPEC-48 "0.1"（ノードバージョン基準・DD-8。当初記録の file x.y="0.3"〔spec.md v0.3.6 時点〕は DD-8 移行で SPEC-48 ノードバッジ x.y="0.1" に再基準化）
