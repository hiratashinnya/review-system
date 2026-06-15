---
name: coverage-html
description: Generate a coverage HTML report for this project using unittest discover. Installs coverage if absent, runs all tests under tests/, writes htmlcov/index.html, and prints a per-module summary. Use when you want to see which lines are covered or uncovered.
---

# coverage HTML レポート生成

`coverage` ライブラリ＋`unittest discover` で `review_system` パッケージのカバレッジを計測し、`htmlcov/index.html` を生成する。

設定ファイル：`.coveragerc`（プロジェクトルート）。計測対象は `review_system/` のみ。

## 手順

1. **coverage インストール確認**
   ```bash
   python3 -m coverage --version 2>/dev/null || pip install coverage
   ```

2. **テスト実行＋計測**
   ```bash
   python3 -m coverage run -m unittest discover -s tests -p "test_*.py"
   ```

3. **HTML レポート生成**
   ```bash
   python3 -m coverage html
   ```
   出力先：`htmlcov/index.html`

4. **ターミナルサマリー表示**
   ```bash
   python3 -m coverage report
   ```

## done

- [ ] 全テストが PASS（失敗があれば原因を報告してから続行）
- [ ] `htmlcov/index.html` が生成されている
- [ ] カバレッジサマリーをチャットに表示済み
