# Issue #540「harness 向け ADR 機構を道具ごとに構築する（feedback_ledger の造りを踏襲）」

- URL: https://github.com/hiratashinnya/review-system/issues/540
- 状態: closed（2026-11-18取得）
- 本文: 9982文字/ 161行。全文: `../raw/issues-2026-09.jsonl`
- AC: 14件（未チェック: 14）
- Issue参照: #452, #371, #537, #539, #522
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### ADR の構造は feedback_ledger の「造り」を写す | ### 置き場はコード共有・データは道具ごとに分離する（訂正済み） | ### クエリ/整合検査層は doc_system 同水準を目指すが、著作は軽いままにする | ### harness 側テストエビは test-strategy を手本にする（訂正済み） | ### トレーサビリティは`ref=`宣言駆動の共通アダプタで実現する（2026-09-24追記） | ## Scope | ### ADR スキーマ・機械検査 | ### 「決めたが実行を忘れる」対策（表現・通知・棚卸しの3層） | ### 置き場 | ## Out of scope
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- > 「現状と根拠」に新規節「トレーサビリティは`ref=`宣言駆動の共通アダプタで実現する」を追記し、Scope の「索引/整合検査」箇条を具体化（`dsv2.query`関数の共通アダプタ経由再利用・`ChangePlan`/`VerificationDesign`を索引対象に明示）、Acceptance criteria に1件追加、Dependencies に関連決定への参照を追記した。
- #371 の V字プロセス改訂（要件定義+アーキ設計／実装の各フェーズで ADR を残す設計）の前提部品として、harness（含有されない汎用ハーネス群）向けの ADR 機構を新設する。
- **索引対象に `ChangePlan`/`VerificationDesign` を明示的に含める**：当初は #371 の envelope を「`tmp/_handoff/` の一時ファイルで work unit 完了後に消える」前提で索引対象外としていたが、各ロールが worktree 内の永続パスへ直接 commit する設計（#371 本体）に変わったため、この除外前提が崩れた。ADR/feedback_ledger と同様に索引対象へ含める。
- - #371 本体の書き直し（本 Issue はその前提部品）。
- - Related: #371（V字プロセス改訂本体。本 Issue はその前提部品。各ロールが自分のADRをworktreeへ直接commit+pushする運用＝決定台帳`FBK-20260923-成果物ロールは各自pushし直接コミットする`は#371側の責務）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
