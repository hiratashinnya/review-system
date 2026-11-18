# Issue #428「pr-merge-gate.sh（classifier.py）が gh を含まない無関係な read-only Bash コマンドまで誤って deny する（_split_shell_commands のリダイレクト一律拒否・#412 Out of scope の残課題）」

- URL: https://github.com/hiratashinnya/review-system/issues/428
- 状態: closed（2026-11-18取得）
- 本文: 4117文字/ 75行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #412, #413
- PR参照: #413
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## bug: 再現手順・期待結果・実際結果・環境・影響・root cause 仮説 | ## Dependencies / Related issues | ## Project fields（実行環境の制約により一部自動設定できず・要手動設定）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 再現手順：`.claude/hooks/pr-merge-gate.sh` が有効な環境で、`gh`/`git` を含まない、または含んでいても merge と無関係な read-only コマンドに `2>&1`・`2>/dev/null` 等のリダイレクトを付けて実行する。上記「現状と根拠」に実測コマンド例を記載。
- - root cause 仮説：上記「現状と根拠」参照。`_split_shell_commands()` がリダイレクト文字の存在のみで安全性を判定せず、構造全体を一律拒否している。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
