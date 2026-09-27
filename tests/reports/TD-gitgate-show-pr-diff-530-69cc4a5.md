---
id: TD-gitgate-show-pr-diff-530
version: 1
condition: boundary
result: FAIL
log_ref: tests/logs/TD-gitgate-show-pr-diff-530-69cc4a5.txt
---
# 目的

Issue #530 のため追加する `show-pr-diff` が PR 番号だけを受け取り、固定の読み取り専用 `gh pr diff <N>` を実行し、3,000 行級の標準出力を欠落なく呼び出し元へ渡すことを確認する。

# 前提

- `tests/unit/test_gitgate.py`、`tests/unit/test_agent_command_gate.py`、`tests/unit/test_codex_agent_command_gate.py` を実行する。
- ゲート許可集合の差分は `pr-reviewer` に限り、push と merge の非対称権限を維持する。

# 手順

1. 正の PR 番号で組み立つ argv が `gh pr diff <N>` のみであることを確認する。
2. 欠落、0、非整数、余分な引数を拒否し、コマンド実行へ到達しないことを確認する。
3. 3,000 行を模した stdout を `show-pr-diff` がそのまま返し、実行引数が `shell=False` の固定 argv であることを確認する。
4. reviewer の新 verb は許可し、issue-implementer では拒否されること、既存の push/merge 判定が維持されることを Claude/Codex 両ゲートテストで確認する。
5. `python3 -m unittest tests.unit.test_gitgate tests.unit.test_agent_command_gate tests.unit.test_codex_agent_command_gate` と全体 `python3 -m unittest` を実行する。

# 期待結果

- 3,000 行すべてが順序どおり stdout に出て、末尾行が保持される。
- `show-pr-diff` に任意 flags、ファイル出力、shell 解釈の入力経路がない。
- git push は reviewer に拒否され、gh pr merge は reviewer に許可されたままである。

## 実測

- ヘッダ: TD v1 / 実装 commit `69cc4a5` / 2026-09-27 / prompt・content hash 対象外 / Linux。
- targeted: `python3 -m unittest tests.unit.test_gitgate tests.unit.test_agent_command_gate tests.unit.test_codex_agent_command_gate` — PASS、155 tests、355.518秒。
- 全体: `python3 -m unittest` — FAIL、2055 tests、334.832秒、7 failures・1 error・9 skipped。
- 根本原因: 既存 `gitgate/cli.py` に実装を加えたため baseline の exact fingerprint が変わり、396行の module-over-100-lines violation が1件追加された。
- 是正: `show-pr-diff` 実装を新規100行未満の `gitgate/show_pr_diff.py` に切り出し、`cli.py` を元の fingerprint に戻す。
- その他の失敗は Codex supervisor feature catalog、Codex rate-limit fallback、読み取り専用 `.codex/hooks/__pycache__`、bubblewrap の作業ディレクトリ chdir に関する環境依存で、本差分との関連を示す証拠はない。
