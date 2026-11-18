# Issue #803「[#375 子4] pr-reviewer の権限分離を機械で強制する（PR コメント投稿経路・worktree 隔離・Write パス制限の hook 依存）」

- URL: https://github.com/hiratashinnya/review-system/issues/803
- 状態: open（2026-11-18取得）
- 本文: 8261文字/ 112行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #375, #697, #800, #792, #694, #270, #129, #479, #466, #340, #452, #542, #696, #337, #517, #409, #386, #722
- PR参照: #697, #479
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### (3) Write のパス制限が hook だけに依存する点 | ### (1) PR コメント投稿 | ### (2) worktree 隔離 | ### #694 項目 (10) との境界 | ## Scope | ### (1) PR コメント投稿経路 | ### (2) worktree 隔離 | ### (3) Write パス制限の hook 依存 | ## Out of scope | ## Acceptance criteria
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- 3. `pr-reviewer` の素の `Write` が、パス制限を **fail-open な PreToolUse hook だけ**に依存している点。#375 の AC「producer へ一般 Write を付与しない」が、hook の稼働を前提にしてしまう。
- - `E2`＝#375 冒頭「共通artifact envelopeとの接続」の追加 AC の2番目（producer への一般書込権限追加なし）。ただし hook 稼働前提の部分だけを本 Issue が受け持つ（設計部分は #800）。
- - 3点目（hook の fail-open）は #375 の AC として明示されていなかった論点で、PR #697 のレビュー（カルテ issue-375 の `F-375-26` として主文脈が記録する予定・本起票時点の `tmp/_karte/issue-375.md` は `F-375-23` までで未記載）に由来する。
- - #694 項目 (10) の記載：Claude Code は終了コード 2 以外の非0ではブロックしない（#270 本文の記述）ため、上記は **素通り（fail-open）** になる。逆に Python 3.11 未満では `-P` が不明オプションで終了コード 2 になり、全 Write/Edit が止まる（偽の python3 でだけ確認・本物の古い python3 では未実測）。
- - 隔離と Write 先は切り離して決められない：`.claude/agents/pr-reviewer.md` は handoff を**主チェックアウトの絶対パス**へ書かせるが、`.claude/rules/05-skills-agents.md` によれば、隔離されたエージェントは作業ツリー外への Write を機械的に拒否される（書き込み側は作業ツリールート相対のパスと、呼び出し側による回収が前提）。`pr-reviewer` に隔離を強制する
- #694（open）の項目 (10)「phase_tool_gate の fail-open と `-P` の下限」は、同じ hook の fail-open を全ロール共通の設計判断として扱い、「項目単位で別 Issue へ分割してよい」としている。**本 Issue は #694 (10) の汎用方針（全ロールへの影響・`-P` の下限）を決めない。** 本 Issue が扱うのは、その結果が `pr-reviewer` の Write パス制限という
-   - (P-c) 現状の「クォート済み `--body`」で短い要約だけ投稿し、finding 全文は handoff（ローカル）に置く。利点＝gate 不変。欠点＝GitHub 側に finding の詳細が残らない。
- - `pr-reviewer` に `isolation: "worktree"` を機械強制するか（確保コスト、worktree 解放 verb、handoff の受け渡し契約の変更を併せて決める）。強制しない場合に、`gh pr checkout` 禁止などの read-only 差分参照契約を機械強制で担保するか。`issue-fixer` が自力復旧できない現状を許容するか、主文脈の介入を前提とし続けるか。
-   - (I-a) 機械強制する。(I-b) 隔離せず read-only 差分参照（`gh pr diff`・`gitgate diff` など）だけに限定し、作業ツリーを動かす経路を機械的に塞ぐ。(I-c) 現状の規律依存を維持する。暫定の推奨は着手時の実測（上記の未確認事項）後に確定する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
