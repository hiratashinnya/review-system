---
name: coverage-html
description: このプロジェクトで unittest discover と coverage を使い、HTML カバレッジレポートを生成する。未導入なら coverage を入れ、tests/ 配下を実行し、htmlcov/index.html とモジュール別概要を出す。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

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
   出力先：`htmlcov/index.html`（`.gitignore` 対象のため未追跡）

4. **ターミナルサマリー表示**
   ```bash
   python3 -m coverage report
   ```

5. **ユーザーへファイル送信**
   `htmlcov/index.html` のパスと確認方法を報告する。

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] `htmlcov/index.html` が生成されている
- [ ] カバレッジサマリーをチャットに表示済み
- [ ] `htmlcov/index.html` のパスと確認方法を報告済み
