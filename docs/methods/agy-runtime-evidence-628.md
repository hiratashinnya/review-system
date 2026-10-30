# agy 実効設定・WSL 起動の観測記録（Issue #628）

Codex (AI) による実測・実装記録。agy1.4.8の限定cohortで通常wrapperの5UCを確認した。最終レビュー・#607引渡し・owner手動mergeは個別に確認する。
下段は PR #627 head `f09f3d099952e9da8293ae88da3749b2c276973e`。
個人パスは `<windows-user>`、`<linux-user>` に置換して記録する。
以下の「使用版と実行環境」から「現環境で解除できない理由と必要条件」までは
2026-10-22 の観測履歴である。各旧章の「現在」は記載日当時を指し、後続の実装・実測は日付とsourceを分けて記録し、末尾の5UC・設定層対応表を現在の支持範囲とする。

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

## 1.4.8の部分実装と検証（2026-10-28）

この章は当日時点の履歴であり、後続の校正・5UC・回帰試験結果は次章以降に記録する。

新しいsnapshotに基づく実機観測で版1.4.8を確認した。親process限定の
`AGY_CLI_DISABLE_AUTO_UPDATE=true` を用い、前後の実行file指紋一致・元4file復元・自然終了を確認した。
これは当該cohortの根拠であり、旧1.3.3/1.3.5/1.4.6観測や過去の終了unknownを遡及更新しない。
現行出力・版契約は1.4.8に限定して接続したが、本番起動gateは未確認理由で停止を維持する。

### 確認した契約と観測限界

- 通常JSONの必須6keyはconversation_id/status/response/duration_seconds/num_turns/usage。
  usageは5項目の整数、num_turnsも整数として確認した。fixtureのsyntheticなid/responseを実応答とは扱わない。
- `--print-timeout` は30s/120sのduration構文を受理した。構文受理をtimeoutの実効顛末・子終了の証明にはしない。
- 既存選択モデルとuseG1Credits=falseの下で、promptへ渡していない秘密anchorの応答一致というread witnessを取得した。
  モデルprobeはtoken0のlocal表示とは別に扱う。
- 許可先write成功と保護対象（偽corpus）不変は確認したが、engine拒否は直接未観測である。
  応答文やfile不変から直接拒否が起きたとは認定せず、直接拒否ログの追加取得を完了条件にはしない。
  実corpus・認証を拒否試験には使っていない。

### 接続した部分実装

| 対象 | 接続した責務 | 残る境界 |
| --- | --- | --- |
| settings_sources | canonical Windows配置の固定3候補とadmin未知を返す。観測済みhome leaf shimだけを限定解決 | 候補発見を層参加・schema・admin不存在の証明にしない |
| settings_reads / settings_decoders | bounded regular/no-follow読取とstrict JSON、global optionalキーの由来・型/rule監査 | Request.settingsを実globalとみなさず、未知schema/alias/layoutへfallbackしない |
| settings_layers | 既知extra rule・重複・型の診断を未知adminと両立させる | 不完全inventoryではmissing-rule全体判定を保留し、実効mergeを推定しない |
| process / version / output_contract | exact1.4.8、duration秒suffix、通常JSON型契約 | 同版の未実測拒否/ERROR/timeout顛末や5UCへ成功を転用しない |

本番sourceと異常TCを追加し、循環home shimの固定理由化を是正した。
最初の4f69fe3局所PASS後、uv Python3.13の全量で固定理由の差を再検出し、F-628-29を再openした。
是正source `f9dba3761cf46882125166e2b2e662e45f6a0f15` のuv Python3.13.14再検証とR80の別context再レビューで解消した。
F-628-01はopenで、guardのskip・削除・期待値反転はしていない。

### 検証をsourceごとに分けた結果

| 対象source・範囲 | 結果 | 証跡・限界 |
| --- | --- | --- |
| 9978820・関連TC | 145件中144成功、既merge guard1失敗。lint違反0/debt77、asset MISSING0/stale18 | `TR-agy-runtime-628-9978820.md`。後続sourceの測定値ではない |
| 4f69fe3・F29局所 | 9TC成功、lint違反0/debt77 | `TR-agy-runtime-628-4f69fe3.md`。別Python環境の当時の結果として保持 |
| 4f69fe3・uv Python3.13全量coverage | 2430件・684.659秒・FAIL2（既guard＋循環shim固定理由差） | `TR-agy-runtime-628-4f69fe3-full-coverage.md`。TOTAL6074 statements/647 miss/89%、agy_delegate780/34 miss/95.6% |
| f9dba37・uv Python3.13.14関連coverage | 146件中145成功、既guard1失敗。循環alias TC成功 | `TR-agy-runtime-628-f9dba37-python313.md`。agy_delegate780/33 miss/95.77%（表示96%）。全量の再測定ではない |

f9dba37でもlintはexit0・violations0・accepted_debt77・baseline変更0、assetはexit0・49assets・MISSING0・stale18を再測定した。
証跡は `TR-agy-runtime-628-f9dba37-lint.txt` と同 `-asset.txt` であり、旧sourceの値の転用ではない。
TR/logは `tests/reports/`・`tests/logs/` にsource別で保存する。4f69fe3全量ではdocidx未importのwarningがあり、
TOTALを全repository包含とは主張しない。HTML/report生成は成功したが、unittestのexit1/FAIL2を上書きしない。
f9dba37は別coverage dataを用い、旧全量log・data・HTMLを上書きしていない。生成物はcommit対象外である。
この文書・coverage専用TRの作成者は既記録を照合しただけで、テストや実機操作を追加実行していない。

## 同snapshot校正と通常影響分析の実機成功（source edda082）

実行sourceは `edda08220ef5060e38685f39af8fcfdbb37a5640`、CLIは1.4.8、WSLはUbuntu、実行側は既存Windows user/homeである。個人accountはownerの本人申告に基づく運用条件であり、機械認証の証明ではない。校正worker・通常wrapperは同じnative executable・明示default-cli-project・固定workspaceに束縛し、子だけの自動更新抑止を確認した。設定原文・認証file・応答原文は公開記録に含めない。

元4fileをWindows親memoryに保持してsafe policyを一時適用した。準備表示による非permissions差分はuseG1Creditsの厳密falseから欠落への既知省略1点だけ、未知変更は0だった。正式configはstrict false、global/project/shared表示とcandidateが一致した。正式なnormalized snapshotをbaselineとして相対path anchorを本番WSL subprocessで読み、値をpromptへ渡さず応答一致を確認した。

校正proofのpublicationはcommitted／complete、durability confirmed true、warning falseだった。続く通常 `runner.run` の影響分析は `success_candidate`／`SUCCESS`／exit0、reason0で、非prompt nonceとaffected_callerの応答一致を確認した。モデル起動は校正1件と通常影響分析1件の計2件であり、校正を別UCへ数えない。保護sentinelは不変だったが、engineのwrite試行と直接拒否は未観測である。

finallyで原4fileのbytes・ACL・ownerを全件再照合して復元した。workerは自然終了exit0、stderr空、source/executable不変、private output cleanupを確認した。原設定rawの新規永続化、恒久設定変更、追加購入は行っていない。復元後のproofはsnapshot不一致で拒否され、safe一時設定の証拠が元設定へ流用されないことも確認した。この成功は過去B2aのrawbytes不一致・旧reader終了unknownを遡及解消しない。

安全結果SHA256は `a43472309572befe632b6e3d9ce2221576a5f51e71ec11de2cca2c223ecac9fe`、実行freezeは `4fa914431ad1371e5a7cb2392aeb873ea4fdd176cb02c7f8b4e609beec8cee2e`（67 entry）。別contextのR111で結果・provenance・source/freezeを照合し、新規指摘0だった。R111時点では残4UCと最終ACが未完了だった。後続の4UC/並列実測と最終回帰は次章以降へ分ける。

## source別の追加検証

`2b94fbe`の全agy関連229件は52.129秒で成功した。専用coverageは1439 statements／69 miss／95%、lint違反0・既存負債77、asset parity exit0だった。`5eddf97`はTD訂正、`edda082`は27件のログ/TR追加だけで、当該測定からpackage・TCは不変である。218件中5失敗、229件中2ERROR、旧全量FAIL2は履歴として保持し、今回の関連試験成功を全repository試験成功へ拡張しない。source別TRとlogは `tests/reports/` と `tests/logs/` を参照する。

## 通常wrapperの4UC実測（source 1e6594b）

source `1e6594bbadb8455d241491fd01a5b7310daf650e`で通常wrapperの影響分析・素案・外部調査・画像生成を実行した。packageは実装source `fb11ab2658ac11d1c41adeeb109712528ff4a8a7`と同じである。CLI1.4.8、Ubuntuから既存Windows user/homeのnative exe、明示default-cli-project、個人accountのowner申告、既存選択モデルClaude Sonnet 4.6 (Thinking)、agentMode accept-edits、実効useG1Credits=falseの条件に限定する。

同snapshotの校正proofはcommitted／complete、durability true、warning falseで、WSL actual subprocessの相対anchor witnessを確認した。通常4UCはsuccessと各witnessがtrue、reason0、受理版一致だった。外部調査の応答witnessは確認したが、直接のweb tool呼出は観測しておらず、tool実行の機械証明とは扱わない。

| 通常UC | input tokens | output tokens | thinking tokens | cache read tokens | total tokens | 成果確認 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 影響分析 | 4935 | 276 | 0 | 11315 | 5211 | 非prompt nonceとaffected_caller一致 |
| 素案 | 4921 | 617 | 0 | 11319 | 5538 | 読取markerと3見出し一致 |
| 外部調査 | 9285 | 533 | 0 | 19452 | 9818 | 公式URLとassertLogsのformatter引数・3.15追加の応答一致、直接web tool未観測 |
| 画像生成 | 9430 | 951 | 0 | 37027 | 10381 | wrapper回収artifact1件、raster認識 |

usageはnative JSONの5整数をそのまま保存した値であり、cacheとの算術関係や金額へ換算しない。画像artifactは270217 bytes、SHA256 `49dd7f541188de858c85f7f2242b8985515dd6d6fa6d5ece94c642e9fe3d5a12`。校正を含むnative prompt起動は5件だった。内部subagentを含むモデル起動総数は未確認であり、5件とは断定しない。

元4fileは親memoryに保持し、finallyでbytes・ACL・ownerの全件完全復元、Windows worker自然終了exit0・stderr空、source/executable不変、private output cleanupを確認した。原設定rawの新規永続化・恒久設定変更・追加購入は行っていない。復元後のproofはsnapshot不一致で拒否された。保護sentinel不変を直接のengine拒否証明へ拡張しない。

安全結果SHA256は `8ccbdb6f933a8b082727b6f3a4e947c162140238ef47f4d4a66de3592e5975b8`、provenance SHA256は `61a5712843c844947872fa1ef7cae3b4e38e4b9fc36ae04c75f2154636775bc3`、実行freeze SHA256は `2c8b28c813227f1ded80c37a877e90c1fdd9b173994bf5e956fb5fb8735a72d5`（73 entry）。4UCはR116の独立レビューで新規指摘0を確認した。後続の並列UCと全体回帰は次章へ分ける。

## 実同時並列と最終回帰（source 01cc080）

実行sourceは `01cc08066dda3f1e62d932e9134d34436ad7125f`。製品package/TCは `fb11ab2`と同一で、`1e6594b`以降は全量試験記録だけを追加した。承認済みpermission_root Wを拡張せず、非重複の子workspace A/Bを各々校正し、通常 `run_parallel` で2件を実行した。native policyはallow2・ask空・deny4（W/A/B corpusと全command）に限定した。

2proofがcommitted、各校正anchorと通常payload witnessが一致、両通常結果が成功した。外部observerがexeとargv markerを照合した異なるnative process2件の生存期間重複を観測した。clock frequencyは10000000で、観測区間の共通部分は約9.858秒だった。同workspaceの順次batchを並列成功と数えていない。

| 通常並列job | input tokens | output tokens | thinking tokens | cache read tokens | total tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 4921 | 151 | 0 | 11363 | 5072 |
| B | 4933 | 153 | 0 | 11365 | 5086 |

校正Aのusageは4850/198/0/11363/5048、校正Bは4859/206/0/11363/5065（input/output/thinking/cache_read/total）。通常jobと校正を別に記録し、内部モデル起動総数はunknownを維持する。W全体のbefore/afterでは変更4件、子外変更0、全corpus不変だった。これは今回観測範囲の事実であり、root内の完全隔離や途中で戻された変更の検出保証ではない。

finallyで原4fileのbytes/ACL/owner完全復元、自然終了exit0・stderr空、source/exe不変、private output cleanup、復元後2proof失効を確認した。原rawの新規永続化・恒久設定変更・追加購入は0。safe結果SHA256は `eecc621e3bc82b51c5379230bef221a731fde152fa200a60639b1b6955730819`、observerは `b00facaa7477d1a95da704ec37bd418666e948db4ae4f401b573a20072147f55`。追跡OBSは元immutable結果とbyte一致を確認した。実測のsource/usage/制約は [5UC成績書](../../tests/reports/TR-agy-runtime-628-live-five-uc.md)、各OBSと公開用provenanceは同directoryに保存した。

全量回帰はsource `1e6594b`で2529件PASS（782.105秒・exit0）。7packages指定coverageは6857 statements／691 miss／90%で、docidx未import warningを保持する。専用agy関連は245件PASS（52.938秒）、1563 statements／78 miss／95%。lint違反0・既存負債77・baseline変更0、asset parity exit0・MISSING0。対象とsourceを分け、全量coverage値を全module実行済みとは宣言しない。旧全量FAIL2・関連失敗/ERRORは過去記録として維持する。

実機記録は[4UC安全結果](../../tests/reports/OBS-agy-runtime-628-1e6594b-four-uc.json)、[並列安全結果](../../tests/reports/OBS-agy-runtime-628-01cc080-parallel.json)、[外部observer](../../tests/reports/OBS-agy-runtime-628-01cc080-parallel-observer.json)、[公開provenance](../../tests/reports/OBS-agy-runtime-628-live-provenance.json)で追跡できる。全量は[1e6594b成績書](../../tests/reports/TR-agy-runtime-628-1e6594b-full-coverage.md)、関連245件は[fb11ab2成績書](../../tests/reports/TR-agy-runtime-628-fb11ab2-parallel.md)を参照する。

R119の別contextレビューで並列実測は新規指摘0を確認した。本waveで通常5UC（影響分析・素案・外部調査・画像生成・実同時並列）の条件付き実機証拠が揃った。最終文書と独立レビュー、#607への実引渡し、default branch到達は別に確認する。PR #627/#680のmergeはownerの手動操作であり、AIはmerge/auto-merge/ready化/下段変更を行わない。

## 支持cohortでの設定層・合成・起動の対応表

| 対象 | 根拠と支持条件 | 実装・停止条件 |
| --- | --- | --- |
| global | `%USERPROFILE%/.gemini/antigravity-cli/settings.json`。公式settings schemaのoptional permissions/allow/ask/denyと、実機/config・/permissionsの一致を確認 | native file-only allowとcorpus/global command denyへexact限定。未知rule・広いallow・ask・必要deny欠落を拒否 |
| project | `%USERPROFILE%/.gemini/config/projects/default-cli-project.json`。明示selectorとroot identityを束縛し、同snapshotのproject scope空を観測 | 一般schemaを推定せず全file bytes/ACL/ownerを束縛。変化・非空scope・不正JSON・読取失敗は拒否 |
| shared user | `%USERPROFILE%/.gemini/config/config.json`。同snapshotのshared scope空を観測 | projectと同じ全file不変条件。未知snapshotを空へdecodeしない |
| admin | 固定`%ProgramData%/Antigravity/admin_settings.json` gateway candidateと大文字小文字を問わないgateway環境名を検査。個人accountはowner申告 | candidate/環境の不存在をremote policy全体の機械証明にしない。未支持の管理条件・未申告・変化時は発行/通常起動を拒否 |
| 優先・配列合成 | 公式changelogはglobal/project配置とproject優先を示し、公式permissions契約はdeny優先を示す。実測cohortではproject/sharedは空、globalだけが非空 | 複数非空layerの一般合成を実装済みとは扱わない。3scopeと実効表示の一致・全file不変の支持profileに限定し、競合は拒否 |
| WSL/native cwd | fixed Ubuntu WSL canonical workspaceから本番Python native subprocessの相対secret anchorを読み、promptへ値を渡さず応答一致 | PS Get-Locationをcwd証明へ流用しない。exe/hash/OS/user/home/workspace/native射影/selector/sourceが異なれば停止 |

一次根拠は[公式settings schema](https://antigravity.google/schemas/v1/settings.json)、[公式settings](https://www.antigravity.google/docs/settings?tab=cli)、[公式projects](https://www.antigravity.google/docs/projects?tab=cli)、[公式changelog](https://www.antigravity.google/docs/changelog)、[gateway管理設定](https://docs.cloud.google.com/gemini/enterprise/docs/ai-developer-tools/deploy-enterprise-gateway)と、source別の校正/通常wrapper安全結果である。gateway候補の契約を一般admin tool-permission schemaへ流用しない。

変更したfail-closeは、既知cohortを無条件停止から校正証拠と現在状態の一致時だけ起動へ限定解除する点である。未知schema・source/binding差・期限・未読・競合・保護deny不足・caller stopped・拒否/異常応答の停止は維持する。設定検査はsandboxではなく、内部tool操作の完全仲介・root内越境の完全隔離・途中変更の完全観測を保証しない。D0・corpus author分離・未検証成果不採用は呼出側の規範と機械的検出範囲を区別する。engine直接拒否は未観測、account変更時の再校正はowner運用である。PR627の#679残存は本Issueで解消したとは扱わない。

## #607への引渡しと最終ACの境界

通常5UCの条件付き実機証拠と全量回帰は揃った。#607への実引渡しとdefault branch到達は別の受入条件であり、草案作成だけで引渡し済みとは認定しない。最終独立レビュー後、具体的本文をownerへチャット提示し承認後に#607へ投稿する。実装・全検証・追跡文書・上段出版・#607実引渡しが揃った時点でF-628-01の実害解消を独立レビューが判定する。default branch到達はowner手動mergeによる別のIssue ACであり、未mergeだけを実装findingとして残さない。PR #627/#680のmergeはowner手動操作である。

#607のMCP解除・実体削除・Codex設定変更は別deploy単位であり、本Issueでは実行していない。撤去前の#606/PR #627 merge、wrapper動作、削除対象のowner確認、必要なpatch保全、撤去後確認と記録を#607で行う。旧B2aの不明を新成功で補完せず、過去失敗と観測限界を維持する。
