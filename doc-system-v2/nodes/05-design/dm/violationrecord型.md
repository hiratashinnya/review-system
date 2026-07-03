**Python クラス**: `ViolationRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: RULE 検査結果の違反 1 件を表す不変値オブジェクト。パース段（MOD-4 parser）と各 checker モジュールが生成し、filter（MOD-6）・reporter（MOD-8）が消費する。
**フィールド**:
- `severity: str` — 深刻度（error / warning）
- `file_ref: str` — 違反検出ファイルパス
- `rule_id: str` — 発火ルール ID（RULE-xxx）
- `node_id: str | None` — 違反ノード ID（ファイル全体違反時は None）
- `message: str` — 違反メッセージ
**不変条件**: `severity` は `error` / `warning` のいずれか。`rule_id` は非空の RULE 識別子。`message` は非空。
**実現する D**: D-5（パース段違反リスト）/ D-6（RULE 違反リスト）/ D-7（カバレッジ計測結果・グラフ網羅性穴リスト部分のみ。FR×condition テーブル部分は DM-5 CoverageReport が担う）

> **改訂理由（MINOR バンプ v0.1→v0.2）**: PR #32 レビュー対応（DM→MOD→D 対称化・FND-100）。D-5（パース段違反リスト・RULE-023〜028）は D-6 と同形の `list[ViolationRecord]` でありながら ViolationRecord 型へ realize されていなかった（DM↔D 被覆の非対称）。型は同一（同じ「もの」＝違反レコード 1 件・発生源差は生成元プロセス P-1/P-2 で既表現）のため新規型を作らず「実現する D」に D-5 を追加。`→MOD-1` ref_version を MOD-1 更新後バッジ "0.3" に追従。`→FND-100` バックリファレンス付与。

> **改訂理由（MINOR バンプ v0.2→v0.3）**: PR #32 再レビュー 🟡 指摘対応。DM-5（CoverageReport）本文が「D-7 の穴リスト部分は DM-3 が担う」と明記しているが、DM-3 の「実現する D」に D-7 が未記載で prose 非対称だった。推奨案 (a) に従い「実現する D」に D-7（穴リスト部分のみ）を追記して対称化。構造変更・edges 変更なし（辺追加不要・D-7 の MOD-1 realize 辺は既存）。
