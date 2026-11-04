# 短期対策 S4–S6：具体設計

作成日 2026-11-03 / ChatGPT (AI)、未承認。関連: [調査レポート](README.md)・[S1–S3](DESIGN-S1-S3.md)・[Issue反映計画](ISSUE-HANDOFF-PLAN.md)。

## S4 重要なテストが誤実装を落とせることを反例で示す

### 既存工程との境界

.ai/agents/test-writer.md は、2aでUT-TD/UT-TC（未実装Red）を作成し、独立pr-reviewerが期待値独立性を点検すると規定済み。**Red-firstとmutationは別検証**：Red-firstは未実装の状態で失敗すること、mutationは実装が意図的に退行した場合に特定のassertが失敗することを検証する。

全体のmutation score算出や常時CI実行は要求しない。判定を間違えると安全・状態・成果物を壊す分岐へ代表変異を当てる。

### 入力と検証順序

対象：issue番号 / sourceパスと関数 / test ID / 原正常条件 / 改変条件 / 期待されるassertの失敗。検証手順は次の5段階。

1. 信頼済みsnapshotを隔離した一時作業面で対象unittestを実行しGreenを確認。
2. 改変前の対象sourceの内容ハッシュ `base_sha256` と、隔離作業面のコミット `head_oid` を記録。
3. 未commitの一時作業面で1か所だけ意味のある欠陥を注入し、`mutated_sha256` を採取する。**`mutated_sha256 != base_sha256`** が必須（同一なら変異未実施として失格）。例: verdictのcleanをharmful-openに変更、入力型チェック除去、拒否コード変更。
4. **対象testのassertion failure**を確認。SyntaxError、ImportError、収集失敗、timeout、コマンド不備は検出成功とみなさない。試験中にcommitしないため `head_oid` は変わらない。
5. sourceをバイト単位に元へ戻して `restored_sha256 == base_sha256` と再Greenを確認。**原本と変異中のSHAは異なり、原本と復元後のSHAだけが一致**する。変異をコミット・PRへ混ぜない。

証跡形式（既存test reportとPR本文への参照であり、新規台帳ではない）:

~~~text
mutation_id: MUT-01
target_source: karte/<module>.py::<symbol>
target_test: tests.unit.test_karte_cli.TestStatus.test_clean
fault: verdict clean -> harmful-open
head_oid: <full-commit-OID, unchanged in all three states>
base_sha256: <source content hash before mutation>
mutated_sha256: <different source content hash during mutation>
restored_sha256: <same source content hash as base>
baseline: test_passed
mutated: assertion_failed
restored: test_passed, restored_sha256 == base_sha256
evidence: <tracked-report-or-log-path>
~~~

### 変更先と実施対象

- #720が既に対象とする tests/unit/test_karte_cli.py::TestStatus.test_clean：部分文字列cleanを探すのではなく、verdict**欄全体**を比較する。変異で赤になることを証明。
- #720の karte_notify/trigger.py::extract_commands：非文字列のcommandを拒否する型ガードを外して赤になることを証明。
- #728の tests/unit/test_karte_cli.py：EXIT_OK以外なら何でもよい、という緩いassertを期待する**固有の終了コード**へ変更。別の拒否コードを注入して赤になることを証明。
- #728の karte_notify/hook.py：runner timeout、tool_input/issue型検査を除去して赤になることを証明。
- コードの修正そのものは#720/#728に属し、本施策で別のテストパッケージを再実装しない。
- 共通化するのは検証プロトコルのみ。.ai/agents/test-writer.md / pr-reviewer.mdへ必要なら小さく参照を付ける。2aのテスト設計に欠陥が発覚した場合、2b実装者が勝手にテスト変更せず上流STOPする。

### 反例テスト

- S4-T1 改変前Green、誤verdict注入後に対象assertがRed、復元後Green。
- S4-T2 期待終了コードが別値になった場合、assertNotEqualでは通る欠陥を新assertEqualが捕捉。
- S4-T3 型ガード除去で不正commandの期待値が崩れる。
- S4-T4 ソースを構文エラーにしただけのRedはmutation検出と認定しない。
- S4-T5 未実装Redをmutationで検出したと二重計上しない。
- S4-T6 `head_oid` は未commitの変異前・変異中・復元後で不変、`mutated_sha256 != base_sha256` かつ `restored_sha256 == base_sha256`。3つのhash値を採取し、対象assert Red・復元後Greenを確認する。

### AC-S4

- [ ] #720/#728の指定変異は個別テストのassert失敗として検出され、収集失敗ではない。
- [ ] 少なくともverdict、終了コード、入力ガードにそれぞれ1代表変異の検出証拠がある。
- [ ] Red-firstの証拠とmutationの証拠を区別している。
- [ ] 変異中のsource SHA-256は原本と異なり、復元後だけが原本と一致する。隔離作業面のHEAD OIDは不変、対象assert Red・復元後Greenで、変異がPRに残留しない。
- [ ] 全域の高コストmutation runner、追加のロールやレビュー工程を新設していない。

## S5 レビュー4点証拠を「同一PR head」に束縛

### 現行の満たしている範囲

.ai/agents/pr-reviewer.md には、RTKの --no-compact 差分全文取得、約100行単位の漏れない読了、差分を確認できなければblocker finding+STOP、ローカルテストとPR CIの区別、PR headが変わったら停止、Karte findingの全件記録が**すでにある**。#530（差分全文取得）はCLOSED。これらの再実装を新規Issueの成果にしない。

追加する成果は**証拠参照が現在のhead・review round・Karteに一致することの可視化**。review artifactの原本化は#375、AgentRunのclose gateは#409の責務であり、本施策が別台帳/validatorを作らない。

### 記録契約（既存PR reviewer返却4部の「判定」へ追記）

~~~text
target: owner/repo PR#<number> head=<exact-OID>
diff: complete|incomplete ; method=rtk gh pr diff --no-compact ; evidence=<path/ranges>
ci: pass|fail|pending|not_observed ; check=<URL/run-ID/attempt> ; event=<pull_request|other>
ci_identity: pr=<N> ; event_head=<PR head SHA A> ; tested_sha=<merge SHA M | head SHA A> ; event_base=<base SHA B if available>
finding: issue=<N> round=<R> karte_verdict=<value> unresolved=<IDs> owner_ref=<ref-or-none>
~~~

- source of truth：レビュー本文/原本artifact（存在する場合）、PRのCI run、Karte。head証拠を別の手動台帳へ二重保存しない。
- **diff != complete**：既存仕様どおり自己finding blocker+STOP。全差分が読めないのにcleanと言わない。
- **CIの同一head判定**：`pull_request` runではGitHub Actionsの `GITHUB_SHA` / checkout既定refは通常 `refs/pull/N/merge` のテスト対象マージコミット **M** で、`github.event.pull_request.head.sha` はPR head **A**。**MとAのSHA値は一致しなくてよい**。run ID/attempt、event種別、PR番号、event内head A、checkout/tested SHA M（必要ならevent base B）を同一runの信頼できる証拠で結び、最新のPR head=Aかを検査する。明示的にheadをcheckoutするworkflowではtested SHA=Aとなる。run側の単一 `head_sha` 欄だけをAとの等価比較に使わない。
- **ci != pass**：必要なCIが満たされていない旨を報告し、merge可能との案内をしない（レビュー自体のSTOP判定は既存規定に従う）。
- **head不一致**：event内headが現在のPR head Bへ更新済みであれば、旧head A由来のMで成功したrunを採用しない。base更新により検査対象が変化した場合も鮮度を確認し、情報を取得できなければ `not_observed`（検証不能）とする。旧レビュー・CI証拠を現headへ転用しない。
- 出典: [GitHub Actions公式: pull_requestのmerge branchとGITHUB_SHA](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)。
- **finding未処置/owner未決**：statusがopenであることだけでなく、既存Karteのdispositionとverdictを確認。scope外でも記録を欠かさない。
- **legacy経路**：現行のread-only legacy承認条件を維持し、対象PRのheadとbase側ローカル実行を混同しない。

### 変更箇所

.ai/agents/pr-reviewer.md の「Finding ID と出力」に証拠4行を追記する候補（2a/2bで適用先を区別）。issue-pipelineの主文脈は既存のcapture/取り込みを用いる。#375/#409実装後はその保存済みartifactフィールドへ対応させる。既に同じ束縛が現状で成立しているなら**コード変更ゼロ、保証の実測証拠整理で完了可能**。

### 試験方法

- S5-T1 head Aに対応する `pull_request` run（event head=A、tested merge SHA=M、PR番号一致）がGreen、diff全読了、owner未決なし→M≠AでもCI成功を有効とする。
- S5-T2 RTKの途中切詰め・保存ファイルの1行でも未読→blocker+STOP。
- S5-T3 PR headがAからBに更新→旧event head=A・tested SHA=Mで成功したrunはBのCI成功として採用しない。
- S5-T4 run ID・event・PR番号・head・tested SHAの対応が不明、別run/別PRに混入、またはbase更新後の鮮度が不明→CI成功と報告しない。
- S5-T5 OOS実害にdispositionなし→Karteのcleanを偽装しない。
- S5-T6 legacy PRではbase側local unittestをそのPRのCIとして報告しない。

### AC-S5

- [ ] 対象PR/head OID、diff読了、CI run ID/attempt・event PR番号・event head・実tested SHA（merge SHAを含む）、Karte round/未処置状態を既存成果物で照合できる。
- [ ] `pull_request` のevent head=A / tested merge SHA=M（M≠A）を正しく受理し、head=Bへ更新した後はA由来runを拒否する両方向fixtureがあり、T2〜T6も検証される。
- [ ] reviewerは自分のレビュー結果からmerge実行せず、owner向けblocker reportを残す。
- [ ] #375と#409の実行台帳/原本を重複新設していない。
- [ ] 現行実装ですでに満たす場合は、必要なコード差分が無いことを証拠付きで説明できる。

## S6 変更特性に応じた製品実環境の検証設計

### 現行契約と対象

ChangePlan.operational_verification（issue_envelope/schema.py）と、#652 / issue_envelope/verify/designs/post-merge-verification-371.md の初回live検証ケースを再利用する。静的仕様や純粋なPythonロジックのすべてを実機検証する要求はしない。silent-failure-diagnosisの既存D0–D8に従い、権限拒否時の迂回プローブを禁じる。

**Live指定の条件**：①hook/Matcher発火、②特定PFのtools/permission、③CIのworkflow起動/Pages、④外部CLIバージョン・profile pin、⑤worktree/lockなど実ファイルとプロセスの同期、⑥外部API/cron時刻。該当しない単純な関数はunittestとintegration testで完結できる。

### テストケースレコードの設計（既存ChangePlan TEXTまたは検証Issue本文で保持）

~~~text
case_id: LIVE-<issue>-01
behavior: 正規product sessionでの具体操作
target: repo/branch/OID/role/PF/CLI version/permission profile OID
preconditions: trust、setup、isolated workspace、認可予算、認証
expected: 許可/拒否、保存artifact、hook発火ログ
method: 正規入口、監査可能なテスト用操作
evidence: run ID / command-result / tool-log / artifact digest / workflow URL
result: pass | fail | blocked | not_run
followup: 未検証時の再実行条件とowner判断
~~~

**判定規則**：実測の正常成功も期待された拒否もpass。設定に存在するだけ、mock結果、exit 0だけ、古いversion、権限を緩めた環境での成功はlive passにしない。未実測/前提欠落はblockedまたはnot_run。証拠参照が取れなければpassとしない。

### 実施アーキテクチャ

1. plannerが検証要否とケースIDをCP.operational_verificationへ記録。
2. premergeではunit/mock/CIを実施して**何を保証したか**を区別。
3. profile pinやtrusted環境等、merge後のdefault branchでしか実施できないものは、既定の別verification Issueに切り出す（#652がその実例）。それを実装PRの未実測として残し、実行不要だと読み替えない。
4. 実機試験は本番に影響のない隔離branch・読み取り専用シナリオ、または安全に拒否を確認できる対象に限定。D0の正しいdenyを見つけたらその場で実験をやめる。
5. 課金、秘密、外部投稿、権限変更、Release公開を必要とする実機実行は既存承認境界を通す。許可がなければblockedとして止める。
6. 一回検証は常設監視とは別成果物。必要な継続監視はL6や既存監視Issueへ切り分ける。

### 変更先

.ai/agents/change-planner.mdのoperational_verification記述を最小具体化。既存 #652 検証設計・ケースのschema/出力書式に合わせ、実機レシピの正本を分散させない。製品用hookの権限・trust設定を検証のために緩めない。特に codex_worktree_exec/profile_pin.py の origin/main pinを変更しない。

### 試験

- S6-T1 hookが正規product経路から発火し所定の追加コンテキスト/denyを返した実証（フック単体成功ではない）。
- S6-T2 ローカルmock成功だが製品hookを発火させていない→not_run。
- S6-T3 origin/main profile pinを満たさず正規起動拒否→未mergeの起動拒否テストはpass、live実dispatchはblocked。
- S6-T4 外部API unavailable→blocked。APIを使えないセッションの成功と報告しない。
- S6-T5 サブロールのreadonly権限/author権限が各roleで実証される。
- S6-T6 本番危険操作に相当する拒否試験は、試験対象を制限して破壊操作が実行されないことまで確認する。

### AC-S6

- [ ] 変更面に基づくlive要否の判定規則と、対象外理由が記録される。
- [ ] 1ケースごとに対象OID/環境/入口/期待/実際/証拠/結果が揃う。
- [ ] pass/fail/blocked/not_runが厳格に区別され、mock等の成功をlive passに読み替えない。
- [ ] #652へ新しい独自実行経路を増やさず、現在の適用対象だけ実測する。
- [ ] 既存D0・trust/pin/費用の拒否を緩めない。

## 初回導入の具体案

- 安全ゲートに関する1PRにS1+S2+S3+S5を、通常のロジック変更1PRにS1+S2+S4+S5を適用する。S6は該当する場合のみ。
- 追加調査時間、merge前に見つけた実害、同型探索の発見数、誤deny、review round数を記録。
- 対策の有効性はまだ実測していないので、効果の大小・全件導入の採否はこの記録から判断する。
- 実装順の正式承認、既存IssueへのAC追加、新Issue起票は本設計段階では実施しない。
