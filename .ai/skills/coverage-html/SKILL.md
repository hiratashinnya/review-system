# coverage HTML レポート生成

coverage・HTML・bytecode はsource検査に混入しないようcheckout外に生成する。
coverageインストールは `uv run --with coverage` に限定し、uv不在ならpipへフォールバックせず停止する。

## 手順

1. 作業面外の出力先とinterpreterを固定する。
   ```bash
   COVERAGE_OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/review-system-coverage.XXXXXXXX")" || exit 1
   export COVERAGE_OUTPUT_DIR
   export COVERAGE_FILE="$COVERAGE_OUTPUT_DIR/.coverage"
   export PYTHONDONTWRITEBYTECODE=1
   export COVERAGE_PYTHON="$(command -v python3)"
   ```
2. 同一interpreterで計測、HTML生成、表示する。
   ```bash
   uv run --no-project --python "$COVERAGE_PYTHON" --with coverage coverage run -m unittest discover -s tests -t . -p "test_*.py"
   uv run --no-project --python "$COVERAGE_PYTHON" --with coverage coverage html -d "$COVERAGE_OUTPUT_DIR/htmlcov"
   uv run --no-project --python "$COVERAGE_PYTHON" --with coverage coverage report
   ```
3. 同じcommit・interpreterで環境変数を解除し、`"$COVERAGE_PYTHON" -m unittest discover -s tests -t . -p "test_*.py"` の失敗test id集合と比較する。差がある場合は未完了として扱う。

## done条件
- [ ] coverageと通常unittestの失敗test id集合が一致
- [ ] `$COVERAGE_OUTPUT_DIR/htmlcov/index.html` が生成済み
- [ ] checkout内に `.coverage`、`htmlcov/`、新しい `__pycache__` が残らない
- [ ] サマリーと作業面外レポートパスを報告済み
