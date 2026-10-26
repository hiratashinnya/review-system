---
id: TD-agy-runtime-628
version: 1
condition: failure
---
# 目的

Issue #628 の本番未確認停止を維持し、版・設定層・起動環境の根拠を取得した後に解除するための残余検証を定義する。本文の手順は計画であり、今回テスト・実機・CLIを実行する指示ではない。

# 前提

PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e` が下段。
本番 `output_contract.CONTRACT_VERSION` と `version.verified_version` の受理版は1.3.3のままである。
1.3.5のduration観測、1.4.6のA2/B1表示・復元は履歴で、現在版の保証ではない。
現在binaryは旧B1のexe指紋と不一致、現在版は未照会でunknown。新hashを1.4.6や1.3.3と同定しない。

最新の限定読取ではM0・R不存在・project canonical元一致・他3file元一致を確認したが、project rawbytesは不一致で旧cleanup/proof未認定、旧reader終了もunknownである。これを通常run・engine効力・全層合成・5UCの成功へ転用しない。
観測の正本は [実測報告](../../docs/methods/agy-runtime-evidence-628.md) と対応OBS。既存の分類・会話・画像・排他等の共通試験は [TD-agy-delegate-606](TD-agy-delegate-606.md) に従い、ここへ重複定義しない。

同じ未merge上段PR内のTD是正でありversion 1を維持する。過去TR/logに記録された当時の版・成績を遡及変更しない。

# 未確認8理由と必要な根拠

次は `runtime.py` の4理由、`settings_layers.py` のinventory不足1理由、追加3理由をsourceから照合した一覧である。今回の試験実行結果ではない。

| 本番の理由 | 解除前に必要な根拠・残余検証 |
|---|---|
| `settings_global_binding_unverified` | 対象版/hash・user/home/Wと実参加globalの結合。期待ルール用Request.settingsを実参加元の代替にしない |
| `settings_project_binding_and_schema_unverified` | selector/cwdとproject選定、参加file名・全permissions schema。候補root idやUI保存位置だけで認定しない |
| `settings_shared_user_location_and_schema_unverified` | 共有userの参加位置・schema・省略値の扱い。空/欠落の観測だけで正のdecoderを確定しない |
| `settings_admin_presence_or_precedence_unverified` | 対象Windows版でのadmin参加元、明示不存在と未読/拒否の区別、優先順 |
| `settings_layer_inventory_incomplete` | 4層が各1件、全て読取・不存在判定・decoderの根拠が揃うこと。未知層を飛ばさない |
| `settings_permission_merge_unverified` | 重複/異rule/allow・ask・deny競合と優先の対称測定。現保守的監査の和集合をengine合成と扱わない |
| `launch_environment_unverified` | 同じ版/hashでWSL/native cwd・path/URI・selector継承をsentinelで確認。観測workerのcwdをagy本体のcwdと混同しない |
| `print_timeout_format_unverified` | 採用する同じ版のduration構文・timeout時stdout/stderr/exit。1.3.5や1.4.6の15sを1.3.3/現在unknown版へ転用しない |

# adapterの残余設計と検証順

以下は未実装・根拠待ちの設計順であり、schema/merge/UNC/durationを確定するものではない。独立した既存adapter設計は無かったため、本TDに必要最小限を集約する。

1. 対象cohortを先に決める。1.3.3の再取得か、現在binaryを別途承認された手段で版同定して新契約を取得するかは未決。版・exe hash・OS・user/home・W・起動mode/selectorへ根拠を束縛し、いずれかが変われば未確認へ戻す。現在unknownのまま定数だけを更新しない。
2. `runtime.resolve_settings_layers` はread-onlyの参加元解決、`SettingsLayer.decode_permissions` は各実測schemaの境界変換に限定する。`SettingsResolution` が揃っても、合成根拠なしで `verify_runtime` を合格させない。CLI入力や呼出元自己申告に検査注入の入口を作らない。
3. `inspect_layer_resolution` の保守的監査と、将来の実効merge判定を分離する。globalの広いallow13が復元されている履歴、corpus deny/追加rule/askの不足・競合を隠さず停止する。read-only resolverは設定を自動修正しない。
4. `process.execute` / `version.verified_version` / `output_contract` は同じcohortに結合する。native path/cwd変換とduration引数は根拠が揃ってから実装し、shell文字列へpromptを連結しない。既1.3.3通常出力fixtureとlocal command envelopeを混ぜない。
5. commitで試験対象を固定し、偽fixture→異常時未起動→独立レビューを先に確認する。その後、別途承認された安全な設定/環境でのみ実機UCへ進む。未確認理由を削る、merge guardのskip/削除/期待値反転で緑にする方法は採らない。

# 手順

実装・試験が別途許可された後、対象commitとTD版を固定し、`python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'`、maintainability_lint、asset_parityを実施してTD/TC/TR/logを対応付ける。今回の編集では実施しない。

| fixture/対象 | 期待する検証 |
|---|---|
| 4層不足・未知path/schema・未読・JSON不正/重複key | 本番runのexecuteと版probeを含むagy子起動0。実設定は読まず偽fileだけを使う |
| admin既知不存在・読取拒否・再出現 | 区別した停止理由。不在をエラー握り潰しで作らない |
| 正しい期待template＋実参加globalの広いcommand/ask競合/corpus deny欠落 | Request.settingsが正しくても未起動。呼出元ready/自己申告で解除しない |
| fake全層監査合格、merge/launch/durationの根拠だけ不足 | 未確認理由を保持してexecute0。fixture監査成功は実機互換性ではない |
| 対象外版/hash・user/home/W/selector変更・path alias/symlink | 既根拠の適用を拒否。UNCや文字列置換だけで別pathを同一視しない |
| 実装済みcohortのversion/argv/result境界 | 既TD606の成功/静かな拒否/ERROR/timeout/未知stderr/壊れたJSON分類を維持。版probe失敗後はprompt起動0、probe自身の実行数を隠さない |

新しいresolver/decoder/merge/launchのpublic関数を実装した場合は、関数単位のunittestへ上表を割り付ける。既合成processの数値文字列・外側timeout検査を、対象版のduration受理の実測にしない。

local slashや版照会も、起動時正規化等の設定作用があり得る。将来の再観測には具体scope・退避/比較/復元条件・原memory/終了確認・独立レビュー・owner認可を要し、既承認を新しい層変更/モデル起動へ転用しない。CLI名だけから無課金・無推論・書込なしを保証しない。

## 実機5UCの残余

全層/起動/許可効力の根拠と安全な使捨てfixtureが揃った後だけ行う。実corpus・認証を拒否試験に使わない。

| UC | 最低限の記録・確認 |
|---|---|
| 影響調査 | 入力anchorを読んだ根拠、対象範囲、未検証部分、非意図の変更なし |
| 素案 | 対象範囲と正本境界、返却成果を呼出元が検証し採用可否を別判定 |
| 外部調査 | 実際の外部取得根拠と出典、未取得を成功化しない |
| 画像生成 | 新規会話/画像差分、返却IDとartifact対応、旧画像fallback拒否 |
| 並列 | 会話/run/workspaceの分離・排他と各結果の成功/拒否/失敗を保持 |

各UCで同じ版/hash/cohort・設定条件・実argv/cwd・状態分類・使用量/課金条件・成果検証・残余制約を秘匿化して記録する。token0の表示観測をモデルUCの代替にせず、自動retry/課金fallbackを加えない。

# 期待結果

現在は8理由による通常run未起動と、merge guardの意図的失敗を維持する設計である。今回のTD編集ではその試験を実行していない。対象cohortの根拠・adapter・異常系・5UC・独立レビュー・#607向け残余引継ぎが揃って初めてIssue #628のACを判定する。

この変更はTDのみ。runtime理由・版定数・本番コード・TC・既存TR/log・実設定・keeperは変更しない。現在の観測や終了状態unknownを、将来の計画やfixture成功で解消済みにしない。
