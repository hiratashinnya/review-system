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

verb 一覧:
  固定 git argv を組むだけの verb（`build_git_argv` の純 argv 経路）:
    status / add / commit / push / branch-current / fetch / diff / log
  policy 実行を伴う verb（`main()` で分岐・純 argv 経路には載せない）:
    new-branch       … fresh fetch + GitHub API 検証済みの exact OID で新規ブランチを作る（#317）
    adopt-branch     … 既存ブランチを期待 OID（任意で PR head）再検証つきで checkout する（#354・PR-2）
    worktree-release … linked worktree を冪等に解放（削除）する（#354・PR-2・FR-W5）
    collect-worktree … handoff を回収 → 検証 → 解放まで1操作で行う（#354・PR-2・FR-W2）
    worktree-forget  … 回収不能な stale エントリを abandoned へ逃がす（worktree は消さない・#354・PR-2）
    worktree-sweep-abandoned
                     … 異常終了（レートリミット等で SubagentStop が発火しなかった経路）で
                       running のまま残ったエントリを回収・解放する（#502・観測1）。
                       `--no-live-dispatch`（live な dispatch が無いことの観測申告）が
                       無ければ何もしない＝#423 の入れ子委譲中 running を誤解放しない。

  **verb を実装することと、あるロールがそれを実行できることは別**である。ロール別許可は
  ゲート側 allowlist（GITGATE_VERBS_BY_ROLE）が持ち、**未登録の verb は既定 deny**。
  Issue #354 PR-2 時点で worktree 系4 verb はどのロールにも未登録＝どの gated ロールからも
  実行できない（付与は PR-3/PR-4）。#502 で追加した worktree-sweep-abandoned も同じく
  どのロールにも付与しない（実行主体はレートリミット復帰フックと主文脈）。

依存仕様:
  - 設計ブリーフ: Issue #227 追加修正3（git ラッパー方式・オーナー確定）。
  - Issue #317（new-branch の分岐元束縛）・Issue #354 PR-2（worktree ライフサイクル verb）。
  - ゲート側の verb ロール別許可は `.claude/hooks/agent-command-gate.sh` /
    `.codex/hooks/agent-command-gate.sh` の GITGATE_VERBS_BY_ROLE が担う（gitgate は全 verb を実装し、
    ロール制限はゲートで機械強制する二段構え）。
"""

from .cli import GitgateError, build_git_argv, main
from .worktree import WorktreeError

__all__ = ["GitgateError", "WorktreeError", "build_git_argv", "main"]
