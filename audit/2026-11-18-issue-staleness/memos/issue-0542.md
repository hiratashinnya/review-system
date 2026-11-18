# Issue #542「マージ権限をAIロールから剥がし settings.json のネイティブ機構へ移す」

- URL: https://github.com/hiratashinnya/review-system/issues/542
- 状態: closed（2026-11-18取得）
- 本文: 6005文字/ 74行。全文: `../raw/issues-2026-09.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #584, #569, #581, #570, #533, #538, #468
- PR参照: #584
- 主見出し: # マージ権限をAIロールから剥がし、ネイティブ設定と共通 hook で拒否する | ## 目的 | ## Scope と実装結果 | ## Acceptance criteria の確認状況 | ## 検証と残る申し送り | ### 台帳の未解消 findings | ## 関連 Issue | ## 保証範囲と限界
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | F-542-10 | #569 | OPEN | 「基点由来」としていた8ケースのうち rate-limit watcher の2件は、#569（Codex レートリミット自動復帰機構の撤去）の対象機構に関するものです。8ケースとも、修正前 PR CI では発生していません。 |
- | F-542-11 | #581 | OPEN | staleness flags と mirror orphans の調査先です。asset parity 全体では flags 29、orphans 3です。 |
- | F-542-12 | #570 | OPEN | `/tmp` worktree の sandbox 前提は未検証です。 |
- - #533 は OPEN です。classifier の誤検知に関する Issue で、この変更では旧 classifier と配線を撤去しています。
- - #538 は OPEN です。Codex supervisor stack の撤去を扱う Issue です。
- - #468 は OPEN です。asset parity の staleness 調査を扱います。現在の29 flags のうち2件は #468 の対象、27件は #581 の対象です。
- - #581 は OPEN です。asset parity の staleness flags 27件と mirror orphans 3件を調査します。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
