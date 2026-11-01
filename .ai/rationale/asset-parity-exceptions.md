# asset_parity 除外（exceptions.py）の経緯と個別根拠

この文書は、`asset_parity/exceptions.py` の module docstring から移した、除外エントリごとの詳細な根拠を保持する（経緯・判断の記録のため、区分1として削除せず移設）。
判定の正本は `.claude/tailoring-registry.md`、各エントリの理由文字列（`_ENV_DEPENDENT` ほか）は `exceptions.py` 側に残す。

## 除外エントリの詳細（移設元の docstring）

* `agy-delegate`（スキル＋エージェント）: agy 直接実行はローカル CLI／Windows Credential
  Manager 認証依存のため、クラウド/別プラットフォームへは非移植。
* `issue-implementer`／`issue-fixer`／`pr-reviewer`（エージェント）:
  gh CLI／Claude Code フック（`agent-command-gate.sh`）／Task 委譲／
  `bloom-model-tier` に依存する Issue 運用 dev-tooling メタパイプラインの
  サブエージェント群。**Codex CLI へは移植済み**（`.agents/skills/issue-pipeline/SKILL.md`・
  `.codex/agents/issue-implementer.toml`／`issue-fixer.toml`／`pr-reviewer.toml`）だが、
  **Copilot（`.github/`）へはエージェント非移植のまま**（gh CLI／Task 委譲／
  `bloom-model-tier` に Copilot 等価物なし）。`issue-fixer`（Issue #308 の是正専任ロール）はさらに
  `karte` CLI と PreToolUse フックの両方に依存するため、Copilot 側では契約が成立しない。
* `codex-review`（スキル）: `codex` CLI／ChatGPT ログイン／`~/.codex/sessions` に
  依存する Linux/WSL 専用の「Codex 公式 CLI への第二意見レビュー委譲」入口。
  **全外部ツリー非移植**（オーナー確定 2026-07-20・.claude/tailoring-registry.md）。
  Codex CLI を Codex 自身の skill ツリー（`.agents/`）から呼ぶのは再帰的で不自然、
  Copilot（`.github/`）にも等価物なし。SKILL の applicable tree は GITHUB と
  AGENTS_DIR のみ（CODEX は agent 専用＝自動 N/A）なので、その2ツリーを exempt する。
* `gh-create-issue`（スキル）: ユーザー指定が Codex と Claude Code の2環境に限定された
  明示スコープのため、その2環境だけに用意する。Copilot 版は作らず、将来 Copilot を
  対象化する時に形式・tool・対話境界を再評価する。

The first two assets' notes are scoped to the GitHub Copilot (`.github/`) tree
specifically — Codex CLI (`.codex/agents/`, `.agents/skills/`) carries real equivalents
for them (verified against the actual files). `codex-review` is exempt on *all* its
applicable trees. Either way exemptions are recorded per ``(name, kind, tree)``, never
as a blanket per-asset exemption.

## 関連

- 判定の正本：`.claude/tailoring-registry.md`
- 除外の追加手順：`asset_parity/exceptions.py` の docstring 末尾
