# オーナーの決定を捕捉する

設計議論で確定したオーナー判断を既存の `feedback_ledger` に記録する。
記録境界の正本は [`feedback_ledger/README.md`](../../../feedback_ledger/README.md#台帳と-adr540の境界)。

## 1. 捕捉対象を判定する

- 全ツール共通の方針決定は台帳だけに記録する。AI案の承認も対象となる。
- 実際のオーナーによる却下・訂正も判断である。何を却下したかを表すtopicと、
  実際の判断日時・逐語を記録する。質問や不満を全面却下へ推測変換しない。
- planの無修正承認は台帳にもADRにも新規記録しない。
- planの修正・条件付き承認は台帳とADRの両方へ記録する。
  ADRから台帳IDを参照し、オーナー逐語をADRへ転載しない。台帳からADRへ参照しない。
- ownerがfindingを覆した判断は台帳へ記録し、#523の捕捉契約にも従う。
  ロール間の覆しはカルテだけに残す。review_system/doc_systemのDDは対象外。

逐語を伴わない設計理由はADRの記録境界に従う。AIの提案そのものをオーナーが
承認した過去決定として登録しない。同一判断を複数entryへ重複登録しない。

## 2. 根拠を確認し下書きを作る

1. 判断の対象・範囲、実判断日時、出典Issueと逐語を確認する。未確定値を推定で埋めず、
   未確認点と選択肢をオーナーへ返す。元案の記録日時は却下日時の代用にならない。
2. `tmp/_feedback/<id>.toml` に下書きを作る。必須キーとテーブルは
   [`LEDGER_SPEC`](../../../feedback_ledger/schema_ledger.py) を正本とする。
   `schema` は `feedback_ledger.schema_version.LEDGER_CURRENT_SCHEMA` の現行版を明示する。
3. topicは30字以内で判断内容を表す。IDは `FBK-<YYYYMMDD>-<slugify(topic)>`。
   slugは既存 `doc-system-v2/slugify.py` を `feedback_ledger.slugify_ref.slugify_topic` 経由で使う。
4. 方針決定は `decision_point = "policy"`、主題は既存7テーマから選ぶ。
   `divergence = "approval"` は捕捉対象のAI案を変更せず承認した判断に使う。
   AI原案を訂正した判断は `reversal` 等の既存語彙を使う。
5. `overridden_role` は実際に原案を示したrole、`recorded_by` は記録者。
   `affected_assets` は実在する対象資産を列挙する。
6. `[[source]]` はIssueごとに分け、PR・round・finding_idsが同じIssueの根拠か確認する。
   議論由来でPR等が無い場合は `pr = 0`、`round = 0`、`finding_ids = []` とする。
7. `narrative.owner_verbatim` は逐語だけ。他の欄へ背景、AI原案、原案の理由、不確実性を分ける。
   未記録の理由を創作しない。推論欄は必ず `推測：` で始め、推測であることを保つ。
8. 既存の承認済み決定を訂正する場合だけ `supersedes` に旧台帳IDを設定する。
   却下された未承認AI案を旧決定として新規投入しない。既存entryは版・バイトとも変更しない。

## 3. CLIで確定し導出ビューを更新する

```bash
python3 -m feedback_ledger new-entry --from tmp/_feedback/<id>.toml
python3 -m feedback_ledger check --canonical
python3 -m feedback_ledger status
python3 -m feedback_ledger render
```

確定先 `.ai/feedback/ledger/` を直接編集しない。終了コード0を確認してからrender出力で
導出ビューを更新し、出力一致を確認する。L4/L5を避けるため逐語を書き換えてはならない。
真正な逐語の誤検出は出典・理由と値全文一致の限定allowlistで処置する。
CLI失敗は成功として記録せず原因を直す。引用の訂正も新entryと `supersedes` で行う。

## 4. 引き渡す

新ID、出典、導出ビュー、検証結果、残る不確実性を報告する。
commit・push・PR投稿はセッションの認可とリポジトリ規約に従う。
