# DD-AGY-628: 実測snapshotだけを受理する限定cohort

状態: 限定cohortの実装契約。実機UCの完了は証拠記録で別途判定し、一般的なproject/shared/admin schemaへ拡張しない。

## 判断

現1.4.8のglobal schemaと、実際にproject/shared scopeが空と表示された不変snapshotだけを支持する。未知memberを空へdecodeする方式は採らない。設定全般の意味を推定せず、校正時と異なるproject/shared bytesは拒否する。

実globalの支持policyはnative file-onlyである。Request.settingsの論理template（read/writeと限定Get-ChildItem allow）は許可の上限を表し、実globalはfile read/writeだけを残して全command denyを追加した厳しいsubsetとして別にexact監査する。論理templateと実globalを同一file扱いせず、一覧command許可を実証済みと宣言しない。native path対応はWSL canonical入力の射影とactualprocessの相対witnessを根拠とし、未知ruleや単なるpath置換を互換性証明にしない。

## 証拠の生成・保存・寿命

- 生成者はfreezeした内部校正workerだけ。通常runにproofを登録するAPI、Request.settingsやCLI/環境変数でproof pathを注入する入口は設けない。
- 原4fileはWindows保持processのmemoryにだけ保全。校正はsnapshot前後と復元結果を確認する。cohortへ保存するのはhash・存在・固定enum・比較bool・日時・source fingerprintだけで、原raw/原rule/認証/モデル本文を含めない。
- 保存先はpwd.getpwuid(os.getuid()).pw_dir配下の固定`.local/state/agy-delegate/cohorts/v1/`。HOME/XDG/CLI等で変更しない。directory0700/file0600、同UID所有、祖先を含むsymlink拒否。全fileは64KiB上限、重複JSON key/未知key/非有限数値を拒否する。
- workspaceのWSL canonical absolute pathのUTF-8 SHA256をWIDとし、indexは`WID.index.json`、proofは`SHA256(canonical proof bytes).json`。index exact schemaは`{"protocol":1,"proof_sha256":"64桁小文字hex"}`。通常runに書込経路は無い。
- publisherは同directoryの排他的`WID.publishing`をCreateNewし、proofをCreateNew0600→write/fsync→readback hash検証→directory fsync、indexをCreateNew一時file→write/fsync/readback→atomic replace→directory fsync、その後marker unlink→最後のdirectory fsyncの順とする。commitpointはmarker unlink成功である。proof/indexの全sync/readbackをその前に終える。既存同hash proofはowner/mode/bytes検証一致時のみ再利用可。
- 入力/schema不正は書込前の固定ValueError。publicationのtyped outcomeは`state`（not_started/pending/committed）、`proof_sha256`（committed時だけhash、それ以外null）、`durability_confirmed`（bool）、`phase`（固定operation名）を返す。marker作成前の失敗はnot_started、既存currentに作用せず新校正の成功へfallbackしない。marker作成後からunlink前の失敗はpending、cleanupでmarkerを消さずreaderをSTOPさせる。
- unlink成功後の最後のdirectory fsync失敗はcommitted/durability_confirmed=falseであり、publication失敗と偽分類しない。呼出側はwarningを必ず記録・表示する。クラッシュでunlinkが巻き戻る場合はmarker再出現→reader STOP、巻き戻らなければ先行durableなindex/proofだけを受理する。post-commitでmarkerを再作成するrollbackは行わない。
- 旧案の「全例外でmarker必残」は、unlink後のdirectory fsync失敗とmarker再作成失敗が重なると成立しないため撤回した（Issue #679と同型の虚偽保証を避ける）。保証はcommitpoint前の作用とpost-commit durability警告へ分ける。明示再校正だけがpending markerを処置する。
- readerはmarker不存在、index/proofのowner/mode/型/filename hash/二読安定を確認する。改変、欠落、期限切れ、権限不正はagy未起動。OS所有者によるcode/state同時の意図的改竄は信頼境界外であり、呼出元自己申告は校正証拠にしない。
- 有効期間は校正完了から24時間を上限とし、下記bindingの変化で即失効。再校正は明示操作とし通常runが自動でnative CLIを起動して修復しない。24時間はaccountや管理設定を恒久保証しないための保守的運用上限である。

## bindingと通常runの順序

proofのexact schema（protocol 1）は次の固定keyと型を持つ。hashはすべて64桁小文字hex、日時はUTC ISO8601文字列、enumはここで列挙した値のみ。

| key | 型・制約 |
|---|---|
| protocol / created_utc / expires_utc | intの1（bool不可） / UTC日時 / createdから24時間以下かつ現在より未来 |
| generator_source_sha256 | 全依存freeze canonical JSONのhash |
| binding | exact object: os_sha256,user_home_sha256,workspace_wsl_sha256,workspace_native_sha256,executable_path_sha256,executable_sha256,permission_root_wsl_sha256,permission_root_native_sha256,logical_settings_sha256（各hash）、cli_version（stringの1.4.8）、project_selector（stringのdefault-cli-project）、argv_profile（stringのexplicit-project-json-duration-v1） |
| files | exact object: global/project/shared各exact object。exists(bool)、sha256(hash又はexists=false時null)、acl_sha256(hash又はnull)、owner_sha256(hash又はnull)。globalはexists=true必須 |
| observations | exact object: global_template_match,explicit_selector_verified,project_scope_empty,shared_scope_empty,relative_cwd_witness,update_disabled_for_child（各bool true）、admin_gateway_candidate_absent(bool true) |
| account_scope | exact object: declaration（personal又はmanaged-supported）、owner_record_sha256(hash)。owner証言の適用範囲を記録し機械検証と呼ばない。未回答/managed根拠未確定では発行しない |

上記以外のmemberや観測bool falseは発行/受理しない。private metadataでもraw設定、原rule、認証、モデル本文は格納しない。

| 対象 | 固定する証拠と再照合 |
|---|---|
| 生成者 | 校正source全依存SHAとprotocol version |
| 実行環境 | WSL/Windows OS識別、実UID/SID、Windows user/home、canonical exe path/hash、exact CLI1.4.8 |
| workspace | WSL canonical pathと対応native cwd。親PS SetLocationで代用せず、本番WSL Python→native subprocess(cwd=W)の相対anchor witness |
| 起動 | 明示--project default-cli-project、JSON出力、duration秒suffix、子限定auto-update無効化。versionとmodelのargv profileも別に固定 |
| source | 固定global/project/shared pathと不存在区別、ACL/owner/bytes安定。project root.idの私的exact比較、明示selectorでの3scope構造とglobal候補/他scope空の整合 |
| 許可 | globalは厳格decoderと限定templateに一致。project/sharedは校正済み空snapshot全file hashへ一致。非空/変更/未認識snapshotは未対応理由で停止 |
| admin | 固定ProgramData gateway candidateの不存在と、個人/組織account適用範囲を別々に記録。不存在をremote管理不存在へ流用しない。未確定時は証拠を発行しない |

workspaceはcwd・排他・実行記録・差分の単位、permission_rootは許可templateとcohort許可境界の単位である。Request.permission_root省略時はworkspace。root/子はcanonical存在directoryかつ全祖先非symlinkを要し、workspaceはroot自身又は子孫に限る。root指定だけで起動権限を広げず、内部発行proofがworkspace/rootのWSL/native各hashを別々に束縛する。追加corpus denyはroot内の既知literalだけを受け、allow/ask/commandの和集合や未知構文は拒否する。非重複2子のnative集合はroot read/writeの2allow、ask空、root/2子corpusと固定全commandの4denyである。

論理Request.settingsはbounded nofollowで読んだ同じraw bytesから検査/hashを行い、logical_settings_sha256へ独立に束縛する。native globalのhashやJSON再serializeで代用しない。校正開始・発行・通常runtime・起動直前の値が一致しなければ停止し、空白だけの変更も別snapshotとして扱う。新closed schemaの不足fieldにfallbackしない。

通常runは入力/template検査→安全なproof読取→WSL内で検査可能なbinding→read-only Windows OS helperでOS/SID/home/ACL/native cwd対応と設定fingerprintを照合→版照会→直前fingerprint再確認→prompt起動の順。proof欠落/改変/期限/WSLで判定できる不正は全子0。Windows事実を照合する段階ではread-only OS helper子を使えるが、差異時はagyのversion/model子0を保証する。helperとagyの起動数を混同しない。

OS helperは固定schemaのnonce-bound request/response、固定候補だけの二読、作用0、本文非公開、全失敗の固定phase/型射影を契約とし、auth file/過去logを読まない。read-only helper子のfailure/timeout/不明応答もagy0。版照会は校正済みcohortの最後のcheckであり、proof欠落の探索には使わない。

2026-10-29の本人チャット「個人アカウントです。」をpersonalのoperator attestationとして受領した（2026-10-28 23:11 UTC前後）。これはaccountの機械検証ではなく、認証fileは読まない。校正proofはこの申告記録のhashを束縛する。将来の設定変更や別workspace/selector/版は再校正対象で、一般合成対応済みとは宣言しない。

既定運用は承認済みtemporary保全sessionとする。Windows親が原4fileをmemory保持→safe policyを一時適用して保持→account適用範囲確定後にactive snapshotを直前再照合してproof発行→通常wrapperで5UC→finally元復元の順。一時設定を元へ戻した時点でglobal snapshot hashが変わるため、その証拠で通常runを受理しない。この自然失効は想定したsafe契約であり、常用safe configへの恒久変更や本人限定新backupをIssue完了の追加条件にしない。恒久config変更/元rawの新永続backupは0を維持し、cohort artifactにも原rawを格納しない。

準備用zero-turn表示でCLIがglobalを正規化するため、正式2表示の前にnormalized snapshotを固定する。2026-10-29実測の非permissions差分はuseG1Creditsの厳密boolean false→欠落だけ（unknown変更0）であった。[公式schema](https://antigravity.google/schemas/v1/settings.json)のdefault=falseと[CLI保存契約](https://www.antigravity.google/docs/settings?tab=cli)のdefault key省略に限り同値と認める。他key/defaultの省略、true/文字列false、値の追加は推測受容しない。準備・正式/configとも実効G1falseを要求し、検証済normalizedそのものをbaselineへ採る。

## 検証と制約

- proofの改変/欠落/期限/型/owner/mode/alias、およびWSL内で独立に照合可能なworkspace/native入力projection/exe path/hash/source差異は全subprocess0。OS/userの複合hashはWindows component取得後に比較するため、read-only helper子が発生し得る。Windows OS/SID/ACL/fingerprint差異と共にhelperを区別して計数し、agy version/model0と無変更・非漏洩を確認する。project/shared未知snapshotもagy0。
- 5UCは支持cohortの本番wrapperで実行する。先行校正の成功だけで5UCを成功扱いしない。
- 許可先writeは実生成・payload一致を確認済み。保護先は不変だがengine write試行/拒否は直接未観測。この限界を記録し、AC外のdebuglog追跡を新しいblockerにしない。
