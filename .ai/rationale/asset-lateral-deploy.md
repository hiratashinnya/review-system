# asset-lateral-deploy — 設計経緯・却下案（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/asset-lateral-deploy/SKILL.md` であり、本文は skill の設計理由と変更履歴だけを保管する。

## 一括変換を廃止した理由

2026-06-15 の方針改定で、スクリプトによる一括変換を廃止し、エージェントが資産を1つずつ種別・起動方式に応じて手書き変換する方式へ移行した。旧スクリプト方式は全サブエージェントを `.instructions.md` に量産し、Copilot の instructions が自動適用される常時コンテキストであるという意味を取り違えていた。その結果、agent／prompt／skill／instructions の境界が崩れ、不要な常駐コンテキストを増やすためである。

旧スクリプト `scripts/lateral_deploy.py` とそのテストはこの方針改定で削除済みである。現在の手順に残すのは、資産の種別を判定し、対象 PF の仕様へ合わせて手作業で変換し、検算するという行動契約だけとする。

## 参照仕様

変換表の判断根拠は次の公式仕様で確認した（リンクは背景資料であり、skill の常駐契約ではない）。改定時は再確認する。

**GitHub Copilot**

- Custom agents（`.github/agents/*.agent.md`）: https://code.visualstudio.com/docs/agent-customization/custom-agents ／ https://docs.github.com/en/copilot/reference/custom-agents-configuration
- Prompt files（`.github/prompts/*.prompt.md`）: https://code.visualstudio.com/docs/agent-customization/prompt-files
- Custom instructions（`.github/instructions/*.instructions.md` ・ `copilot-instructions.md`）: https://code.visualstudio.com/docs/agent-customization/custom-instructions
- Agent Skills（`.github/skills/<name>/SKILL.md`）: https://code.visualstudio.com/docs/agent-customization/agent-skills ／ https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/

**Claude Code**

- Skills（`.claude/skills/<name>/SKILL.md`）: https://code.claude.com/docs/en/skills
- Subagents（`.claude/agents/<name>.md`）: https://code.claude.com/docs/en/sub-agents
