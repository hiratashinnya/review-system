# Harness ADR

Codex (AI) による Issue #540 の実装。標準ライブラリのみを使い、判断の内容を道具ごとの `<tool>/adr/*.toml` に保存する。review_system/doc_system の既存判断は移行しない。

```bash
python3 -m adr new-entry --root issue_start/adr --draft draft.toml
python3 -m adr render --root issue_start/adr
python3 -m adr todo --root issue_start/adr
python3 -m adr stale --root issue_start/adr --days 14
python3 -m adr check --root issue_start/adr --repo . --require-base
python3 -m adr file-issue --root issue_start/adr --id ADR-20261016-判断を残す
python3 -m adr file-issue --root issue_start/adr --id ADR-20261016-判断を残す --create
python3 -m adr deps --root issue_start/adr --id ADR-20261016-判断を残す
```

`file-issue` は既定で本文下書きを表示する。`--create` で GitHub に Issue を起票し pending→filed と番号を書き戻す。作成後の書戻しに失敗した場合は出力された番号を `--issue <番号>` で復旧できる。再起票の前に GitHub 上の作成結果を確認する。`--repo` は GitHub の対象リポジトリでもあるローカルcheckoutを指定する。

初回は `schema.py` のすべての欄を下書きへ記載する。`id` のみ省略でき、`decided_at` と正本slugifyから自動生成する。`source` と `alternatives` は最低1件。空値も明示する。`topic` は30字以内。`tracking_status` は必須で、`pending` は番号・理由とも空、`filed` は正の番号のみ、`not_needed` は理由のみを持つ。逐語を伴うオーナー決定は feedback_ledger が正本で、ADR には `owner_decision_refs`（FBK id配列）だけを記録する。台帳の正規表現を再利用して書式と参照実在を検査する。

`check` は単体スキーマ・資産実在・参照実在・置換循環・canonical一致・merge baseからの不変性を検査する。本文訂正は新ID＋`supersedes` で行う。唯一の更新例外は実行メタデータの pending→filed（番号書戻し）。topicの訂正等で既存IDを再計算しない。base未解決は明示WARN、`--require-base` は失敗とする。`render` の active/superseded は置換参照から導出し、保存しない。`todo` は全pending、`stale` はOPENかつ updatedAt が閾値を超過したfiledを返す。GitHubへのアクセスに失敗した場合、監査を成功扱いにしない。

`deps`/`dependents`/`orphans`/`index` は `harness_trace` がDocSpecのref宣言から作った索引を dsv2.query に渡す。ADR rootと台帳を集約し、`--envelope <永続JSON>` は複数指定可能。JSONには `doc_spec: {kind, schema, tables: [{name, repeated?, fields: [{name, kind, ref?}]}]}` と `document` を置く。kindはChangePlanまたはVerificationDesign。#371のenvelope本体形式を定めず、各発生源が自分のDocSpecを提供する境界である。Python利用者は `harness_trace.build_index([(spec, data, path), ...])` に直接渡せる。参照欄名を共通adapterに追加する必要はない。

PostToolUse の `adr.hook` は Bash / context-mode 実行のnew-entry/file-issue直後にpendingを `systemMessage` で通知する。CLI自体も同一書込操作内で通知JSONを出す。hookは助言専用で、読取不能等はstderr診断後に継続する。

## 記録境界

逐語を伴わない設計理由（why・代替案・帰結）は道具別 ADR が正本で、`recorded_by` はロールでもよい。
逐語を伴うオーナー決定の正本は [台帳の境界規則](../feedback_ledger/README.md#台帳と-adr540の境界) に従う。
ADR に逐語を転載せず `owner_decision_refs` で台帳 ID を参照する。plan の修正・条件付き承認は両方に記録し、
無修正承認は新規記録しない。全ツール共通の方針は台帳だけに記録する。既存判断の一括移行は行わない。

設計理由・凍結セットは [rationale](rationale.md)、テスト設計は [TD](../issue_start/verify/designs/TD-adr-540.md) を参照。
