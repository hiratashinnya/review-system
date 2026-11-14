# issue-pipeline 品質分類と #371 導入前 baseline

> Codex AI agent が Issue #370 Wave 0 として 2026-08-26 に作成した。
> この文書は #371 の導入前測定であり、導入後の再計測結果ではない。

## 1. live binding

| 項目 | 再束縛した値 |
|---|---|
| repository | `hiratashinnya/review-system` |
| default/base branch | `main` |
| baseline snapshot | `main@e9856dacbdf1b47bee0ac5de861886d8d0dccb2d` |
| quality issue | [#370](https://github.com/hiratashinnya/review-system/issues/370)（open） |
| native parent | [#368](https://github.com/hiratashinnya/review-system/issues/368)（open） |
| intervention issue | [#371](https://github.com/hiratashinnya/review-system/issues/371)（open、同じく #368 の子） |
| native dependency | #370 の `blocked_by` / `blocking` はともに 0。#371 との関係は sibling と本文上の品質証拠引き渡しであり、native dependency ではない |

## 2. 分類規則

Issue #370 本文の4分類を、次の2軸として使う。C1〜C3は排他的な lifecycle 分類、C4は原因・予防統制の不足を示す直交タグである。C4をC1〜C3と排他的にすると「merge前に見つかっていたが、safe default 不足でもあった」という事実を失うため、合計100%を要求しない。

| ID | 分類 | 判定規則 |
|---|---|---|
| C1 | merge前に発見可能だったが未検出 | merge前に repository/diff/既存契約から検出できた証拠がある一方、実装・レビュー・是正のどこにも finding/OOS として残っていない |
| C2 | merge前に発見済みだが OOS / 別 Issue として残したまま merge | merge前の PR 本文、レビュー、是正、実測のいずれかに既知事項として残り、元 PR では処置されなかった |
| C3 | merge後の live 運用でのみ観測可能 | default branch 上の workflow、外部 scheduler、実運用 transport など、merge前には成立しない条件で初めて観測できた |
| C4 | safe default・機械 gate・lint 不足 | 誤用しやすい既定値、必要能力を拒否/許可する gate、同期・契約 drift lint、closure gate の不足が再発経路に含まれる。C1〜C3のいずれにも併記できる |

「発見可能」は後知恵だけでは付けない。merge前の artifact に証拠が無い場合、単に静的に読めそうだったという理由だけでC1へ算入しない。既知OOSをC1へ重複算入しない。

## 3. 分母と集計単位

Issue #370 が列挙した参照 Issue は7件（#354 / #355 / #356 / #357 / #360 / #362 / #363）である。ただし #357 は PR #353 の派生ではなく、Issue #345 の調査コメント訂正規範であるため、PR混入率の分析分母から除外する。

- 参照総数: **7 Issue**
- 系譜補正後の Issue 単位分母: **6 Issue**
- 元 PR 分母: **3 PR**（#353 / #358 / #359）
- finding 単位分母: **8 finding**。#360だけが3 findingを束ね、ほか5 Issueは各1 findingとして展開する
- 除外: **1 Issue**（#357）。分類漏れではなく `outside_cohort` として台帳に残す

## 4. 事例台帳

| Issue / finding | 元PR | lifecycle | C4 | merge前後の根拠 | #371へ渡す主な risk signal |
|---|---:|---|---|---|---|
| [#354](https://github.com/hiratashinnya/review-system/issues/354) | [#353](https://github.com/hiratashinnya/review-system/pull/353) | C2 | あり | PR本文が `issue-fixer` への isolation 要求をスコープ外と明記。レビューでも是正ラウンドのbranch移送問題をmerge前に検出 | role parity、PF差、worktree/branch lifecycle、権限gate |
| [#355](https://github.com/hiratashinnya/review-system/issues/355) | [#353](https://github.com/hiratashinnya/review-system/pull/353) | C2 | あり | PR #353 の是正round 1で、commit/push後の `--base HEAD` により `touched: []` が実測済み | unsafe default、append-only、結果検証、fail-close |
| [#356](https://github.com/hiratashinnya/review-system/issues/356) | [#353](https://github.com/hiratashinnya/review-system/pull/353) | C2 | あり | 実装中に `asset_parity check` がgateで拒否され、代替確認とCI依存を自己申告済み | role capability、PF asset parity、command gate、CI lint |
| [#357](https://github.com/hiratashinnya/review-system/issues/357) | — | `outside_cohort` | 集計外 | 発端は Issue #345 の調査コメント訂正。PR #353 merge後派生として数えない | evidence lineage、訂正と履歴保全の分離 |
| [#360-1](https://github.com/hiratashinnya/review-system/issues/360) ctx記述 stale | [#358](https://github.com/hiratashinnya/review-system/pull/358) | C2 | あり | PR本文の `OOS-323-01` と reviewer が独立にmerge前検出 | PF/同期先、既存記述の陳腐化、content lint |
| [#360-2](https://github.com/hiratashinnya/review-system/issues/360) clean merge経路のworktree解放欠落 | [#358](https://github.com/hiratashinnya/review-system/pull/358) | C2 | あり | reviewer がmerge前に検出し、PR #353由来の既存事象として申し送り | 分岐網羅、branch lifecycle、closure policy |
| [#360-3](https://github.com/hiratashinnya/review-system/issues/360) agent定義のsession固定 | [#358](https://github.com/hiratashinnya/review-system/pull/358) | C2 | あり | PR #358 の是正roundで新契約が同一sessionに反映されないことをmerge前に実測 | lifecycle、PF runtime、snapshot/外部仮定、運用検証 |
| [#362](https://github.com/hiratashinnya/review-system/issues/362) | [#359](https://github.com/hiratashinnya/review-system/pull/359) | C2 | あり | round 2 reviewer が `OOS-345-R2-01` としてmerge前に発見し、openのままmergeable判定 | contract drift、既知OOS、closure policy、doc lint |
| [#363](https://github.com/hiratashinnya/review-system/issues/363) | [#359](https://github.com/hiratashinnya/review-system/pull/359) | C3 | なし | merge後のscheduled workflowで初めて74〜104分間隔を実測。staleness gate自体はfail-closeしていた | 外部scheduler仮定、post-merge operational verification、close保留 |

## 5. 導入前 baseline

### 5.1 対象 cohort の再集計

| 指標 | Issue単位 | finding単位 | 解釈 |
|---|---:|---:|---|
| C1: merge前に発見可能だったが未検出 | **0 / 6 = 0.0%** | **0 / 8 = 0.0%** | この限定標本から「reviewerの未検出」を混入原因とは結論できない |
| C2: merge前に発見済みの既知OOS/別Issue | **5 / 6 = 83.3%** | **7 / 8 = 87.5%** | 主信号は検出不足より、既知残件を明示判断なしにcarryしたclosure policy不足 |
| C3: merge後live運用のみ観測可能 | **1 / 6 = 16.7%** | **1 / 8 = 12.5%** | merge前の静的レビューではなく、運用検証とclose保留で扱う |
| C4: safe default・機械gate・lint不足タグ | **5 / 6 = 83.3%** | **7 / 8 = 87.5%** | C1〜C3と重複する原因タグ。#363はgate不足でなく外部仮定の実測不足 |

Issue作成数だけを見ると、補正後も **6 Issue / 3 source PR = 2.00 Issue/PR** である。しかし、そのうち5件はmerge前に既知、1件はmerge後のみ観測可能で、C1は0件だった。したがって、この値をそのまま「reviewerが見逃した欠陥率」と呼ばない。

### 5.2 全体の既存 baseline

親 #368 の 2026-08-01〜2026-08-16 集計は、merge **22 PR**、新規 **41 Issue**、**41 / 22 = 1.86 Issue/PR**、open純増 **+21 / 15日** である。この値は全新規Issueを含む流量指標であり、上の限定cohortのC1〜C4と分子の意味が違う。Wave 5では1.86との比較と、分類後の品質指標を別々に提示する。

## 6. #371へ渡す taxonomy / risk signals

#371 の investigation artifact の affected-surface matrix は、少なくとも次を列として持つ。

| signal | 確認質問 | 本baselineの実例 |
|---|---|---|
| role | 実装者、fixer、reviewer、主文脈で契約・権限・既定値が揃うか | #354 / #356 |
| PF | `.ai`正本とClaude/Codex/GitHub wrapper、実効toolが一致するか | #354 / #356 / #360-1 |
| branch/worktree | 作成、受渡し、是正、clean merge、解放の全分岐が閉じるか | #354 / #360-2 |
| lifecycle/closure | 未解消finding、既知OOS、owner decision、運用検証が残る時にmerge/closeを止めるか | #360-2 / #362 / #363 |
| sync target | presenceだけでなく内容・版・下流手順の陳腐化を検出するか | #360-1 / #362 |
| external assumption | session固定、scheduler、API、runtime transportを実測し、未実測ならclose保留にするか | #360-3 / #363 |
| safe default / fail-close | CLIの既定値と空結果が、通常手順で静かに証拠を失わせないか | #355 |
| evidence lineage | Issueと元PR/findingの関係を時刻だけで推定せずartifactで束縛したか | #357の除外補正 |

change plan と plan review は、次を受入条件へ写像する。

1. 既知OOSを残す場合は owner decision と処置先を必須にし、無ければmerge/closeをfail-closeする。
2. operational verification が必要な外部仮定は、実測完了まで元Issueをcloseしない。
3. safe default、空結果拒否、capability preflight、content/contract lintを運用注意ではなく機械統制として比較する。
4. 高リスク plan review は変更行だけでなく、影響matrix上の既存記述と下流分岐の陳腐化を反証する。
5. artifactは各findingについて `detected_phase`、`disposition`、`owner_decision_ref`、`verification_phase`、`source_pr` を保持する。

## 7. Wave 5 の再計測契約（未完了）

導入後比較は、#371 の全対象経路が有効化され、低・中・高リスクの実dispatchが完了してから行う。対象は「#371有効化後に新パイプラインを通ってmergeされたPR」とし、旧経路のPRを混ぜない。

| 再計測項目 | 分子 | 分母 |
|---|---|---|
| 実装前設計finding率 | implementation開始前にinvestigation/planning/plan reviewで記録したdesign finding数 | 対象PR数、および全design finding数を併記 |
| 明示判断なし残留率 | merge時点でowner decision refも処置済み証拠も無いfinding/OOS数 | merge前までに既知だったfinding/OOS総数 |
| C1混入率 | merge前に発見可能だったがartifactに無く、merge後に起票されたfinding数 | 対象PR数と、全派生finding数を併記 |
| C3運用検証完了率 | planで要求されたoperational verificationの完了数 | 要求されたoperational verification総数 |
| PRあたり新規Issue | 観測窓内の新規Issue数 | 同期間にmergeされたPR数 |

- [ ] #371 導入後の対象PR集合と観測窓を固定した
- [ ] 低・中・高リスク経路を同一定義で再集計した
- [ ] 導入前の **0/8 C1、7/8 C2、1/8 C3、7/8 C4** と比較した
- [ ] 全体流量 **1.86 Issue/PR** と同じ定義で比較した
- [ ] 品質効果と追加dispatch・artifact・contextコストを対で #368 へ反映した

これらが未完了のため、Wave 0 のPRは Issue #370をcloseせず、`Closes #370` を付けない。
