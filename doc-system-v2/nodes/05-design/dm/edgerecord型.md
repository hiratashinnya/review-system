**Python クラス**: `EdgeRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: NodeRecord 内の単一の無名依存辺を表す不変値オブジェクト。参照先 ID と参照時バージョンを保持し、ドリフト検査（MOD-5）が消費する。
**フィールド**:
- `to: str` — 参照先ノード ID（単数）
- `ref_version: str` — 参照時の参照先バッジ x.y
**不変条件**: `to` は非空の単一 ID（配列不可）。`ref_version` は `x.y` 形式の非空文字列。`kind` / `status` フィールドを持たない（無名依存辺）。
**実現する D**: D-4（構造化ノードセット）
