---
id: TD-gitgate-show-pr-diff-530
version: 1
condition: boundary
result: FAIL
log_ref: tests/logs/TD-gitgate-show-pr-diff-530-b76ecf2.txt
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

- ヘッダ: TD v1 / 実装 commit `b76ecf2` / 2026-09-27 08:15 UTC / prompt・content hash 対象外 / Linux。
- targeted: `python3 -m unittest tests.unit.test_gitgate tests.unit.test_agent_command_gate tests.unit.test_codex_agent_command_gate` — PASS、155 tests、268.934秒。
- 全体: `python3 -m unittest` — FAIL、2055 tests、382.510秒、6 failures・1 error・9 skipped。
- 全体 suite の残存失敗: `test_installed_codex_profile_normal_and_negative_matrix_is_model_free` は feature catalog に3項目が無いエラー、`test_real_outer_diagnosis_mount_denies_code_karte_and_git_writes` の sandbox code flag 不一致、rate-limit 2件は helper の `FALLBACK`、compile test は読み取り専用 `.codex/hooks/__pycache__`、bubblewrap 2件は一時 worktree chdir 失敗。Issue変更との因果を示す証拠はない。
- `python3 -m maintainability_lint check` — PASS、violations=0、accepted_debt=136。`gitgate/cli.py` は基準 fingerprint の既存379行に戻り、新規 module はいずれも100行未満。
- `python3 -m asset_parity check` — PASS、39 assets checked、0 missing、29 heuristic staleness flags。
- 補足 coverage 実測（main context 実行）: `uv run --with coverage coverage run -m unittest discover -s tests -p 'test_*.py'` — FAIL、2055 tests、325.679秒、6 failures・1 error・9 skipped。同じ環境依存の7失敗で、Issue変更との因果を示す証拠はない。
- coverage HTML — PASS、`htmlcov/index.html` を生成。
- coverage report — PASS、9523 statements / 1452 missed / 85%。
