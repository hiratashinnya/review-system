# オープンIssueへの影響確認（#371）

Codex（AI）、2026-10-16。GitHub fresh一覧でopen95件を取得し、#371/新role/CP/VDを参照する16件を確認した。Issue本文・native relation・Project値の書換えは行っていない。

| Issue | 接続・境界 |
|---|---|
| #551 | 既存コード構築原則とbaselineを維持。優先順位3〜7位の機構は追加しない。 |
| #547 | 診断チャネル本体は変更しない。新phaseの不一致はIssue-startのfail-close理由で返す。 |
| #543 | 本PRはharnessのST/IT/UTエビのみ。review_system側レベル導入は移さない。 |
| #537 | LEDGER-SPEC-371.mdの担当確認を引き渡す。enum追加は#371後、全体close待ちにしない。 |
| #525 | 新工程でもowner判断と起票実行を分離。承認済み改訂の起票経路は再実装しない。 |
| #524 | 新phase/run/artifact参照を利用可能にする。週次判断の器を重複新設しない。 |
| #523 | 1a/1b/2aのreviewも同じIssueのkarte連番対象。override_ref本体は再実装しない。 |
| #521 | 作成工程とfeedback loopの境界を維持し、新ledgerを追加しない。 |
| #513 | 未決owner/STOP/権限拒否は助言で解除できない。escalate機械強制本体は追加しない。 |
| #468 | Copilot薄wrapperは新工程参照を同期。Codex主文脈入口は退役のまま。専用agentは非移植。 |
| #409 | run/phase/dependency/expected outputを保持。owner手動merge・運用検証別Issueに接続し、AgentRunは作らない。 |
| #376 | phaseとartifactは導出表示可能。バックログ処分のowner判断は工程roleへ移さない。 |
| #375 | plan-reviewerの1a/1bとpr-reviewerの2aを対象へ追加。capture原本性方式は本PRで決めない。 |
| #370 | 欠陥分類と追加dispatchコストを対で観測する。実dispatchと導入後効果は未測定。 |
| #368 | 全体品質下限と本施策の中間目標を混同しない。観測窓/採否のowner決定とmerge後実測が必要。 |
| #310 | 旧planning対象外を前提にせず1a/1b/2a/2bの連番reviewを接続。karte配線本体は実装しない。 |

本施策の低リスク/中リスク/高リスク実dispatch、実使用モデル、追加費用、流出欠陥の観測は未完了。最小必須工程数は調査省略時8 dispatch、調査あり9 dispatchで、是正と相談は追加になる。これは工程数の構造的計算であり実測値ではない。比較窓・品質中間目標はowner判断前に捏造しない。merge後一回検証案を別文書へ用意した。
