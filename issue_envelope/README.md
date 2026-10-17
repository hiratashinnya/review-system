# Issue工程artifact

`issue_envelope` は共通コードだけを持つ。CP/VDはIssue本文の包含木配置へ直接TOMLで永続化し、IR/TDは `investigation_report/IR-<issue>.toml` と `test_design/TD-<issue>.toml` に置く。`store.write` は新規作成専用で暗黙上書きを拒否する。改訂のcommitは呼び出す成果物ロールが行う。

`python3 -m issue_envelope check --repo .` は型・canonical・包含木・独立したwork_units DAG・共通ref参照・AC網羅・STOPを検査する。`index` はADR/feedback ledger/工程artifactを共通adapterで統合し、`show --id VD-371` は復元した内容を表示する。`deps --id ID` / `dependents --id ID` / `orphans` は索引を直接照会する。`query` は既存 `dsv2.query.deps/dependents/orphans` を再公開する。

実行直前には `handoff.validate_handoff(document, expected)` を呼ぶ。期待値には `producer/phase/issue/run_id/target_key/input_digest/snapshot_oid/artifact_type/input_refs` を全て呼出側から与える。CPでは `ac_refs` も必要である。documentの自己申告を期待値へコピーして認可してはならない。digestは入力artifact集合に対する呼出側の信頼済み値、OIDは呼出側の観測した現在snapshotを渡し、任意の値が異なればstaleとして拒否する。owner_decisionsは既存ledgerの参照だけ、未決は `unresolved_owner_decisions` に明示する。

# 設計理由（暫定実装判断）

包含はノードID、実行順はwork_unit IDで検査する。ルート/中間/葉のスキーマは同じであり、親のscopeは子のscopeを包含する。ノード間の `depends_on` と `work_units[].depends_on` は別のDAGである。

葉の物理名はIssue契約どおり `<target>/verification_design/VD-371.toml` 等を維持し、IDは `VD-371-<target-slug>` とする。ルートと葉を同名IDにすると既存harness_traceのglobal一意IDに衝突するため、葉だけIDとstemを分離する。これはオーナー決定の引用ではなく、既存trace境界へ整合する暫定設計である。

ADRのschema/check/CLI、既存Field/TableSpec/DocSpec、TOML正規化/直列化、共通refアダプタ、dsv2 queryは再実装しない。queryの索引は毎回生成する導出物であり、新しいrun/決定台帳を作らない。run/phase/dependency/next_expected_artifactは将来#409へ渡せるがAgentRun自体を実装しない。review結果の取込は#375/#310の既存karte境界に委ねる。

`snapshot_oid` はartifact作成前の入力ソースsnapshotを指す。artifact自身を含むcommit OIDを埋め込む自己参照はしない。callerは祖先性とその後の差分が同Issueの正当な工程artifactのみであることを検証し、通常source変更があればstaleとして拒否する。artifact自身のbytes digestと入力集合の `input_digest` は別に照合する。


# TestDesign の実体とRed証拠

`ut_td` / `ut_tc` はID文字列ではなくrepo相対ファイルpathで、`Field.path_ref` 宣言をSSoTとして検査する。各pathはrepo内の通常ファイルでsymlinkを経由せず、HEADにcommitされ、作業面のbytesがHEAD blobと一致しなければならない。存在しない、未commit、改変済みのTD/TCでは `check` が失敗する。2b入口も同じrepo検査を行う。

TestDesignにはUT-TCごとに一つの `[[red_evidence]]` を記録する。`tc` / `tc_sha256` はレビュー対象のテストコード、`log` / `log_sha256` は非空の実行ログを指す。`command` は実行コマンド、`exit_code` は正の非zero終了コード、`failure_reason` は `implementation_missing` とする。logも `path_ref` 宣言に従う同じ実在・commit・bytes検査を受ける。TD/TC/ログを先にcommitし、そのbytes/hashをTestDesignへ記録する。独立2a reviewerはTCとログを読み、失敗が本体未実装による期待したassertionであることを確認する。syntax/importエラー・環境不備・テスト収集失敗をRed完成と認めない。機械検査は実行結果の意味を自己認定せず、独立レビューreceiptがTestDesign bytes digestを束縛する既存契約で、この確認対象を固定する。

CP/VDの葉の配置は `scope` に列挙したtargetのいずれかと完全一致する `<target>/<kind>/<prefix>-<issue>.toml` に限る。複数scopeの葉でも無関係なtargetや暗黙の親子directoryは許可しない。多階層targetはその全pathをscopeへ書く。ルート/中間グループは複数targetを包含しrepo直下に置く。

schema `issue-envelope/v1.0` は本PRで初導入された未merge契約である。本是正はその同一PR内の未完成な実体/証拠契約を補完するため、共通guidanceの「1回のPRで版を複数回上げない」に従い追加bumpしない。

2aのTestDesignには非空の単一 `work_unit` を必須とし、handoffもtrusted callerの同名期待値と完全一致させる。TestDesignの `input_refs` は承認済みCPのID一つ、`input_digest` はそのCPのcommit済みbytesのSHA-256とする。VDはCPを介して参照する。2a著作者と独立reviewerはCP内の同じunitを検査し、別unitや欠落を受理しない。target_keyはunit IDの代用ではない。2bの消費TDも同じCP/digest/unit/run/Issue/target/snapshotへ束縛する。これは同一PRの未merge契約の補完であり、既存の版遷移を再bumpしない。
