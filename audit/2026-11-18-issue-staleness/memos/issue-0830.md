# Issue #830「improvement(review): reviewer の finding に実運用での到達経路・前提脅威の根拠欄を設け、取り込み後も保持する」

- URL: https://github.com/hiratashinnya/review-system/issues/830
- 状態: closed（2026-11-18取得）
- 本文: 3078文字/ 63行。全文: `../raw/issues-2026-11.jsonl`
- AC: 9件（未チェック: 0）
- Issue参照: #832, #784, #785, #816, #511, #783, #691, #723, #781, #375, #801, #810, #370
- PR参照: #816
- 主見出し: ## 目的・背景 | ### 利用者価値・提案挙動 | ### 互換性・代替案 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 対象 harness
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- レビューが収束しない一因に、論理上は正しいが実運用では起きない指摘や、エージェントのうっかりミス対策に悪意ある攻撃への耐性を求める指摘がある。指摘は減らさず、reviewer に「実運用での到達経路」「前提とする脅威」の根拠を書かせ、評価と棄却候補化は後続 Issue（β: triager 側＝#832）で行う。本 Issue は、根拠を書かせて後段へ失わずに渡す入力側だけを扱う。
- - reviewer は各 finding に「到達経路」「前提脅威」を書く。書けない場合も finding を省略せず「根拠なし」を明示する。harm は従来どおり review-harm で判定し、根拠の有無で変えない。
- - `.ai/skills/review-harm/SKILL.md`: harm は real|none。到達性・前提脅威の欄も基準も無い。
- - PR #816（draft・OPEN）は `karte/`・`pr-reviewer.md`・review-harm を変更していない（変更ファイル一覧で確認）。
- 1. 「到達経路」「前提脅威」の定義・最小記載要件・「根拠なし」の表記を1か所に定義し、reviewer と後続の triager が同じ定義を参照できるようにする（置き場は実装で決める。review-harm の harm 判定基準は変更しない）。
- - [x] 到達経路・前提脅威の定義・最小記載要件・「根拠なし」の表記が1か所に定義され、pr-reviewer 契約から参照されている。review-harm の harm 判定基準・「迷ったら real」・harm_detail 規約が差分で変更されていない。
- - [x] 代表ケース（理論上のみ／悪意前提のみ／うっかり経路で到達可能／根拠欠落）の finding がパース・保持される。実例は PR #816 等の既存レビュー記録から最低数件を fixture にする（評価は β）。
- - 親: #691（オーナー決定）。blocked-by: なし。後続: β（triager 側の評価）。
- - 連携: 新キーが triager に届くことが β の前提（#816 の binding は `asdict(ReviewFinding)` を使う）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
