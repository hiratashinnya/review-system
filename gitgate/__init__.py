"""gitgate — a thin, fixed-template wrapper around a small set of git verbs.

Issue #227 追加修正3（オーナー確定 2026-07-13）。

背景:
  agent-command-gate.sh の「gated 2ロールに生 git を許可し、サブコマンド以降の引数は自由」という
  設計が、`git push --receive-pack='sh -c "…"' <repo> HEAD`（外部プログラム実行）や
  `git log/diff --output=<path>`（任意ファイル書込）といった exec/write 面を開いていた（再レビュー
  Critical）。静的なフラグ検査では網羅性を保証できないことが 40 回超のバイパスで実証された。

方針:
  gated ロールからは生 git を一切禁止し、この `python3 -m gitgate <verb>` ラッパーだけを許可する。
  各 verb は固定テンプレートで git を呼び、**ユーザ制御のフラグが git に届かない**。想定外の引数は
  git に渡さず gitgate がエラー終了する（＝exec/write 面を構造的に閉じる）。

セキュリティ要件:
  - git 実行は argv を list で組み立て subprocess.run([...], shell=False)。**shell は使わない**。
  - 各 verb は厳格な引数スキーマを持つ。想定外の引数は build_git_argv が GitgateError を送出し、
    git を一切実行しない。
  - leaf 値（パス／ブランチ名／ref／整数／grep パターン）は検証する。改行・NUL を含む leaf は拒否。

依存仕様:
  - 設計ブリーフ: Issue #227 追加修正3（git ラッパー方式・オーナー確定）。
  - ゲート側の verb ロール別許可は `.claude/hooks/agent-command-gate.sh` /
    `.codex/hooks/agent-command-gate.sh` の GITGATE_VERBS_BY_ROLE が担う（gitgate は全 verb を実装し、
    ロール制限はゲートで機械強制する二段構え）。
"""

from .cli import GitgateError, build_git_argv, main

__all__ = ["GitgateError", "build_git_argv", "main"]
