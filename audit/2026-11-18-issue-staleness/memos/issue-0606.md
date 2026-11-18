# Issue #606「agy-delegate を agy 直接実行ラッパーへ移行し、許可ルール検査と規範を整備する（#575 の子 S1）」

- URL: https://github.com/hiratashinnya/review-system/issues/606
- 状態: open（2026-11-18取得）
- 本文: 10170文字/ 235行。全文: `../raw/issues-2026-10.jsonl`
- AC: 25件（未チェック: 2）
- Issue参照: #680, #627, #628, #726, #676, #679, #575, #607, #513, #484, #605, #271, #284, #290, #273, #615
- PR参照: #680, #615
- 主見出し: ## 目的・背景 | ## 起票時の現状と根拠（履歴） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 仕様詳細（#605・PR #615 を踏まえた補足） | ### 1. 責務と正本 | ### 2. 実行前検査と起動契約 | ### 3. 結果の正規化と成功判定 | ### 4. 入力確認と成果の採用条件 | ### 5. 会話継続・並列・再試行
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- Codex（AI）による2026-11-03更新：PR #680→#627 の main 到達と #628 実機5UCの既存根拠に加え、#726 マージ後の Codex 専用 delegate の共有リファレンス読込と実行経路の live 検証を反映しました。Claude の共有リファレンス読込と受入範囲全体の最終独立レビューは未完了で、Issue は open を維持します。#676/#679 への切出しと owner waiver は維持し、それらを今
- 導入当時の stdout 不具合は agy 1.0.15 以降で修正済みで、現行 agy 1.2.1 は直接実行で正常に動作する（#575 本文の実測）。ブリッジ前提のまま作り直すと同じファイルを再度書き換えることになるため、本 Issue でラッパー前提の構成にする。ブリッジ自体の撤去は兄弟 Issue #607（S3）（オーナー実行）。
- ## 起票時の現状と根拠（履歴）
- - `origin/main` には `agy-delegate` の `.ai` 正本が無く、`.claude/agents/agy-delegate.md`・`.claude/skills/agy-delegate/SKILL.md`・`.codex/agents/agy-delegate.toml`・`.agents/skills/agy-delegate/SKILL.md` と `.ai/troubleshooting/agy-delegate.m
- - `silent-failure-diagnosis` の再実装（兄弟 Issue #605（S2）。本 Issue の前提）。
- - #284・#290 のクローズ判断（前提消滅に伴う処置はオーナー判断）。
- - Blocked by: #605（S2）（`silent-failure-diagnosis` の `.ai` 正本）
- - PR #615 が追加した「現在は利用者なし／#606 で接続予定」の現状説明を、接続完了に合わせて更新する。経緯として残す記録とは区別する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
