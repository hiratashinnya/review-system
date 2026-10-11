# Codex 実行経路の現状

Issue #452 の Codex repo supervisor 方式は Issue #538 の PR-A で退役した。退役した実行契約・設計判断・却下案は
[`.ai/rationale/codex-supervisor-retirement-538.md`](../../.ai/rationale/codex-supervisor-retirement-538.md) へ移設した。
本書は現在の状態だけを記す。

## 結論

- **Codex は主文脈にしない。** 主文脈は Claude Code であり、Codex はサブ実行者として使う
  （オーナー決定・2026-09-22・Issue #538）。
- **repo supervisor は退役した。** `issue_start` の Codex 起動スタック、launch-intent gate、
  manifest の Codex 起動用 block は存在しない。
- **Codex の `spawn_agent` で `issue-implementer` / `issue-fixer` を起動する経路は無い。**
  issue-start gate が常時 `ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する。
- **`/issue-pipeline` の実装・是正を Codex に実行させる経路は、現時点では存在しない。**
  Issue #538 の PR-B で導入する予定であり、それまで実装・是正は Claude Code の
  `issue-implementer` / `issue-fixer` が行う。

## Codex `spawn_agent` の常時拒否

Codex の `spawn_agent` / `collaborationspawn_agent` で既知の `issue-implementer` / `issue-fixer` を
指定した dispatch は、issue-start gate が payload の詳細・cwd・ledger・GitHub API を読む前に
`ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する。malformed な payload でも理由は変わらない。
`issue_start/managed-entrypoints-v2.json` の `binding_transports` は `claude` だけを宣言し、
Codex の binding transport は置かない。

gate の判定順と Claude transport の marker／isolation 契約は
[`docs/tools/issue-start-and-branch-source.md`](../tools/issue-start-and-branch-source.md) を正とする。
Claude 経路の契約は supervisor の退役で変更していない。

## 変更していないもの

- `codex-review`（別モデルファミリによる第二意見レビュー）と `.codex/mcp/claude_review/`。
- `.codex/hooks.json` に残る2つの PreToolUse hook（`agent-command-gate.sh`・`issue-start-gate.sh`）。
- worktree 所有台帳（`issue_start/worktree_ledger.py`）と `durable_lock.py`。supervisor 専用ではない
  共有モジュールであり、Claude 経路の issue-start gate が引き続き使う。

## 今後の予定

Codex を実行者として呼ぶ経路（`codex exec -C <worktree>` の薄いラッパーとロール別 permission profile）は
Issue #538 の PR-B で導入する。設計の確定事項と未決事項は Issue #538 を正とし、導入時に本書へ現行契約として記載する。
Codex を主文脈とする前提で書かれた資産（`.codex/agents/issue-implementer.toml`・`issue-fixer.toml`、
`.agents/skills/issue-pipeline` 等）の整理は Issue #603 で扱う。

## 記録の所在

| 記録 | 置き場 |
|---|---|
| 退役した supervisor 方式の実行契約・設計判断 | `.ai/rationale/codex-supervisor-retirement-538.md` |
| 主文脈を Claude Code とする決定の経緯 | `audit/2026-09-21-pipeline-redesign/README.md` |
| Issue #452 のテスト設計・テスト結果 | `archive/issue-452-codex-supervisor/` |
| Issue #452 のテストログ | `tests/logs/TD-issue-start-452-*` |
