# coverage HTML レポート生成

`coverage` ライブラリ＋`unittest discover` で `review_system` パッケージのカバレッジを計測し、`htmlcov/index.html` を生成する。

設定ファイル：`.coveragerc`（プロジェクトルート）。計測対象は `review_system/` のみ。

> **coverage 未導入時の扱い**：`coverage` が入っておらず下記コマンドがエラーになった場合、
> **pip 等で自動導入してはならない**。**その場で停止し、coverage 未導入である旨をオーナーに
> 打ち上げる**（導入可否・導入方法はオーナー判断）。PF固有の実行制約は各PF wrapperに置く。

## 手順

1. **テスト実行＋計測**
   ```bash
   python3 -m coverage run -m unittest discover -s tests -p "test_*.py"
   ```

2. **HTML レポート生成**
   ```bash
   python3 -m coverage html
   ```
   出力先：`htmlcov/index.html`（`.gitignore` 対象のため未追跡）

3. **ターミナルサマリー表示**
   ```bash
   python3 -m coverage report
   ```

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] `htmlcov/index.html` が生成されている
- [ ] カバレッジサマリーをチャットに表示済み
