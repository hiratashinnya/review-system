# #371担当文脈のLEDGER_SPEC確認

Codex（AI）、2026-10-16。

確認対象は `feedback_ledger/schema_ledger.py` のLEDGER_SPEC、
`feedback_ledger/README.md` のADR境界、`adr/schema.py` と `adr/index.py`、
`audit/2026-09-21-pipeline-redesign/README.md` の生存決定である。

- 8ロールに必要なowner判断は `overridden_role`（文字列）とsource Issue/PR/round/findingで表現できる。
  本Issueの新ロール名を許すためのenum追加は不要。
- owner逐語・推奨と理由・不確実性・推定理由は既存narrativeに分離して保存できる。
- affected_assets、supersedes、source、occurred_at、recorded_byを持ち、判断と根拠・適用対象を追跡できる。
- CP/VDのowner_decisionsは既存ledger ID参照のみ。逐語を含まない実装理由はtool別ADRへ置く。
  ADRからledgerへの片方向参照を維持し、owner逐語をADRへ転載しない。
- common ref adapterは既存DocSpecを受け、CP/VD発生源がrefを宣言する。欄名をadapterへ追加しない。
- run/phase/work unit/digestは工程artifactの束縛でありowner決定ではないため、LEDGER_SPECへ追加しない。
  #409用の別実行ledgerは新設しない。

#371の責務境界で、LEDGER_SPECに必要欄の欠落は認めなかった。これは#537全体の完了判定ではない。
#537へ渡す確認結果はこの文書と実装差分であり、enum追加を#371より先へ動かさない。
#537への外部投稿は主文脈へ引き渡し、投稿済みとは扱わない。
