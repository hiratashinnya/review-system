"""`GATED_ROLES` の正本（Issue #510・F-510-08）。

push/merge の非対称権限を課す3ロール（`issue-implementer`/`issue-fixer`/`pr-reviewer`）の集合は、
`issue_start/gate.py`（Task/Agent dispatch の呼び出し元判定・Issue #517）と
`.claude/hooks/agent-command-gate.sh`／`.codex/hooks/agent-command-gate.sh`
（Bash・実行系 MCP コマンドのロール別 allowlist）の両方が必要とする。以前はこの値が2ファイルに
リテラルで重複定義されており、片方だけロールを増減させても機械検査に掛からない片肺状態が
無言で生じ得た（F-510-08）。

**本モジュールが唯一の正本**であり、他は必ずここから読む：

- `issue_start/gate.py` は通常の Python import（`from .gated_roles import GATED_ROLES`）で読む。
- `.claude/hooks/agent-command-gate.sh` / `.codex/hooks/agent-command-gate.sh` は埋め込み Python
  スクリプトから `from issue_start.gated_roles import GATED_ROLES` で読む（cwd がリポジトリルート
  であることを前提にする。フック実行時の cwd は gated ロールに対し明示指定が deny されており、
  常にプロジェクトルートに固定される設計＝`.claude/rules/05-skills-agents.md` の ctx_* ツール付与方針
  「gated ロールは `cwd` の明示指定が deny」参照）。

依存を意図的に最小（標準ライブラリのみ・他の `issue_start` サブモジュールも `blocker_gate` 等の
重い依存も一切 import しない）にしてある。両フックは push/merge 境界の判定という最も頻繁に通る
経路でこの値を読むため、`blocker_gate`・`worktree_ledger` 等を巻き込む `issue_start.gate` を
そのまま import すると、無関係な依存の障害がロール別 allowlist 判定全体を巻き込んで壊しうる
（この軽量モジュールならその心配がない）。
"""

from __future__ import annotations

GATED_ROLES = frozenset({"issue-implementer", "issue-fixer", "pr-reviewer"})

__all__ = ["GATED_ROLES"]
