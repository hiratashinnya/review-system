---
name: coverage-html
description: このプロジェクトで実装またはテストコードを CLI で変更した時だけ、unittest discover と coverage.py でカバレッジを確認する。生成物は commit しない。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

# coverage 確認（生成物は commit しない）

`coverage.py`＋`unittest discover` で `.coveragerc` の `[run] source` に定義された対象を計測する。
この skill は、Codex が CLI 経由で実装コードまたはテストコードを書いた時だけ使う。仕様・README・agent/skill だけの変更では
coverage を実行しない。

設定ファイル：`.coveragerc`（プロジェクトルート）。測定対象・除外・HTML 出力先は設定ファイルを正とし、CLI へ重複指定しない。

## 手順

1. **CLI 入出力仕様を文脈へ入れる**
   実装・テスト対象の CLI コマンド、入力引数、標準出力/標準エラー、終了コード、生成/更新ファイルの仕様を先に確認する。
   CLI 経由の仕様がある場合は、その入出力をテスト観点として coverage 結果と突き合わせる。

2. **coverage インストール確認**
   ```bash
   python3 -m coverage --version 2>/dev/null || pip install coverage
   ```

3. **テスト実行＋計測**
   ```bash
   python3 -m coverage run -m unittest discover -s tests -p "test_*.py"
   ```

4. **ターミナルサマリー表示**
   未実行行を効率よく見るため、missing line と 100% 到達済みファイルの省略を使う。
   ```bash
   python3 -m coverage report -m --skip-covered
   ```

5. **HTML レポート生成（必要時のみ）**
   ```bash
   python3 -m coverage html --skip-covered
   ```
   出力先：`htmlcov/index.html`（`.gitignore` 対象、commit 禁止）。GitHub Pages 公開分は `.github/workflows/pages.yml`
   が `main` 更新時に `_site/coverage/` へ組み立てて直接デプロイする。

6. **生成物を commit 対象から外す**
   `.coverage*`、`htmlcov/`、`_site/`、`doc-system-v2/meta.json`、`doc-system-v2/doc_view.html` は生成物なので
   `git add` しない。既に追跡されていれば `git rm --cached` で index から外す。

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] カバレッジサマリーをチャットに表示済み
- [ ] 実装/テスト変更に関係する CLI 入出力仕様を確認済み
- [ ] 生成物を commit 対象に含めていない
