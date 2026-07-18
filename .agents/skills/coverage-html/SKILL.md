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

> **coverage 未導入時の扱い**：`coverage` が入っておらず下記コマンドがエラーになった場合、
> **pip 等で自動導入してはならない**（agent-command-gate の方針＝任意パッケージの実行・導入を
> 許さない・issue #227）。**その場で停止し、coverage 未導入である旨をオーナーに打ち上げる**
> （導入可否・導入方法はオーナー判断）。
>
> **gated 2ロール（`issue-implementer`/`pr-reviewer`）からは使えない**：本 skill の手順1
> `python3 -m coverage run …` は agent-command-gate の第2次修正（2026-07-15）で **deny**
> される（`coverage run` は任意 Python 実行経路のため。2ロールは `report`/`html`/`xml`/`json`
> のみ許可）。カバレッジ計測は **main context（ゲート対象外）専用**。gated ロールはテスト検証を
> `python3 -m unittest discover -s tests/unit` で行い、カバレッジ計測は main context に委ねる。

## 手順

1. **CLI 入出力仕様を文脈へ入れる**
   実装・テスト対象の CLI コマンド、入力引数、標準出力/標準エラー、終了コード、生成/更新ファイルの仕様を先に確認する。
   CLI 経由の仕様がある場合は、その入出力をテスト観点として coverage 結果と突き合わせる。

2. **テスト実行＋計測**
   ```bash
   python3 -m coverage run -m unittest discover -s tests -p "test_*.py"
   ```

3. **ターミナルサマリー表示**
   未実行行を効率よく見るため、missing line と 100% 到達済みファイルの省略を使う。
   ```bash
   python3 -m coverage report -m --skip-covered
   ```

4. **HTML レポート生成（必要時のみ）**
   ```bash
   python3 -m coverage html --skip-covered
   ```
   出力先：`htmlcov/index.html`（`.gitignore` 対象、commit 禁止）。GitHub Pages 公開分は `.github/workflows/pages.yml`
   が `main` 更新時に `_site/coverage/` へ組み立てて直接デプロイする。

5. **生成物を commit 対象から外す**
   `.coverage*`、`htmlcov/`、`_site/`、`doc-system-v2/meta.json`、`doc-system-v2/doc_view.html` は生成物なので
   `git add` しない。既に追跡されていれば `git rm --cached` で index から外す。

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] カバレッジサマリーをチャットに表示済み
- [ ] 実装/テスト変更に関係する CLI 入出力仕様を確認済み
- [ ] 生成物を commit 対象に含めていない
