# agy 実効設定・WSL 起動の観測記録（Issue #628）

Codex (AI) による 2026-10-22〜26 の部分的な実測記録。受入完了・通常 run の解除を意味しない。
下段は PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e`。
個人パスは `<windows-user>`、`<linux-user>` に置換して記録する。
以下の「使用版と実行環境」から「現環境で解除できない理由と必要条件」までは
2026-10-22 の観測履歴である。その後の限定変更・設定元調査の履歴を保持し、最新の未確認状態は「段階B2a」に記録する。

## 使用版と実行環境

- Linux `6.18.33.2-microsoft-standard-WSL2`、WSL distro は Ubuntu。
- Linux 側起動入口 `~/.local/bin/agy` は Windows 側 `%LOCALAPPDATA%/agy/bin/agy.exe` へのリンク。
- `agy --version`: `1.3.5`。既存 wrapper の出力契約は 1.3.3 に束縛されている。版検査を緩めていない。
- sandbox 内の Windows 実行は `UtilBindVsockAnyPort: socket failed 1`。sandbox 外の読み取り実行では版表示成功。
- 実行 workspace: `\\wsl.localhost\Ubuntu\home\<linux-user>\ws_claude\review-system\tmp\worktrees\issue-628`。

## duration 観測と受理版の未確認契約

`agy --output-format json --print-timeout 15 -p /usage` は exit 2、
`time: missing unit in duration "15"` を返した。
同じ local command の `--print-timeout 15s` は exit 0、`status: SUCCESS`、
空の conversation ID、`num_turns: 0`、token 使用量 0 を返した。
この観測は 1.3.5 に限定され、wrapper の受理版 1.3.3 の互換性証拠にはならない。
第一弾ではこの結果を転用して `s` を付けたが、R1 で無根拠な変更を取り下げた。
内部 process の数値文字列は従来の合成試験用の挙動であり、1.3.3 での受理を保証しない。
本番 runtime は `print_timeout_format_unverified` で未起動を維持する。
解除には受理版の正確な実引数と実行結果、またはその版に束縛された公式根拠が必要である。
外側 `subprocess.run(timeout=...)` は数値秒のままとする。

## 読み取りで確認した層

| 層 | Windows 実行側で確認した場所 | 観測した形式・内容 | 未証明 |
| --- | --- | --- | --- |
| global | `%USERPROFILE%/.gemini/antigravity-cli/settings.json` | `permissions.allow` 13件、ask/deny キーなし | 他層との配列合成・拒否優先 |
| cache内の対応表（履歴） | `%USERPROFILE%/.gemini/antigravity-cli/cache/projects.json` | 当時のworkspace の Windows path → UUID | 対応表の観測。active projectの証明にはならない |
| 対応先のproject候補（履歴） | `%USERPROFILE%/.gemini/config/projects/<UUID>.json` | `id`, `name`, `projectResources.resources[].folderUri` | engine適用・permissionsの格納箇所・schema |
| shared user | `%USERPROFILE%/.gemini/config/config.json` | この環境では `userSettings.remoteControlHostname` のみ | permissions の schema・適用優先順 |
| admin | Linux `/etc/antigravity/admin_settings.json` は不存在 | Linux 側の不存在だけを確認 | Windows 側の実パス・全適用源・優先順 |

`agy --output-format json --print-timeout 15s -p /permissions` は
`command.data.permissions` に `project`、`shared`、`global` の3 scope を返した。
project/shared は scope のみ、global は allow 13件。admin の不存在証明にはならない。
`/config` の `command.data.config.permissions.allow` も13件だった。
非空の複数層・重複・allow/deny 競合を観測していないため、配列合成を推定しない。

## 現環境で解除できない理由と必要条件

global には `command(git status)` と `command(codex --help)`、別 workspace の
`git pull` / `fetch` を含む事前許可がある。既存の限定テンプレート以外の許可であり、
対象 workspace の read/write 許可・corpus deny がない。
設定を変更せず通常 run を許可すると、既存の安全契約を満たさない。
必要な設定差分は、全参加層から追加の command allow を除き、対象 workspace の
`read_file`・`write_file` と限定した単一 command のみを許可し、
`write_file(<workspace>/doc-system-v2/nodes)` を deny に加えること。
実際の Windows パス表現・規則の効力を先に測定する必要がある。
この日の観測では既存 user 設定を変更していない。その後の限定変更は、後述の owner 承認範囲で実施した。

`/config` の `useG1Credits` は false、`/usage` は Gemini と Claude/GPT の週次枠100%を返した。
これだけで画像生成の無課金を保証しないため、実機 UC 5種は未実施。
この段階ではモデル推論を依頼していない。

## 既存ユーザーでの段階A・A2（2026-10-23）

受領した追加パスは WSL 作業ディレクトリであり、専用 Windows user/home ではなかった。
owner は既存 Windows ユーザー向けの設定変更案を選択し、段階Aと、その後のA2具体案を個別に承認した。
認証ファイルは読み取り・コピーしていない。通常 run・モデル依頼・他設定層への書込み・
実機 UC・段階Bは、この承認範囲に含めていない。

段階Aは global permissions の退避、一時的な allow/ask/deny の空配列化、
完全一致 local command `/config`・`/permissions` の観測、復元を対象とした。
段階Aの `/config` 起動区間では permissions が空objectとして表示され、実ファイルから同キーが欠落した。
原因は断定できない。全ファイルの指紋変化を検出して停止し、owner が承認した限定復旧で
元 permissions・復旧直前のその他値・元ACLを確認した。
この過去runでは元全ファイルbytesは不一致で、元のその他値を独立比較する記録もなく、
その同一性は未証明のままである。

A2は、元のその他値の方式付き指紋を元全ファイル指紋に結び付けて保存し、
permissions が承認済みの空形式だけに変わった場合に、本人・ACL・終了・競合条件を確認して
メモリにある元bytesへ戻す案である。未知形式・値の変化・指紋不明・終了不明・競合では停止する。
表示の空objectや省略は表示の観測に限り、deny-all・権限効力・全層合成の証明には使わない。

| 実行・是正 | 確認できた事実 | 限界・結果 |
| --- | --- | --- |
| A2初回 | 最初の baseline `/config` が外側40秒で timeout。prepare・設定置換には未到達 | 元指紋の保存前であり、開始時との設定同一性は不明。後の独立読取で現設定・ACL安定、残留0を確認 |
| F-628-16 是正 | 版照会を含む最初のCLI起動前に、元permissions・比較metadataの同期保存確認を必須化 | 保存未確認ならCLIを起動しない。過去runの不明を遡及解消しない |
| R25 | permissions backup の確認で停止。CLI起動0・設定置換0 | 失敗箇所は当時の分類だけでは未確定。独立読取では本人限定ACLだがfile ownerが現SIDと不一致 |
| F-628-17・18 是正 | 固定phase/codeの診断と、新しい空backup fileのowner設定・本人限定ACL確認を内容write前へ追加 | 別contextのR27再レビューで両指摘解消、新規0。元の失敗throw地点を断定しない |
| R28 | backupの同期保存確認は成功。版照会の自然終了後、版検証で停止。baseline観測0・設定置換0 | A2未完了。後続の限定probeで実版1.4.6と期待1.4.5の相違を確認 |
| R28独立OS読取 | 今回元全ファイル・permissions・ACL一致、その他値same、本人binding一致。bytes/ACL二読安定、worker・agy/GUI・候補残留0 | 今回元状態の現在一致を確認。過去runの不明、A2未完了、実効合成・5UC未達は維持 |
| R29 | 同じA2承認scopeのscratch期待版を実測1.4.6へ限定追随 | 別contextの独立レビューで新規0。本番受理版1.3.3・停止条件・将来版の拒否は不変 |
| R30 | CLI前の同期保存、1.4.6一致、baseline2種、一時空permissions適用、変更後表示2種、元bytes復元がすべて完了 | 表示と復元の限定A2のみ成功。権限効力・配列合成・5UCは未証明 |
| R30独立OS読取 | 今回元全ファイル・permissions・ACL一致、その他値same、本人binding一致。bytes/ACL二読安定、全worker自然完了、worker・agy/GUI・候補残留0 | 今回元状態の現在一致を独立確認。過去runの不明は維持 |

R28では設定置換・復元writeは実施していない。最新R30では実行authorが元bytesへ復元し、
別contextのreaderが書込みをせずに元全ファイルとの一致を確認した。本人限定backupは保持している。
通常runの停止を維持し、実機writerがいる場合は追加作用を行わない。
R28後の限定probeでは `--version` を1回だけ実行し、strict semver `1.4.6`、exit0、
timeoutなし、stderr空、自然完了を確認した。scratchの期待版 `1.4.5` とは一致しない。
probe前後でR28元backupとのbinding・全ファイル指紋・ACL・その他値sameと残留0を確認した。
このprobeでbaseline表示や空設定適用は行っていない。
主文脈は、既存のA2承認scope内のscratch実装選択として、実測1.4.6への限定追随を判断した。
R29の独立レビュー後、R30で限定実機確認を完了した。本番受理版1.3.3・本番adapterは変更せず、将来版も自動受理しない。

R30の変更後 `/config` はpermissionsを空objectとして表示し、`/permissions` は
project/shared/global各scopeだけを表示した。変更前後の4表示はいずれもexit0・status成功・
stderr空・token全項目0・turn0で、2回の `/config` はuseG1Credits=falseだった。
表示から実ファイルの具体的な空形や拒否効力を推定しない。
今回の公開用最小集計は `tests/reports/OBS-agy-runtime-628-stage-a2.json` に保存する。
この集計には設定原文・規則値・個人path・SID・ACL原文・設定指紋・private backup名を含めない。

実装・是正と独立レビューは別contextで実施し、カルテで指摘と結果を追跡した。
R29時点でF-628-02〜18は解消、F-628-01はopenである。
今回のscratch是正に対するテスト追加・実行は行っていない。
maintainability lintは違反0だったが、gitignoredのscratchが対象だった証拠にはならない。
PR内の本番ソース・既存試験の測定結果とは区別する。

## 段階B1: 限定ruleの表示と復元（2026-10-24）

ownerはA2と別のB1具体案に「ok」と回答した。B1はglobal候補の限定表示と元bytes復元だけを対象とし、
通常run・モデル依頼・tool操作・他layer書込み・fixture/corpus作成・5UCは行っていない。
候補と実装・readerは別contextの独立レビューを通し、最終R33レビューの新規指摘は0、F-628-01はopenだった。

全CLI起動前に元permissionsと比較metadataの本人限定同期保存・読戻しを確認した。
最初に固定 `--disable-slash-commands=false --version` を1回だけ起動し、
自然完了・exit0・stderr空・1.4.6完全一致で構文受理を確認した。同じfalse flagを表示2種にも付けた。
[公式settingsのCLI override契約](https://www.antigravity.google/docs/settings?tab=cli#command-line-overrides)と
[対応flagの公式reference](https://www.antigravity.google/docs/cli/reference/)に基づき、session overrideを採用した。
これは一般契約を固定false flag経路にも適用する設計判断・推論であり、全層scalarの実効優先を実測した証明とは分ける。
元globalの当scalarは欠落または厳密なfalseだけを受理した。

| 確認対象 | 実行・独立読取で確認できたこと | 証明していないこと |
| --- | --- | --- |
| 一時候補 | globalにallow3・ask0・deny1を適用し、readbackを確認 | ruleのparse受理、UNC/regexの効力 |
| `/config`・`/permissions` | 各1回、allow3/deny1が順序込み完全一致。ask表示は省略。両方exit0・status成功・stderr空・token全項目0・turn0 | deny効力、deny優先、複数層の配列合成 |
| config scalar | useG1Credits=false、slash無効化はfalseまたは既定値として表示 | 全設定層のscalar優先順位 |
| author復元 | 実fileが候補完全一致・ask空/欠落のみで、元その他値・ACL・binding・終了・不在・bytes安定・late照合を満たして元memory bytesへ復元 | 未知・競合・終了不明時にも復元できる保証 |
| 独立OS読取 | 今回元全file・permissions・ACL一致、その他値same、本人binding・backup一致、bytes/ACL二読安定、全worker自然完了、worker・agy/GUI・候補残留0 | 過去runの元状態不明の遡及解消 |

実行は1回で、表示完了と復元完了はともにtrueだった。独立readerは書込みを行わず、
authorによる復元後の元状態一致を確認した。bindingは1snapshot、bytes/ACL/process/candidateは2snapshotで照合した。
元allow13を含む元bytesへ戻したため、狭い候補は残っていない。本人限定backupは保持する。
公開用最小集計は `tests/reports/OBS-agy-runtime-628-stage-b1.json` に保存する。
原rule値・設定指紋・SID・ACL原文・個人path・private backup名・実行file指紋は公開しない。

本番受理版1.3.3・adapter・停止条件は変更していない。将来版は自動受理しない。
表示の一致をparse成功・権限効力・全層合成・5UCへ拡張せず、F-628-01はopenを維持する。
今回のテスト追加・実行はなく、scratchのlint違反0を対象包含の証明として扱わない。

## 設定元のread-only inventory（2026-10-24）

B1の元状態記録を参照し、現binding・cwd・実行file指紋が一致する範囲で設定元を読取調査した。
今回agyを起動しておらず、1.4.6はB1の実測fileへの束縛である。新たな版照会の結果ではない。
両inventoryとも設定write・backup作成・CLI・モデル起動は0で、復元やGUI停止要求も行っていない。

### 旧cache selector調査とF-628-19

現workspaceを記号 `W` として扱い、cacheの完全一致keyだけからUUIDを選ぶ旧inventoryは、
required3phaseに対しattempted/completedが2/2で論理STOPした。開始した2phaseはnonce付き自然完了を確認したが、
全inventory完了はfalseであり、selected project fileは読んでいない。F-628-19は、試行分の自然完了と
全調査成功・未試行phaseを混同する状態報告を分け、R36の別context再レビューで解消した。

globalはB1元全file・permissions・ACL一致、その他値sameで、allow13のみ、ask/deny・disableSlashCommandsキーはなかった。
shared rootとuserSettingsはobjectで、両直下のpermissions・disableSlashCommandsキーはなかった。
B1参照file・global/sharedの存在・bytes・owner・ACLは二読安定、各phase前後の既知agy/GUIは0だった。
cacheは存在しroot objectだが、exact `W` keyは0件だった。cacheは1読で安定性unknown、UUID選択は行っていない。
この0件をproject層の不存在・未登録・別名候補へのfallback根拠にしない。

### 公式selectorの訂正とF-628-20

[公式ProjectsのDefault project execution](https://www.antigravity.google/docs/projects?tab=cli#default-project-execution)は、
project flags無しのsessionが `default-cli-project` を使い、会話resumeは既存会話のprojectを使うと説明する。
B1固定argvにはproject指定・新project作成・resumeがないため、この一般契約を選定根拠として採用した。
cwdは実行場所のbindingとして別に保持し、cacheのcwd対応をactive projectの証明に使う想定を訂正した。
F-628-20はR38の別context再レビューで解消した。公式契約は物理file名・格納schema・実engine適用の実測証拠ではない。

新inventoryはcacheを読まず、予約literal `default-cli-project.json` の1候補だけを仮説検証として読んだ。
3phaseすべてのnonce自然完了を確認し、限定inventoryは完了した。候補は存在し、root objectのidは予約identityとexact一致、
存在・bytes・owner・ACLは二読安定だった。id確認後のrootではpermissions/settings/userSettingsがすべて欠落し、
未知memberは2件だった。未知member名・値は公開せず、別UUID・別名・content探索はしていない。

候補filename契約とschema契約はunknown、engine適用は未証明である。
`candidate_engine_application_proven=false` は適用の証明が得られていない意味であり、非適用を実証した意味ではない。
キー欠落から別格納位置の不存在や適用層の不在も推定しない。Windows admin sourceもunknownを維持する。
新調査でもglobalはB1元全file・permissions・ACL一致、その他値same、binding一致とglobal/sharedの二読安定を確認した。

公開用最小集計は `tests/reports/OBS-agy-runtime-628-source-inventory.json` に保存する。
原settings・rule値・実W・UUID・SID・ACL原文・設定/file指紋・private pathは含めない。
F-628-19・20の解消は状態報告と選定根拠の是正であり、全層合成・効力・5UCの完了ではない。
F-628-01はopen、本番1.3.3契約と起動停止、A2/B1成功と過去runの元状態unknownは維持する。
今回のテスト追加・実行、本番code変更はない。

## 段階B2a: native UI追加後のSTOPと限定復旧の未完了（2026-10-25〜26）

**承認された限定4file読取でM0・root_absent・元canonical一致を確認したが、旧cleanup完了は未認定である。**
projectのrawbytesは元と不一致、旧reader終了と現在binaryの版はunknownである。
原keeperはR48前後でSTOP同一・原memory gate成功を確認しており、旧STOP・phase・proofを変更していない。
後続UIは許可されていない。これをA2/B1の過去の復元成功やsource SHA一致で補完しない。

B2aでは、ownerが承認したnative permissions UIのread marker1件を、以下では記号Mと呼ぶ。
Mの原文・実path・project UUID・未知member名・原設定指紋は公開しない。
operatorの「初期ruleなし・追加1件・退出」と、後の「削除1件・全tab空・退出」は人の申告として受領した。
UI token0や自然終了receiptの機械証明は得ていない。keeperからモデル/tool promptや設定JSONの直接書戻しは行っていない。

| 時点 | 確認できた事実 | 停止・未確認事項 |
| --- | --- | --- |
| 追加申告後 | 読取frameは自然完了。global/shared/cacheは元存在・全file・ACL・owner一致、project id/binding/存在/ACL/owner一致。M exact1を過去観測 | projectの全file/canonicalは不一致。allow leafの空化/削除だけで元canonicalへ一致せず、元guardのlogic_success=falseでSTOP |
| 別contextのSTOP診断 | 診断コピー上で、Mを含むroot直下objectの削除だけが元whole canonicalへ一致。leaf/内側objectの空化・削除とroot直下objectの空化は不一致 | 元before型/値はunknown。pure permission wrapperの証明、実設定への削除・正規化の認可にはしない。旧worker receipts未取得で不在unknown |
| owner限定復旧承認後の準備 | 同じMだけをnative UIで1回削除する別guardを準備。独立before frame/proofを確認しdelete_ready。固定R/I/allowのM1・余分sibling0・R外canonical一致を確認 | 準備時点では削除UI未起動。旧keeper STOP・原memory保持を維持し、cleanup成功とはしない |
| 削除申告の保存 | launch-used/one-use gate消費を確認し、operator-doneで削除1件・全tab空・退出の申告を保存 | 人の申告をUI自然終了・token0・M0の機械証明にはしない |
| 新guardのverify | 1回実行しexit2、固定reason `recovery_guard_unverified` でSTOP | 自分after比較・独立reader結果/frame/proof・completeは未作成。比較不一致・reader終了・保存例外のどこで失敗したかは未確定 |
| 別after observer | 1回実行しexit2、observer_completed=false、observer_state=unknown | own OS frameの自然完了を未確認。reader未起動と終了済みを区別できず、現在M数・after条件・終了状態はunknown/null |
| R48 local/keeper probe | localはexit0/local boundary到達、keeperはexit0/Windows reader境界未進入。正当nonce/peer/PID/birthticks、前後STOP同一・原memory gate、固定metadataの読取を確認 | capture_four・新Windows reader・CLI/version/UIは呼ばず、proof作成・phase進行なし。前observerの原因や旧reader終了、after設定成功を証明しない |
| R52再レビュー後のWindows inventory | 新worker1回がstartup receipt・nonce一致・natural completion・child exit0・stderr空で完了。B1 bindingはexe hashだけ不一致 | 設定は未読。変更時刻・現在版は未確認で、元guard/observerの失敗と同じ原因だった証明はない |
| 承認後の限定4file読取 | 新worker1回がstartup/completion identity・nonce・natural・child exit0・stderr空で完了。M0、R不存在、R外/whole canonical元一致を観測 | project rawfullhashは不一致。旧cleanup/proof・engine適用の証明にはしない。過去reader終了・現在版はunknown |

限定復旧でprivateに固定したroot keyをR、唯一の内側keyをIと呼ぶ。ownerが追加承認した削除後の形は、
R不存在、`R={}`、`R={I:{}}`、`R={I:{allow:[]}}` の4形だけである。
全てM0・全tab空・他rule0・R外canonical一致と、他3fileの元比較などを必要とする。
空wrapperが残る場合の元project rawbytes一致は保証しない。
後続の限定読取ではM0・root_absent等のデータ条件を確認したが、旧guardの完了・正式cleanup/proofとは分けて記録する。

R48はlocal/status/snapshot範囲で停止を再現しなかった限定事実である。
過去observerの失敗箇所をcapture_four内部と断定せず、source一致だけで現設定や旧reader不在を証明した扱いにしない。
keeperのSTOP応答や原memory保持をcleanup成功へ読み替えず、旧verify・observerの再実行、JSON直接復元、kill/forceは行っていない。
R49でF-628-23（major）を起票し、新inventory経路に固定stage・安全な失敗分類・private child identity/receiptの同期保存を追加した。
timeout時も生存親が同じchild/pipeを保持し、payload再送・再起動・killなしで待機する経路を静的に独立確認し、R52の別context再レビューで解消した。
これは将来の証拠保持の是正であり、過去observerがtimeoutした、Windowsを起動した、残留した、という証明にはしない。

新inventoryは自然完了したが、元B1とのexe hash差異を検出した。profile/SID/OS/exe path/固定workspace/target labelは一致した。
actual process/provider cwdはworkspaceと異なり、そのboolは固定workspaceの存在・binding比較と分けて記録した。
cwd差をbinary差異の根拠には使っていない。現在版と変更時刻は未確認で、版照会も行っていない。
2回の現在process snapshotはともに既知agy/GUI0、exact既知readback script0、exact既知runtime script0、CommandLine非取得shell0、その他shell3だった。
その他shell3を安全なprocessと認定せず、known count0を旧readerのPID同定・自然終了へ読み替えない。
この先行inventoryでは設定を読んでおらず、その時点のM数・4empty形・after条件はunknownだった。旧reader終了は引き続きunknownである。
新workerの成功と、過去の取得されなかった証跡、元generic STOPの原因を別の事実として保持する。

### 限定4file readonly 1passで確認した現在データ

ownerの追加承認とR56の独立レビュー後、設定変更を伴わない限定読取を1回実行した。
global/shared/cacheは元存在・fullhash・owner・ACLが全一致した。projectは存在・id・owner・ACL一致、rawfullhashは不一致だった。
固定Rは不存在、M exact0、R外canonical H・whole canonical Hは元referenceと一致し、4file各二読は安定した。
rawbytesとcanonical値の一致を分け、after_data_conditions_match=trueを旧guard/proofの完了へ昇格しない。

exe hashは元B1値と不一致のまま、今回pass前後のcurrent hashは安定した。他のprofile/SID/OS/exe path/固定workspace/target bindingは一致した。
original_binding_all_same=falseを保持し、元referenceをcurrent値へ更新していない。現在binaryの版は照会せずunknownである。
前後processは既知agy/GUI0・exact known script0・CommandLine非取得shell0・その他shell3で、その他3件のidentity setは前後同一だった。
用途はunknownのまま安全な除外と認定せず、過去reader終了や将来の静止も証明しない。actual process/provider cwdのworkspaceとの差はbinary差異と別fieldで保持した。

今回workerのstartup/completion identity・nonceと自然完了を確認した。agy/version/UI起動、設定/marker変更、旧verify再実行、
JSON復元、phase進行、kill/retryは行っていない。cleanup_confirmed/proof_savedはfalseで、engine適用も未証明である。
この報告編集では新しいWindows読取・agy/UI起動・設定書込み・テスト追加実行を行っていない。

公開用最小集計は `tests/reports/OBS-agy-runtime-628-stage-b2a-recovery.json` に保存する。
原値・実path・UUID・SID・ACL/設定/file指紋・private参照は含めない。
F-628-23はresolved、現在openはF-628-01。本番1.3.3契約と起動停止、schema/効力/合成/5UC未達、過去runの元状態unknownを維持する。

## 後続の実測と #607 への引継ぎ

公式 `agy --help` に config/home を切り替えるオプションはない。
`--project` は既存 user/global を隔離する証明にはならない。
専用 Windows user/home を使う案に対し、owner は既存ユーザーの設定変更案を選択した。
承認済みA2と、別途承認されたB1のglobal限定表示・復元は完了した。
read-only inventoryで観測した候補のidentity・shapeだけでは参加sourceやpermissions schemaは確定しない。
B2aのnative UI追加と限定復旧の旧guardはSTOPのままだが、別途承認された読取でM0・root_absent・canonical元一致を確認した。
project rawbytes不一致、旧cleanup/proof未認定、元binarybinding差異、旧reader終了unknownを別々に保持する。
現在データの一致から旧STOPを自動解除せず、keeperの原memoryと証拠を保持して次の判断を行う必要がある。
新しい診断・独立レビュー・実行許可が整うまで、追加UIや設定作用へ進まない。
複数層の変更・モデル利用を伴う実測もまだ認可・実施していない。
無課金枠と自動課金無効を確認し、具体的な次段階を承認した上で次を測定する。

1. project/shared/adminの参加元・permissions格納schema・CLI選定条件を確定する。cacheや候補file名から適用を推定しない。
2. 同じ rule の重複、異なる rule、allow/ask/deny 競合を各組合せで確認。
3. cwd sentinel を別 workspace に置き、Windows 起動の cwd と URI/path を照合。
4. 影響調査・素案・外部調査・画像生成・並列の5 UC を、版・設定・使用量とともに記録。

これは実験入力の書込みを伴い、read-only 観測だけでは合成規則を証明できない。
#607 への現時点の引継ぎは「撤去不可、実機証明未完」。
#513 の corpus 保護・D0・未検証成果不採用を緩めず、設定検査は sandbox ではないという
PR #627 の制約を維持する。merge guard は意図的に赤のままである。
