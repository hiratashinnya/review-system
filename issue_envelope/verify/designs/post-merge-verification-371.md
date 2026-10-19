# #652: #371 導入後の工程分離・新ロール権限・adviserを初回実dispatchで検証する

Codex（AI）が、Issue #371 の実装と一回限りの運用検証を分離するために作成した検証計画です。
追跡先は [Issue #652](https://github.com/hiratashinnya/review-system/issues/652)、native parentは #368 です。
2026-10-17にowner認可後の起票とparent relationを取得して確認しました。製品経路の実dispatchは未実測です。

## 目的・背景

Issue #371 が導入する工程分離と新ロールの実行委譲について、default branch に到達した実装を使う初回受け入れ検証を実施し、工程順・権限・失敗時挙動の実測報告を完成させる。

成果は、対象版・環境・ケース別の証拠と判定を含む一つの初回検証報告である。実装変更や継続的な品質効果測定はこの成果に含めない。

Issue #371 本文「運用検証の置き場」は、一度確認すれば済む新機能の初回実挙動を別 verification Issue とし、実装 Issue の完了条件を「検証 Issue の起票と relation」までと定めている。本件はその分離を行う。

## 現状と根拠

- `codex_worktree_exec/profile_pin.py` は、実行worktreeの `.codex/config.toml` のblobが `origin/main` と一致することを起動前に要求する。未mergeの新permission profileを含むPRは、正規CLIでは `CODEX_EXEC_PROFILE_DRIFT` で拒否される。
- このpinは呼び出し側が書き換えたprofileで実行させない信頼境界である。本検証のためにpinを緩めたり、`origin/main` を検証用commitへ差し替えたりしない。
- cloud Codex等で現在利用できるツールの権限と、製品の `codex_worktree_exec` が実際に適用するpermission profileは別物である。subagentでの作業成功やmock runner成功を、製品経路の新ロール実dispatch成功に代用しない。
- 本文作成時点では、#371の最終merge commit、premerge検査ログ、製品経路のlive結果は未確定である。実行時に実際の値・ログを記録し、未実施を合格として記載しない。
- 仕様根拠: https://github.com/hiratashinnya/review-system/issues/371 、`audit/2026-09-21-pipeline-redesign/README.md` の生存決定。

## Scope

### 実行前に確定・記録する事項

1. #371を実装したmerge commitと、実行開始時点のdefault branch OID、profile blob OID、CLI版、OS、PF、実際のpermission regimeを記録する。正規profile pinとtrust検査を通す。
2. premergeの最終テスト・CIを参照し、schema・木/DAG・digest/OID・role binding・STOP等の機械検証と、mockを使った検査を区別する。未merge profile拒否の証拠は「起動拒否の検証」であり実dispatchではないと明記する。
3. 実行するケース、各roleの許可/拒否操作、相談回数・時間・コスト上限、停止・回復方法を開始前に定める。課金の認可が必要なら既存規約に従い、未認可で有料経路を起動しない。
4. テスト専用の隔離領域・対象branchを使う。禁止操作の否定ケースは、拒否されることを確認でき、万一の実行でも実資産を変更しない制御された対象を選ぶ。

### 初回実dispatchのケース

| ケース | 入力・観測対象 | 成功判定 |
|---|---|---|
| 低リスク | 調査省略理由が説明できる小変更を正規pipelineへ渡す | investigationの省略根拠をartifactへ保存し、1a→独立レビュー→1b→独立レビュー→owner承認→2a→独立レビュー→2bの実行順と別コンテキストを証明できる |
| 中リスク | 原因・影響範囲の調査を要するケース | investigatorが証拠付き成果物を返し、その参照を1a以降が利用する。必須工程・レビューを省略しない |
| 高リスク | 共有資産・権限境界など、既存契約のモデル引上げ条件を満たすケース | モデル選定根拠・解決値・実使用値を記録し、必要層で実行する。自動fallbackやレビュー省略を行わない |
| 著作ロール | ac-designer/change-planner/test-writer/issue-implementer | 各roleが承認範囲の成果物を作成し、許可された呼び出し側のcommit/pushを含む正規経路で次工程へ渡す。実際のbranch/OID/worktree継承方式が承認済み設計と一致する |
| readonlyロール | investigator/plan-reviewer/pr-reviewer/adviser | 許可された読取りと所定の返却が成功する一方、成果物編集・push・台帳変更が拒否される。保存は認められたcapture主体だけが行う |
| 共通の権限拒否 | 全AIのmerge、任意再委譲、元roleを超える操作、#608の削除・移動・baseline更新 | 各境界を実行先の機構が拒否する。プロンプトの自己申告やexit codeだけで判定しない |
| adviser正常系 | 担当者が構造化相談を要求し、上位モデルから同じ担当者へ回答を戻す | Issue/role/run/phase/work unit/digest/OIDと回答モデルが束縛され、担当者が採否・理由・実検証を記録する。レビュー合格・STOP解除を助言で代用しない |
| adviser異常系 | 相談起動失敗、部分出力、上限到達を制御して発生させる | 成功・工程completedにせず、理由と試行履歴を主文脈へ返す。予算超過後の反復や自動降格をしない |
| handoff異常系 | 不一致・stale・STOP・未決owner decision・AC未対応の入力を渡す | 後段の実dispatchに進まず拒否し、理由を追跡できる |

各新ロールの権限確認はロール別に記録する。既存implementer/fixerの成功標本を新ロールの成功へ転用しない。各ケースの実行回数・実行時間・artifactサイズ・モデル利用量・得られる範囲の実コストを記録するが、改善効果の数値目標とは扱わない。

### 証拠と結果

報告にはケースID、期待結果、実結果、判定、時刻、role/backend/model、入力artifact参照とdigest、snapshot/出力OID、dispatch・権限拒否ログ、保存先を含める。秘密情報は保存しない。ケースを `pass` / `fail` / `blocked` / `not_run` で区別し、CLIのexit 0だけでは `pass` にしない。

実害のある不一致は既存karteのfindingとして記録し、修正担当と独立再レビューへ戻す。本Issueの成果を報告するために実装担当の完了を偽装しない。

## Out of scope

- profile pin・信頼境界を緩める変更、製品の権限制限をテスト用に迂回すること。
- #371本体や#375/#310/#409の重複実装、既存finding schemaの変更。
- agyの#606/#628未到達経路の有効化。実行時も条件未達なら「無効化の維持」を確認し、agy実dispatch成功とは記録しない。agyの初回確認は成立後の対象範囲をownerと整理する。
- hookの定常発火・snapshot鮮度などの常設監視、長期観測、導入後品質効果の採否判定。
- #371固有の品質目標、cohort、観測窓、採否条件をAIが新たな数値で確定すること。必要なowner判断は#368/#370の計測契約側へ申し送る。
- 本文案だけに基づく新Issue・Project・relationへの書込み。

## Acceptance criteria

- [ ] 検証対象merge commit・実行環境・default branch/profile blobのOIDと、正規pin/trust検査結果を記録している。
- [ ] premerge機械検証、mock検証、製品経路のlive実測、未検証を区別した対応表がある。
- [ ] 低・中・高リスク経路を実dispatchし、工程順、独立コンテキスト、各レビュー、owner承認点、artifact/OIDの継承を証拠で確認している。
- [ ] 各新ロールの許可操作と拒否操作を実起動で確認し、readonlyの編集/push/台帳操作、全AIのmerge、任意再委譲、#608境界が拒否される。
- [ ] adviserの相談→同じ担当者への返却→採否→実検証を確認し、入力・回答・モデル・時間・利用量/コストを追跡できる。
- [ ] 相談失敗・部分出力・予算到達、および不正handoffで成功扱いや後段dispatchが起きないことを実測している。
- [ ] 有効化不能なbackendと理由を明記しており、agyの未到達経路を有効化していない。
- [ ] 実行対象ケースに `fail` / `blocked` / `not_run` が残る場合は完了扱いせず、理由・必要判断・再実行条件を報告している。期待された拒否はケースの `pass` として記録する。
- [ ] 実害findingを既存karteで追跡し、是正が必要な場合は独立再レビュー後の再実測まで報告に含めている。
- [ ] 一回検証報告と証拠の永続パスを#371およびtracking先から参照でき、継続監視や品質効果の採否を本Issueの完了と混同していない。

## Dependencies / Related issues

- 実行開始条件: #371の対象実装とprofileがdefault branchへ到達していること。AIはmergeを実行しない。
- 実装との関係: #371から本検証への参照を付ける。**#371を本検証でblocked-byにしない**。実装とlive検証の完了を分離する既決契約を維持する。
- tracking relation案: #368/#370の実際のparent/sub-issue構造を起票前に読み、初回検証成果を包含する既存tracking親のsub-issueとする。他方へrelated参照を付ける。二つのnative parentを新設したり、優先度・日程・既存関係を本文案だけで変更したりしない。
- #538/#542: 導入済みCodex経路・owner手動merge境界の根拠。
- #606/#628: agyの有効化条件。条件未達の経路を本Issueの成功標本に含めない。
- #375/#310/#409: findingと将来runの接続境界。既存契約を利用し、未実装機構を利用可能と扱わない。
- #513/#517/#565/#608: STOP、再委譲、role境界と禁止操作の関連契約。

## 起票前の確認事項（履歴）

外部投稿・Project変更・relation変更は未実施。既存open/closed Issueとの重複、live labels、Project候補・fields/options・更新権限、現行relationsは起票前に取得する。分類はverification相当の成果だが、`type:verification` が存在するとは仮定せず、live taxonomyでownerに予定値を提示する。Horizon・Priority・実行時期、品質効果の目標/cohort/窓は本案では確定しない。

上記は起票前の状態を保存した履歴である。owner認可後に重複・taxonomyを取得し、承認本文で #652 を作成してparent #368を確認した。
ProjectへのAI書込は行わず、実測対象版・実行開始条件・完了証拠は #652 で追跡する。
