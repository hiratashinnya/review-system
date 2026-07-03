**Python クラス**: `CoverageReport`（不変値オブジェクト・`@dataclass(frozen=True)`。FR 行を表す内側 VO `CoverageRow` を保持）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: FR×condition 仕様カバレッジ計測の集計結果を表す不変値オブジェクト。spec_coverage（MOD-17）が生成し、reporter（MOD-8）がカバレッジ点検結果（O-2）として整形・出力する。
**フィールド**:
- `rows: tuple[CoverageRow, ...]` — FR ごとの充足状況行（id 昇順）
- `CoverageRow.fr_id: str` — 対象 FR の ID
- `CoverageRow.required_conditions: tuple[str, ...]` — required な condition 値群
- `CoverageRow.satisfied: tuple[str, ...]` — 実際に SPEC/TD で充足された condition 値群
- `CoverageRow.missing: tuple[str, ...]` — 未充足の required condition 値群
- `CoverageRow.covering_specs: tuple[str, ...]` — 充足元の SPEC/TD ノード ID 群
**不変条件**: `rows` は frozen（生成後変更不可）。各 `CoverageRow.missing` は `required_conditions` の部分集合かつ `satisfied` と素。`fr_id` は非空の FR 識別子。
**実現する D**: D-7（カバレッジ計測結果・FR×condition カバレッジテーブル部分。グラフ網羅性穴リスト部分は DM-3 ViolationRecord が担う）

> **新設理由（FND-100・PR #32 レビュー対応）**: D-7（カバレッジ計測結果）の FR×condition カバレッジテーブル部を表す novel 型。違反でない計測集計値であり ViolationRecord では表せないため別の「もの」として新設（PR1）。MOD-17 が `measure_spec_coverage(...) -> CoverageReport` で型名を既に命名済み。`→FND-100` バックリファレンス付与。
