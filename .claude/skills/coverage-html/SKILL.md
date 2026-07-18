---
name: coverage-html
description: Generate a coverage HTML report for this project using unittest discover. Runs all tests under tests/, writes htmlcov/index.html, and prints a per-module summary (does NOT auto-install coverage; if it is missing, stop and escalate to the owner). Use when you want to see which lines are covered or uncovered.
---

# coverage HTML レポート生成

`coverage` ライブラリ＋`unittest discover` で `review_system` パッケージのカバレッジを計測し、`htmlcov/index.html` を生成する。

設定ファイル：`.coveragerc`（プロジェクトルート）。計測対象は `review_system/` のみ。

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

4. **ユーザーへファイル送信**
   `SendUserFile` で `htmlcov/index.html` を送る。

## done 条件
- [ ] 全テストが PASS（失敗があれば原因をユーザーに報告してから続行）
- [ ] `htmlcov/index.html` が生成されている
- [ ] カバレッジサマリーをチャットに表示済み
- [ ] `htmlcov/index.html` を `SendUserFile` で送信済み
