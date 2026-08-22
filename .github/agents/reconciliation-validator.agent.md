---
name: reconciliation-validator
description: 'Read-only structural validator for doc-system v2 nodes in tmp. Returns VALIDATION_OK with explicit self-fix instructions or ROLLBACK. Never writes files.'
model: claude-sonnet-5
tools:
  - read_file
  - grep_search
  - file_search
  - run_in_terminal
---

> **Copilot loader**：この custom agent は最初に [reconciliation-validator の共通契約](../../.ai/agents/reconciliation-validator.md) を読み込む。Copilot に read-only 検証器がない場合は書き込みへフォールバックせず STOP する。

## GitHub Copilot 固有の境界

- `run_in_terminal` は決定論的な検証・照会だけに使う。`create_file`、`replace_string_in_file`、リダイレクト等による書き込みは行わない。
- `VALIDATION_OK` / `ROLLBACK` の全項目をチャットの hand-off として返し、自己修正は確定値付きの指示に限定する。
- Copilot の agent loader は反映担当を自動起動しない。`VALIDATION_OK` は呼び出し元が reconciliation へ渡す。
