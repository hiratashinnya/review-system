# Issue #540 実装判断

Codex (AI)、2026-10-16。

## 是正判断（round 3、方式転換）

F-540-02はshell構文を増やしても実行対象を推定する境界が誤っていた。新規書込とfile-issue更新のCLIが
実際のabsolute rootをgit top-levelの`tmp/_adr-notify/<root SHA256>.root`へatomic replaceで登録する。
gitが無いときは明示`--repo`（省略時cwd）を共有scopeとする。hook側cwdも同じrepo scopeを用いる。
索引はrepo内の既存write権限だけを使い、各要素のsymlinkを拒否する。rootごとの固定keyなので並行登録で失わない。
CLI stdoutにも`ADR-WRITE-ROOT:` receiptを出すが、3toolのPostToolUseは登録済みrootだけを読み、TOMLからpending IDを再計算する。
未信頼のtool_responseは読み順のhintに限り、任意パス・任意systemMessageを採用しない。部分receiptが他の書込を
隠さないよう登録全rootを必ず検査する。stdoutの全切詰め・redirect・MCPの要約でも通知対象が消えない。
索引に残った別rootの破損や読取不能はrootごとにstderr診断して隔離し、今回書込rootの通知を巻き添えにしない。

操作紐付けはreceipt消費型でなくlevel-triggerとする。CLI登録後の同一操作PostToolUseでpendingを通知し、以後も
残っていれば再通知する。複数shell/並行hookのreceipt奪取や、CLIへsession/tool tokenを注入するPreToolUse追加を避ける。
この選択では別rootの既存pendingも再通知し得るが、未解決を継続可視化する目的に合う。systemMessageはhookが出す。
索引は履歴・既読状態ではなく再構築可能なroot集合であり、tmp cleanupで消去可能。消去後は次のCLI書込で再登録する。
CLIを介さない直接TOML編集は操作イベントにしない。正本TOMLを変更せず、登録の無い既存rootは次のCLI操作で登録する。
通知以外の利用者が無いshell_commandsのparserとその専用TCは削除する。実行結果を扱うE2Eへ統合し、死んだ実装を互換目的で残さない。

F-540-07は`.write.lock`のflock内でload・NFKC/casefold衝突検査・公開を連続実行する。new-entryとreplaceで共用し、
既存`.file-issue.lock`とは分ける。取得順はfile-issue→writeのみで、writeからfile-issueへ戻らないため入れ子deadlockを作らない。
固定lock inodeは削除しない。schemaは変更せず、同じ未merge PRの是正なのでharness-adr/v1.0は据え置く。

F-540-06の最新CIではfresh checkoutのtmp不存在とsynthetic trust fixtureの前提相違が判明した。
入口TCはrepo/tmpの存在を仮定せず親を明示準備し、git管理下のおとりcwdを使う。trust fakeのmixedは実repoのpre-tool gateを
優先し、そのkeyが存在しない単一SessionStart fixtureでは先頭hookを未信頼化する。検知内容を弱めずStopIterationを防ぐ。
この追加是正も同一PR内でありschemaを再bumpしない。

## 是正判断（round 1）

全索引ノードの参照実在はDocSpecから導出した同じ辺を検査する。資産のrepo内実在検査は書込前とread-only checkで共用する。
file-issueはroot内の固定lockファイルへのflockを保持したまま最新状態を読み、起票・番号書戻しを行う。
lockは削除せずinodeを固定して別processの待機者とも排他する。root単位の直列化は同一ADRだけのlockより単純でIDのパス化も不要。
shell通知はコマンド区切りごとにcdの作業ディレクトリを解決し、各実行ツール経路に共通適用する。
schema変更はなく、同一未merge PRの是正であるためharness-adr/v1.0を再bumpしない。

## 是正判断（round 2）

通知cwdは区切りごとの単一値ではなくshellのプロセス境界で管理する。リスト内のcdだけを後続へ引き継ぎ、
subshellとpipeline各枝・backgroundは親へcwdを返さない。nested subshellも同じ再帰規則で処理する。
Codexのhookは既存の.sh入口契約に合わせ、repo正本をsafe pathでimportする。trust fakeは末尾に依存せず
特定のpre-tool gateを未信頼化し、新PostToolUseの未信頼も別ケースで検出する。schema変更はなく同一PRのため版を据え置く。

## 初回判断

- module/interface: feedback_ledger の既存 DocSpec/Field/TableSpec・正規化・canonical serializer・slugify wrapperをimport再利用する。共有索引adapterはharness_traceへ分離し、adrの欄名を持たせない。新Python moduleを100行以内に分割するため、既存負債のfingerprint変更もbaseline更新も不要。
- protocol/persistence: 道具別rootのcanonical TOMLをCLIからatomicに保存する。schemaはharness-adr/v1.0。ADRから台帳への片方向参照は独立したowner_decision_refs（ref=ledger）。sourceへ混在させる案より参照対象を明確にできる。オーナー逐語は転載しない。
- orchestration/prompt: #371本体のロール・著作pipelineは導入しない。既存PostToolUseと同型の助言hook＋同一CLI操作の通知を併用する。
- log/version/test strategy: TD/TC/TR、実装commit後にテスト。staleの時刻とGitHub subprocessは注入可能にし、外部ネットワークなしで検証する。
- immutabilityとfile-issue書戻しの両立: 設計判断は不変だが、pending→filedと番号のみを許可する。全面上書きを許す案は判断履歴を壊す。起票後書込失敗時は番号を表示し、--issueで復旧する。
- ChangePlan/VerificationDesign: 現mainには#371の永続envelope/DocSpecが存在しない。形式本体を先取りせず、発生源が宣言するDocSpec＋documentの永続JSONを入力できる境界とし、任意欄名の両種別をテストする。実装済の発生源からはDocSpecを直接注入できる。
- #452証跡: 実装着手時main=9ffe086d。tests/designs/TD-issue-start-452*.md と tests/reports/TD-issue-start-452*.md は0件。99d89553（#538）で archive/issue-452-codex-supervisor/{designs,reports}/ へ履歴を保持して退役済み。ACが指定した実在元ファイルはなく、退役証跡を現行道具へ復活させない。issue_start/verify/には本IssueのTD/TC参照/TRを初弾として配置する。
