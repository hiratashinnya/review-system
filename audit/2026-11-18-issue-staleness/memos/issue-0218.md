# Issue #218「fix(hooks): agent-command-gate のサブシェル括弧パイプ＋sort/head/tail/uniq パススルー未対応バイパスを是正」

- URL: https://github.com/hiratashinnya/review-system/issues/218
- 状態: closed（2026-11-18取得）
- 本文: 2572文字/ 44行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #216, #215
- PR参照: #216
- 主見出し: ## 発見経緯 | ## 実地確認済みPoC（2026-07-12・現在の main `b7c9b70` で再現） | # .claude/hooks/agent-command-gate.sh を issue-implementer ロールで実行、いずれも deny されるべきだが allow（空stdout）になる | ## ギャップ1: サブシェル括弧グルーピングが `PIPE_ONLY_RE` に未対応 | ## ギャップ2: `cat`/`tee` 以外の単一行保存フィルタが `PASSTHROUGH_COMMANDS` 未収録 | ## 受け入れ基準 | ## スコープ外（明記）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 実地確認済みPoC（2026-07-12・現在の main `b7c9b70` で再現）
- **設計上の注意**：`grep`・`tr` は無条件の恒等変換にならない（`grep` はパターン一致が前提、`tr` は文字変換が前提）ため、`cat`/`tee` と同列の「常に恒等」パススルーとして単純追加するのは不正確。`sort`/`head`/`tail`/`uniq` も、複数行入力や特定フラグ（`sort -r`、`head -n0` 等）では恒等にならない。**「単一行 literal producer の出力に対して、かつ恒等変換にな

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
