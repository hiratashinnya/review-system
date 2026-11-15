# coverage HTML レポート生成

coverage・HTML・bytecode は checkout 外に生成する。coverage の導入・実行は
`uv run --no-project --with coverage` に限定し、uv 不在なら停止（pip へのフォールバック禁止）。

## 手順

1. Git HEAD と tracked worktree が一致する作業面で、一時出力先を決める。
   ```bash
   COVERAGE_OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/review-system-coverage.XXXXXXXX")" || exit 1
   export COVERAGE_OUTPUT_DIR
   ```
2. 同一コミット・interpreterによる **全** `unittest discover -s tests -t . -p "test_*.py"` を比較する。
   ```bash
   python3 -B -m codex_worktree_exec.coverage_parity --output "$COVERAGE_OUTPUT_DIR"
   ```
   この処理は通常 unittest を隔離した detached worktree で、coverage unittest を
   現作業面で実行する。通常側に `PYTHONDONTWRITEBYTECODE` や
   `PYTHONPYCACHEPREFIX` を設定しない。coverage 側は
   `PYTHONDONTWRITEBYTECODE=1`・`COVERAGE_FILE` を作業面外に指定し、
   同一interpreterを `uv run --no-project --python` で固定する。
   両実行の失敗test ID集合・終了コードを `parity.json` に記録する。
   一致してもどちらかが非0なら未完了。失敗時はHTML/reportを生成せず停止する。
3. 成功したら `$COVERAGE_OUTPUT_DIR/htmlcov/index.html` を表示・送付する。
   通常側の detached worktree は検査終了時に除去する。元checkoutはbytecodeを生成しない。

## done条件
- [ ] 同一commit・同一interpreterでの全テストID集合が一致し、**両方の終了コードが0**
- [ ] `$COVERAGE_OUTPUT_DIR/parity.json` および `htmlcov/index.html` が生成済み
- [ ] 元checkout内に新しい `.coverage`、`htmlcov/`、`__pycache__` が増えない
- [ ] 比較結果と作業面外レポートパスを報告済み

補足：parity runner自身のimportによるbytecodeも、起動時の `python3 -B` により防止する。
