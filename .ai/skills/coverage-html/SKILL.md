# coverage HTML レポート生成

`coverage` ライブラリ＋`unittest discover` で `review_system` パッケージのカバレッジを計測し、`htmlcov/index.html` を生成する。

設定ファイル：`.coveragerc`（プロジェクトルート）。計測対象は `review_system/` のみ。

> **coverage の実行経路は `uv run --with coverage` に限定する**：`coverage` はグローバル環境にも
> venv にも事前インストールせず、`uv run --with coverage <command>` の使い捨て環境経由でのみ実行する。
> **pip 等での事前導入・グローバルインストールは禁止**（環境を汚さず、導入可否を判断する余地自体を
> 無くすため）。`uv` 自体が使えない（未インストール・ネットワーク到達不可等）場合は、代替として
> pip 等で自動導入せず、その場で停止して uv 未導入である旨をオーナーに打ち上げる（導入可否・
> 導入方法はオーナー判断）。PF固有の実行制約は各PF wrapperに置く。

## 手順

1. **テスト実行＋計測**
   ```bash
   uv run --with coverage coverage run -m unittest discover -s tests -p "test_*.py"
   ```

2. **HTML レポート生成**
   ```bash
   uv run --with coverage coverage html
   ```
   出力先：`htmlcov/index.html`（`.gitignore` 対象のため未追跡）

3. **ターミナルサマリー表示**
   ```bash
   uv run --with coverage coverage report
   ```

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] `htmlcov/index.html` が生成されている
- [ ] カバレッジサマリーをチャットに表示済み
