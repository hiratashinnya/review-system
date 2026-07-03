**パス**: `spec_inspector/domain.py`
**責務**: NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice / CoverageReport / InspectionViews 等の値オブジェクトを定義する。
**公開 I/F**: `NodeRecord`, `EdgeRecord`, `ViolationRecord`, `ConfigSlice`, `CoverageReport`, `InspectionViews`
**依存**: なし（最下層・他のどの層にも依存しない）
**依存方向**: domain（被依存される最下層）

> **改訂理由（MINOR バンプ v0.1→v0.2）**: FND-96 選択肢A（DM→MOD→D 正規化）。MOD-1 は処理プロセスを実装しないため P-1 辺を削除し、realize するデータ型概念 D-4/D-6/D-9〜D-21 への辺へ変更。`→FND-96` バックリファレンス付与。
>
> **改訂理由（MINOR バンプ v0.2→v0.3）**: PR #32 レビュー対応（DM→MOD→D 対称化・FND-100）。FND-96 処置後に残った DM↔D 被覆の非対称を是正。D-5（パース段違反リスト・DM-3 ViolationRecord が realize）と D-7（カバレッジ計測結果・DM-5 CoverageReport が realize）への realize 辺を追加し、`DM→MOD→D` チェーンの被覆漏れを補完。D-17〜D-21 は既存辺あり（DM-6 InspectionViews が realize）。型変更・構造変更なし（辺追加のみ）のため MINOR。`→FND-100` バックリファレンス付与。
>
> **改訂理由（z バンプ v0.3→v0.3.1・DD-8 §4）**: FND-110 被参照アンカー付与（`→FND-110` ref "0.1" 追加）＋FND-96 backref ref を是正後バッジ "0.4" へ整合訂正（"0.3"→"0.4"・FND-110/DD-21 適用是正）。辺追加・ref 訂正はいずれも downstream 無影響の provenance/lifecycle 操作＝DD-8 §4「backref 辺追加＝z バンプ」に該当（issue #40・2026-06-28）。
