# #371担当文脈のLEDGER_SPEC確認

Codex（AI）、2026-10-17。開始baseは main `418807f93967b1c2de056425ca035c63f1a62a06`。
本報告は #371 の工程8ロール、CP/VDのowner decision参照、ADR境界を対象とする。
#537全体、既存決定の投入作業、#523担当文脈の確認を完了と判定するものではない。

## 確認範囲と訂正

`feedback_ledger/schema_ledger.py::LEDGER_SPEC` の宣言だけでなく、
`schema_utils.valid_overridden_role`、`model_identity._check_document_identity`、
`cli_entry.py` の投入前検査と `.ai/schema/feedback-ledger-v1.json` を照合した。
開始baseでは旧4ロールと `skill:<name>` のみが許可され、新6ロールは L1 ERROR で拒否された。
以前の「文字列なのでenum追加不要」「欠落なし」という報告を撤回する。

是正では `schema_values.py` の語彙と JSON Schema を同期し、
`issue-investigator` / `ac-designer` / `change-planner` / `plan-reviewer` /
`test-writer` / `adviser` を v1.2 から追加した。旧4ロールとskill語彙は維持する。
`recorded_by` が主文脈でも、覆された対象は当該ロール名で記録する。

## 必要欄と検査根拠

| 必要な情報 | 既存欄・検査 | #371での確認 |
|---|---|---|
| 識別・版・主題 | `schema`, `id`, `topic`, `theme` | supported minor/ID導出/30字制限/版別theme条件を維持 |
| 判断の分類・対象 | `decision_point`, `overridden_role`, `divergence`, `confidence_of_inference` | role不足をv1.2で是正。他の既存分類語彙は維持 |
| 発生・記録・適用先・置換 | `occurred_at`, `recorded_by`, `affected_assets`, `supersedes` | 日付型、実在path、ledger参照の既存検査を維持 |
| 出所 | `source[]` の `issue`, `pr`, `round`, `finding_ids` | repeated source・Issue必須・任意値の0/空表現を維持 |
| 背景・AI推奨・理由 | `narrative.background`, `recommendation`, `recommendation_reason` | 必須本文として分離 |
| 不確実性・owner逐語・推定 | `narrative.uncertainty`, `owner_verbatim`, `inferred_reason` | 逐語と推測の分離、L4/L5の既存検査を維持 |

CP/VDの `owner_decisions` はledger ID参照だけを持つ。
`feedback_ledger/README.md` と `adr/README.md` の現行境界に従い、逐語を伴う判断は台帳、
逐語を伴わない設計理由はtool別ADR、条件付きplan承認は双方へ記録する。
ADRからledgerへの片方向参照を維持し、逐語をADRへ転載しない。
共通ref adapterは `DocSpec` / `Field(ref=...)` を読むため、CP/VD欄名の個別追加は不要。
run/phase/work unit/digestは工程artifactの束縛であり、owner判断の欄ではない。
#409用の別実行ledgerも新設しない。

## 版・投入への影響と #537 の境界

`audit/2026-09-21-pipeline-redesign/README.md` の2026-09-22 v1据置判断は
source repeated化とエントリ0件の間に限定される。
`FBK-20261009-後方互換変更でminorを上げられる仕組みにする` のowner逐語、
AGENTSの版変更規則、`feedback_ledger/README.md` のminor運用に従い、
今回の後方互換追加は **v1.1→v1.2の1回** とする。major 1とJSON Schemaファイル名は維持する。

既存 v1/v1.0/v1.1 の読取・canonical検査は維持し、既存entryの版・バイト列は変更しない。
新6ロールを旧版に指定するとPython/JSON双方で拒否する。
`new-entry` は従来通り現行版だけを受け付けるため、新規draftはv1.2を明記する必要がある。
旧draftの自動書換えや既存決定移行は実施しない。

#537と生存決定が「#371後に追加」とするのは **DECISION_POINTS / DIVERGENCES** の2語彙である。
本是正のrole許可追加とは区別し、その2語彙の追加・既存決定投入は変更していない。
#371担当範囲で発見したrole不足は本差分で処置し、他の必要欄は上表の既存契約で表現できると確認した。
#537はこの担当別結果と、他担当の結果・既決の2語彙拡張・投入条件をそれぞれ確認する必要がある。

## 実施証拠と受渡し条件

`tests/unit/test_feedback_ledger_roles.py` は、新6ロールそれぞれのCLI投入・保存後canonical検査、
対応全版でのPython identity検査とJSON pattern/版条件の一致、未知roleの投入前拒否を検査する。
既存のfeedback ledgerテスト群と合わせ112件成功。実リポジトリの
`feedback_ledger check --canonical --require-base` とmaintainability検査の結果は
本PRの検証記録から確認する。全27ACの監査結果は [AC-EVIDENCE-371.md](AC-EVIDENCE-371.md) に残す。

2026-10-17の開始base監査では #537 最新受領記録
[6214228158](https://github.com/hiratashinnya/review-system/issues/537#issuecomment-6214228158)
に #371 担当結果がなく、AC18はpartialだった。
最終的な受渡し証拠は、#537の **#371担当結果を特定するコメント** と本後追いPR本文にある
報告・対象head/OID・受領URLを照合する。文書の存在だけでは引渡し完了にしない。
外部引渡しと受領確認は主文脈が実施し、是正担当のローカル検証で代替しない。
