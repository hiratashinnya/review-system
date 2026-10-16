# Issue #540 実装判断

Codex (AI)、2026-10-16。

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
