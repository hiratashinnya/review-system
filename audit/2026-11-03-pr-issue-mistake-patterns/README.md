# マージ済みPRレビュー・不具合Issueに見られる反復ミスの分析と対策案

- 記録日: 2026-11-03（JST）
- 対象: hiratashinnya/review-system
- 調査・記録主体: ChatGPT (AI)
- 状態: 調査結果・対策**原案**。実装順序、IssueのAC変更、既存決定の覆しは承認されていない。
- 位置付け: 監査・分析レポート。規範の正本や個別Issueの代替ではない。

## 0. 要旨

同じ失敗を繰り返す最大の要因は、個別ファイル内の単純なミスだけではなく、(A) 上流・下流の契約接続の不足、(B) 異常系・実行境界の漏れ、(C) 修正時の同型箇所への横展開不足、(D) テスト／CIの成功を実機の保証と取り違えること、(E) 指摘・状態・オーナー判断のクローズが不完全なことにある。

対策は二段構えとする。

1. **短期:** 既存工程を増やさず、変更影響面・同型探索・ALLOW/DENY両方向の反例・変異テスト・レビュー読了範囲・必要な実機証跡を、既存の調査／設計／レビューに小さく追加する。
2. **長期:** 契約の接続、状態遷移と回復、tool実行権限、CI検証対象、finding処置・停止判定を、証拠に拘束した決定論的な機械検査にする。独自の台帳・ゲートを重複新設しない。

「高確実性」は全不具合の撲滅を意味しない。対象とする失敗クラス、検証環境、拒否すべき入力、回復条件を限定して、それらに対し再現可能な検証があることを意味する。

## 1. 調査方法・範囲・限界

GitHubのマージ済みPRを、コメント数が多いもの、最近のもの、特定機構（ゲート、worktree、issue-pipeline、レビュー、CI）のものから分散して選び、会話・インラインコメント・レビュー本文を確認した。IssueはOPEN/CLOSEDを区別せず、Bugラベルに加え不具合を内容に含むmaintenance、testing、関連語検索の結果を参照した。

- 発見された検索集合: type:bug 64件、type:maintenance 39件、concern:testing 53件。**重複する集合であり合計は不可**。全件を本文まで精査した件数ではない。
- マージ済みPRのコメントを約45件のPRから確認した。PRの全件・全コメントの悉皆調査ではない。レビューコメントにはAIが提示した未実証の懸念と実測済み所見が混在する。
- 「多く見られる」は、複数の独立した事例や再発のある**定性的な表現**。ここに記す25カテゴリは頻度順位でも統計的発生率でもない。
- 根拠の強さは、Issue本文に実測・再現あり、レビューでテスト実測あり、コード読みや設計上の予測に分けて理解する。参照先が後日更新されることがある。
- IssueのOPEN/CLOSEDは2026-11-03確認時点。時間経過とともに変わり得る。関連Issueを挙げることは、すべての要求が未実装であることを意味しない。
- PRレビューで検出した「未修正時の欠陥」と、現時点のmainに残る「未解決の不具合」を混同しない。

GitHub参照: https://github.com/hiratashinnya/review-system

## 2. 失敗パターンの収集結果（25分類）

### 2.1 契約・ガイダンス（1–6）

| ID | 反復パターン | 根拠例 | 見落としやすい確認点 |
|---|---|---|---|
| 01 | 使用を指示するtoolが実行時に無い・ゲートに塞がれる | [#535](https://github.com/hiratashinnya/review-system/issues/535)、[#725](https://github.com/hiratashinnya/review-system/issues/725) | frontmatterの宣言だけでなく実行PFのtool一覧と許可経路 |
| 02 | 独立した契約が同時に満たせない | [#323](https://github.com/hiratashinnya/review-system/issues/323)、[#685](https://github.com/hiratashinnya/review-system/issues/685) | 呼出側と被呼出側を結ぶ実操作、checkout、パス |
| 03 | 呼出契約の必須入力が生成promptに渡されない | [PR #520](https://github.com/hiratashinnya/review-system/pull/520#issuecomment-5689799937) | producer→consumerの必須パラメータとOID |
| 04 | 正本の変更が全利用側・CI起動条件へ波及しない | [#468](https://github.com/hiratashinnya/review-system/issues/468)、[#467](https://github.com/hiratashinnya/review-system/issues/467) | 共通本文、PF wrapper、生成物、CIフィルタ |
| 05 | 実装と文書・コメント・CLI例が食い違う | [#342](https://github.com/hiratashinnya/review-system/issues/342)、[#714](https://github.com/hiratashinnya/review-system/issues/714)、[PR #66](https://github.com/hiratashinnya/review-system/pull/66#discussion_r3509453757) | 変更した仕様の古い記述を他所から検索 |
| 06 | 工程・ロールの担当境界に実装空白がある | [#663](https://github.com/hiratashinnya/review-system/issues/663)、[#723](https://github.com/hiratashinnya/review-system/issues/723) | 誰が実際に成果を生成・検査・承認できるか |

### 2.2 ゲート・安全・入力（7–12）

| ID | 反復パターン | 根拠例 | 見落としやすい確認点 |
|---|---|---|---|
| 07 | raw文字列・regexでコマンドを判定し、引用/パイプ/別表現を見逃す | [PR #348](https://github.com/hiratashinnya/review-system/pull/348#issuecomment-5237509707)、[PR #219](https://github.com/hiratashinnya/review-system/pull/219#issuecomment-4950837745) | 正規化後の意味、実行経路、同型の別表現 |
| 08 | 例外・UNKNOWN・Noneの扱いから意図せぬfail-open | [#722](https://github.com/hiratashinnya/review-system/issues/722)、[PR #219](https://github.com/hiratashinnya/review-system/pull/219#issuecomment-4950837745) | hook終了コード・各判定値の実際の意味 |
| 09 | 過剰なfail-close・保守的分類で正常操作も停止 | [#533](https://github.com/hiratashinnya/review-system/issues/533)、[#597](https://github.com/hiratashinnya/review-system/issues/597)、[#655](https://github.com/hiratashinnya/review-system/issues/655) | 禁止操作だけでなく正常操作のALLOW試験 |
| 10 | 直接操作のみ制御し、サブ委譲やworkflow dispatchを見落とす | [#517](https://github.com/hiratashinnya/review-system/issues/517)、[PR #727](https://github.com/hiratashinnya/review-system/pull/727#issuecomment-6582308269) | 代理実行や権限を持つ別主体への遷移 |
| 11 | パス・symlink・redirectなど信頼境界の見落とし | [PR #2](https://github.com/hiratashinnya/review-system/pull/2#discussion_r3369395688)、[PR #659](https://github.com/hiratashinnya/review-system/pull/659#pullrequestreview-5561712938) | 実際に書込・通信する直前の束縛 |
| 12 | 識別子・真正性・参照先の検証が弱い | [PR #316](https://github.com/hiratashinnya/review-system/pull/316#issuecomment-5158710190)、[PR #633](https://github.com/hiratashinnya/review-system/pull/633#pullrequestreview-5538114139) | 本人性、repository、item、証拠の由来 |

### 2.3 状態・実行環境（13–18）

| ID | 反復パターン | 根拠例 | 見落としやすい確認点 |
|---|---|---|---|
| 13 | worktree/branch ref/lock/ledgerの後始末が非対称 | [#426](https://github.com/hiratashinnya/review-system/issues/426)、[#464](https://github.com/hiratashinnya/review-system/issues/464)、[#502](https://github.com/hiratashinnya/review-system/issues/502)、[#559](https://github.com/hiratashinnya/review-system/issues/559) | 異常終了後に**次のdispatchができるか** |
| 14 | cwd・base OID・snapshot参照先を取り違える | [#437](https://github.com/hiratashinnya/review-system/issues/437)、[#355](https://github.com/hiratashinnya/review-system/issues/355) | primary/isolated worktree、push前後の差分 |
| 15 | 保存確定とCLI返却が食い違う・read-create-writeが非原子的 | [#679](https://github.com/hiratashinnya/review-system/issues/679)、[PR #644](https://github.com/hiratashinnya/review-system/pull/644#issuecomment-6208219642) | 中間失敗・再試行・重複作成・結果の一致 |
| 16 | 実行ID一意性や冪等性を楽観する | [PR #2](https://github.com/hiratashinnya/review-system/pull/2#discussion_r3369395719)、[#694](https://github.com/hiratashinnya/review-system/issues/694) | 同時実行・再入・途中終了 |
| 17 | cron/API/CLI版など製品環境の実態を推測で代用 | [#363](https://github.com/hiratashinnya/review-system/issues/363)、[#345](https://github.com/hiratashinnya/review-system/issues/345)、[PR #680](https://github.com/hiratashinnya/review-system/pull/680#pullrequestreview-5609758861) | 実機・実版・実権限で確認した証拠 |
| 18 | 入力型、例外、終了コードの契約が不一致 | [#719](https://github.com/hiratashinnya/review-system/issues/719)、[#721](https://github.com/hiratashinnya/review-system/issues/721) | 非ASCII数字、巨大入力、argparse既定値 |

### 2.4 テスト・レビュー・記録（19–25）

| ID | 反復パターン | 根拠例 | 見落としやすい確認点 |
|---|---|---|---|
| 19 | 不正な挙動でもPASSする恒真・緩いテスト | [#720](https://github.com/hiratashinnya/review-system/issues/720)、[#728](https://github.com/hiratashinnya/review-system/issues/728) | 変異を入れて、テストが実際に失敗するか |
| 20 | mock/静的設定/直接実行を、製品hookの実発火と同一視 | [PR #322](https://github.com/hiratashinnya/review-system/pull/322#issuecomment-5230387421)、[PR #680](https://github.com/hiratashinnya/review-system/pull/680#pullrequestreview-5609814645) | trusted/enabled/fired、製品版、期待する操作 |
| 21 | CIのpaths・suiteが実際の変更や本番経路を覆わない | [#467](https://github.com/hiratashinnya/review-system/issues/467)、[PR #642](https://github.com/hiratashinnya/review-system/pull/642#issuecomment-6207764186) | 差分→workflow→suite→本番処理の接続 |
| 22 | 大きなPRの差分が省略され未読領域が残る | [#530](https://github.com/hiratashinnya/review-system/issues/530)、[PR #650](https://github.com/hiratashinnya/review-system/pull/650#issuecomment-6226756000) | full diff取得、読了範囲、head一致 |
| 23 | scope外や処置未決のfindingが完了判定から消える | [#495](https://github.com/hiratashinnya/review-system/issues/495)、[#513](https://github.com/hiratashinnya/review-system/issues/513) | 原本性、harm、disposition、stop条件 |
| 24 | 修正した判定経路だけ直し、同型の別経路を放置 | [#503](https://github.com/hiratashinnya/review-system/issues/503)、[#511](https://github.com/hiratashinnya/review-system/issues/511) | status/check/escalateや各呼出先の同一意味 |
| 25 | 指標・監査台帳が暗黙の前提や登録漏れを検出できない | [#488](https://github.com/hiratashinnya/review-system/issues/488)、[#493](https://github.com/hiratashinnya/review-system/issues/493)、[#724](https://github.com/hiratashinnya/review-system/issues/724) | 分母、時間窓、参照表記、未登録事象 |

## 3. 共通原因の整理

| 原因クラス | 説明 | パターンID | 対策の設計原則 |
|---|---|---|---|
| A. 契約の接続不良 | それぞれの仕様・ロールは正しく見えても、入口→実行→返却が成立しない | 01–06, 14, 22 | producer・consumer・権限・環境を**同じケース**で検証 |
| B. 境界条件の設計不足 | 引用、型不正、部分失敗、競合、間接実行で破綻 | 07–12, 15–18 | 安全/禁止を両方向で検証。UNKNOWNは明示する |
| C. 局所是正・横展開不足 | 1関数は直っても同じ意味を持つ別経路に残る | 04, 05, 09, 13, 21, 24 | 同型検索と影響面の閉包を修正範囲と区別して示す |
| D. テスト成功の過大解釈 | mock成功、CI緑、特定文字列があるだけで保証と誤認 | 17, 19–22, 25 | 各証拠が何を保証しないかも記録 |
| E. 発見・状態・承認のクローズ不足 | scope外、失敗状態、未決判断が見えなくなる | 13, 15, 23, 25 | 元findingと処置・運用検証・オーナー判断を追跡 |

上表は**多対多**。分類の数は因果頻度・故障率を意味しない。

## 4. 短期対策：既存工程を軽く強化する

効果見込みは過去の実測削減率ではなく、確認した反復失敗クラスとの適合性に基づく相対評価。工数は1人が既存実装を活用する概算で、調査・CI待ち・オーナー承認待ちを含めない。

| ID | 施策と実施方法 | 初期作業量の目安 | 効果見込み | 既存Issue・注意点 |
|---|---|---|---|---|
| S1 | **変更影響面の横睨み**。影響するrole、PF、入口、呼出先、state/cleanup、正本・mirror、CIと外部前提をチェックし、「確認済／対象外理由／未確認」を記録。全Issueの新規文書を義務にせず、既存Investigation/ChangePlanに追記 | 半日～2日 | 高（01–06、24） | [#370](https://github.com/hiratashinnya/review-system/issues/370)、[#371](https://github.com/hiratashinnya/review-system/issues/371)の既存affected-surface要求を利用 |
| S2 | **同型不具合探索を是正の一部にする**。修正原因を一文で表し、同じ判定/例外/意味を持つ関数・呼出先を検索して、修正・別Issue・対象外を分類する。修正権限・スコープを勝手に拡大しない | 半日～1日で運用化、個別調査は別 | 高（13、24） | [#370](https://github.com/hiratashinnya/review-system/issues/370)、[#691](https://github.com/hiratashinnya/review-system/issues/691)と重複設計しない |
| S3 | **ゲートのALLOW/DENY対照試験を先行追加**。修正前後の同一コマンド集で、悪性入力のdeny、正常入力のallow、曖昧入力の安全処理、hook実際の終了コードまで固定する。新規parserを丸ごと作らない | 対象1機構あたり1～3日 | 高（07–10） | [#533](https://github.com/hiratashinnya/review-system/issues/533)、[#722](https://github.com/hiratashinnya/review-system/issues/722)等を起点 |
| S4 | **重要分岐の小規模変異テスト**。verdict、終了コード、入力ガードについて意図的に誤実装へ書き換え、期待するテストが赤になることを記録する。最初は重要5分岐程度に限定 | 1～3日 | 高（19）※対象分岐に限る | [#720](https://github.com/hiratashinnya/review-system/issues/720)、[#728](https://github.com/hiratashinnya/review-system/issues/728)。全suiteへの一括導入はしない |
| S5 | **レビュー証跡の3点確認**。対象headに対する①diff全文読了または未読範囲の明記、②そのheadのCI、③未処置finding／承認・実測未達の明記。すでに持つreceiptとkarteを使い新台帳を作らない | 半日～1日で様式化 | 中～高（20–23） | [#530](https://github.com/hiratashinnya/review-system/issues/530)、[#513](https://github.com/hiratashinnya/review-system/issues/513) |
| S6 | **実機検証を必要ケースへ限定して切り出す**。hook発火、PF固有tool、GitHub Actions実起動、CLI対応版、異常回復はmockでは代用せず、最終headまたはmerge後に実測し証拠を保存する。製品上の制約があるなら「未実測」を維持 | 1～3日で対象・手順定義、実測負荷は別 | 高（17、20、21）※適用環境に限る | [#652](https://github.com/hiratashinnya/review-system/issues/652)、[#363](https://github.com/hiratashinnya/review-system/issues/363) |

### 短期でまず試す最小セット

- 代表的な1件の**ゲート変更PR**で、S1+S2+S3+S5を既存手順に適用する。
- 代表的な1件の**通常のロジック変更PR**で、S1+S2+S4+S5を適用する。
- 各PRで、チェックにかかった実時間、merge前に新たに見つけた実害finding、修正後の同型見落とし、既存レビューの重複作業、誤拒否件数を記録する。改善に寄与しないチェックは増やさない。
- 別の強制フェーズ・スキル・台帳はこの段階では新設しない。

## 5. 長期対策：失敗クラスごとの機械的保証を作る

| ID | 高確実性対策と設計する保証 | 規模感 | 先行・関連Issue | トレードオフ |
|---|---|---|---|---|
| L1 | **工程間の実行契約をグラフで検証**。run/phase/producer/consumer/branch-OID/artifact digest/必須tool・role別能力/trace linkを実行前・引継ぎ前に照合。対象ケースが成立しないなら次工程へ進めない | 複数週間級 | [#409](https://github.com/hiratashinnya/review-system/issues/409)、[#703](https://github.com/hiratashinnya/review-system/issues/703)、[#652](https://github.com/hiratashinnya/review-system/issues/652)、実装済[#371](https://github.com/hiratashinnya/review-system/issues/371) | 誤拒否・運用負荷を増やす可能性。既存issue_envelopeとrun台帳に接続、重複正本を作らない |
| L2 | **worktree・handoff・結果保存の状態遷移と故障注入**。正常/timeout/二重実行/途中失敗/再起動で、返却結果・保存結果・リソース所有が整合し、次dispatchへ回復できることを実Git/I/O試験で保証 | 複数週間級 | [#559](https://github.com/hiratashinnya/review-system/issues/559)、[#679](https://github.com/hiratashinnya/review-system/issues/679)、[#699](https://github.com/hiratashinnya/review-system/issues/699)、[#409](https://github.com/hiratashinnya/review-system/issues/409) | 状態空間が増えるため、まず実測済み再発経路から固定。手動回復を消す前に誤削除がないことを確認 |
| L3 | **コマンド安全性を閉じた操作契約に寄せる**。可能な操作は構造化verb・引数で許可し、shell一般構文の完全解析へ拡張し続けない。非対応の動的実行を許す範囲・拒否する範囲を明示し、ALLOWとDENYを実shellと差分検証 | 設計変更を伴う複数週間級 | [#699](https://github.com/hiratashinnya/review-system/issues/699)、[#513](https://github.com/hiratashinnya/review-system/issues/513)、過去[#517](https://github.com/hiratashinnya/review-system/issues/517) | 対象toolの呼出形式変更が必要。まず誤操作防止の保護対象に絞り、万能sandboxを目指さない |
| L4 | **変更箇所→CI経路→テスト→実機証跡の対応検証**。CI pathsと実際の検査対象の対応、full diff/head一致、clean-scopeの型/schema、実機専用ケースの未実測を明確に検出 | 複数週間級 | [#701](https://github.com/hiratashinnya/review-system/issues/701)、[#703](https://github.com/hiratashinnya/review-system/issues/703)、[#652](https://github.com/hiratashinnya/review-system/issues/652)、[#702](https://github.com/hiratashinnya/review-system/issues/702) | 全ケースをPR CIで実行するのは非現実的。実機検証は別の完了条件として維持 |
| L5 | **finding原本・処置・停止判定の閉ループ**。独立レビューの原本、triage、オーナー承認されたdisposition、検証済み申し送り、karte verdict/stopを相互に束縛。未決の実害が黙ってclean化しないことを機械テスト | 複数週間級 | [#691](https://github.com/hiratashinnya/review-system/issues/691)、[#513](https://github.com/hiratashinnya/review-system/issues/513)、[#409](https://github.com/hiratashinnya/review-system/issues/409)、対応済[#723](https://github.com/hiratashinnya/review-system/issues/723) | triagerにオーナー権限を与えない。自動処置は明示承認・版付きポリシーの範囲に限定 |
| L6 | **merge後欠陥の計測と対策効果の検証**。発見可能な見逃し／発見済み未処置／実運用でのみ発見／safe default・gate不足を別集計し、対象PR・時刻窓・重複除外を固定して導入前後比較 | 1～数週間級 | [#370](https://github.com/hiratashinnya/review-system/issues/370)、実装済[#488](https://github.com/hiratashinnya/review-system/issues/488) | 現行defect_metricsの定義を黙って変更しない。既存レポートとの比較可能性を保って補助分類を追加 |

### 機械化する順番の考え方

1. **安全性と停止復旧の実害を優先:** L2の既知再発ケース、L5の未決実害停止、L3の危険な迂回／過剰拒否。
2. **上流の契約を固定:** L1で工程入口・実行・受渡しの対応を閉じる。
3. **検証経路を閉じる:** L4を適用して「CI緑＝何を確認したか」を明確にする。
4. **測定で効果を検証:** L6は早期に基準を用意し、他施策の前後比較に使う。

この並びは提案であり実装順序の確定ではない。#699・#701・#702・#703の個別Issueも起票時点では着手順未承認とされている。

## 6. 評価方法：効果を過大評価しない

### 推奨観測値

| 指標 | 定義案 | 観測上の注意 |
|---|---|---|
| merge前捕捉率 | 対象とした再発クラスに属する、merge前に新たに発見した実害finding数 ÷ 同クラスの最終的な確認finding数 | 分母の後追い発見は追跡期限を固定。未観測をゼロ扱いしない |
| 同型漏れ率 | 修正後に同じ根本原因が別経路で新規発見された件数 ÷ 同根本原因を処置した修正案件数 | 同一症状・別原因と、同一原因・別症状を区別 |
| 強制判定の品質 | 禁止入力DENY率、正常入力ALLOW率、UNKNOWN時の処置適合率を**別々に**計測 | deny率だけを上げない。安全性と可用性の両方を見る |
| テスト有効性 | 対象重要分岐に投入した代表変異の検出数 ÷ 投入数 | 代表変異以外への一般化は不可 |
| 実測達成率 | 実機証跡が必要と分類されたシナリオのうち、正規経路で実測が完了した割合 | mock/直接起動を分子に入れない |
| 生産性への影響 | 既存工程の調査・是正・再レビュー工数、誤拒否による復旧回数 | 新規チェックの工数と削減した再作業を合わせて評価 |

### 集計上の必須区別

[#370](https://github.com/hiratashinnya/review-system/issues/370)で定義された次の4分類を守る。

1. merge前に発見可能だったが未検出
2. merge前に発見されていたがOOS/別Issueとして残した
3. merge後のlive運用で初めて観測できた
4. safe default・機械gate・lint不足

この4分類は原因と観測時期が一部重なるため、**単一の排他的な区分として使う際は優先規則の定義が必要**。本レポートは測定ルール自体を上書きしない。

## 7. 既存Issueとの整合・追加起票の要否

### 原則

- #371（工程分離）と#723（実害基準SSoT）は**CLOSED**。同じ機構を作り直さない。
- #370、#409、#513、#559、#652、#691、#699、#701、#702、#703、#720、#728 は確認時点で**OPEN**。短期の実装を新Issue化する前に責務とACの重複を再確認する。
- 「短期の確認項目」は既存のInvestigation/ChangePlan/PRレビューへ**最小差分**で組み込む案を優先する。新しいロール、強制フェーズ、常駐プロンプト、新規台帳の追加を前提にしない。
- #699はfailure/idempotency、#701は型/schema ratchet、#702はログ契約、#703はtrace linkが既に主題。新規の同名包括Issueは不要。
- 既存IssueのAC変更、クローズ、スプリント確定は本レポートでは行わない。対策案はオーナー判断の材料にとどめる。

### 今後の実行単位案（起票前の候補）

- 短期のS1+S2+S5は、横断的に重複したチェックリスト群を増やさず、既存パイプラインの1箇所へ入れる候補。
- S3はゲート対象機構ごとに、S4は#720/#728に沿って小規模に検証し、成功基準を実測してから拡張可否を判断。
- L2は#559と#699の分担、L5は#513と#691と#409の分担、L1/L4は#409/#652/#703の重複整理を先行する。
- 既存Issueに収まらない明確な独立成果が見つかったときだけ、新規Issue案を切り出す。

## 8. このレポートの限界と次の確認事項

- 25分類の真の件数・割合、レビュー発見件数、開発工数削減率は未計測。効果の「高・中」は期待仮説。
- 一部事例は当時のPRレビューにおける**修正前の所見**で、mainに残る欠陥と同義ではない。
- 全PR/全Issue/全コメントの自動採集・重複排除や実機再現を行ったわけではない。悉皆化するなら収集期間・分母・採番・同型クラスタリング・事実/仮説の区別を先に固定する。
- 見逃した不具合だけでなく、正常操作の過剰拒否、手戻り、修正後の再発、レビュー工数も評価する。
- 本レポートの提案は既存仕様・オーナー既決方針を上書きしない。対策の導入前に対象Issueの最新本文と正本を再読する。

---

**要約:** まず既存工程で「変更影響面をつなぐ」「修正時に同型箇所を探す」「テストが誤実装を落とせるか確かめる」を小さく試し、同時に#409/#513/#559/#691/#699等で状態・権限・完了条件の決定論的保証を整える。観測値が得られるまでは効果を断定しない。
