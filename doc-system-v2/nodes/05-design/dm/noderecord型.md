> **改訂理由（z バンプ v0.1.0→v0.1.1・FND-101 辺逆転コホート backref）**: FND-107（resolved）の辺逆転（DD-16）完了に伴い、処置対象である DM-1 に `→FND-107`（ref_version "0.1"＝FND-107 現バッジ x.y）バックリファレンス辺を付与（DD-3）。バックリファレンス辺追加は内容のみ変更のため z バンプ（DD-8 §4・ドリフト非誘発）。なお当初 FND-107 を MINOR バンプし ref を "0.2" としていたが、Q-5/DD-21（辺逆転は z）により FND-107 が v0.1.2 へ訂正されたため ref も "0.1" に修正。

**Python クラス**: `NodeRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: パース結果の単一ノードを表す不変値オブジェクト。フロントマター YAML の各フィールドと辺情報を保持し、各検査モジュールが消費する。
**フィールド**:
- `id: str` — ノード ID（型 prefix + 連番）
- `type: str` — 型値（MOD / DM / SPEC 等）
- `labels: list[str]` — ラベル群
- `scheduled: str` — スケジュール（空文字＝即時）
- `edges: list[EdgeRecord]` — 依存辺リスト（DM-2）
- `condition: str | None` — condition 属性（SPEC/TD/TC 等のみ）
- `result: str | None` — 実行結果（TR のみ）
- `log_ref: str | None` — ログ参照（TR のみ）
**不変条件**: `id` は非空かつ一意。`edges` の各要素は EdgeRecord。`condition` は config の `condition_vocab` 語彙に属す（保持時は任意・検査は別モジュール）。
**実現する D**: D-4（構造化ノードセット）

> **改訂理由（MINOR バンプ v0.1→v0.2・issue #118 後続）**: suppress 機構廃止に伴い、NodeRecord から `suppress` フィールドを除去した。scheduled は現行のフェーズ限定発火指定として残す。
