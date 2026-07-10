"""asset_parity テスト用の合成 4 ツリー生成（tmp ディレクトリ・git 不使用）。

staleness の git-log 呼び出しはテストでは `commit_epoch_fn` 差し替えで隔離するため、
このフィクスチャは git init しない（アダプタ境界＝テスト境界・test-strategy 規約）。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_tree(test: unittest.TestCase) -> Path:
    """最小限の合成 4 ツリーを tmp ディレクトリに構築し root Path を返す（cleanup 登録済み）。

    含む asset：
      * ``plain-skill``（既定 skill モード）: github/agents_dir 双方に present（サイズ揃え済み）
      * ``orchestrator-skill``（``disable-model-invocation: true``）: github は
        skill 形でなく ``prompts/*.prompt.md`` にのみ present
      * ``principle-skill``（``user-invocable: false``）: github は構造的 N/A（inline 想定）・
        agents_dir には plain な SKILL.md として present
      * ``missing-everywhere-skill``: 正本のみ。exempt 登録なし → 両ツリーで MISSING
      * ``exempt-skill``: 正本のみだが github は exempt 登録あり（agents_dir は present）
      * ``plain-agent`` / ``exempt-agent`` / ``missing-agent``: 同様の agent 版
      * ``no-frontmatter``: フロントマター無し（棚卸し対象外・スキップされることを確認）
    """
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name)

    # --- 正本（.claude/） ---
    _w(root / ".claude/skills/plain-skill/SKILL.md",
       "---\nname: plain-skill\ndescription: A plain skill.\n---\n\nbody\n")
    _w(root / ".claude/skills/orchestrator-skill/SKILL.md",
       "---\nname: orchestrator-skill\ndescription: An orchestrator.\n"
       "disable-model-invocation: true\n---\n\nbody\n")
    _w(root / ".claude/skills/principle-skill/SKILL.md",
       "---\nname: principle-skill\ndescription: Always-loaded principle.\n"
       "user-invocable: false\n---\n\nbody\n")
    _w(root / ".claude/skills/missing-everywhere-skill/SKILL.md",
       "---\nname: missing-everywhere-skill\ndescription: Nowhere else.\n---\n\nbody\n")
    _w(root / ".claude/skills/exempt-skill/SKILL.md",
       "---\nname: exempt-skill\ndescription: Documented non-mirror.\n---\n\nbody\n")

    _w(root / ".claude/agents/plain-agent.md",
       "---\nname: plain-agent\ndescription: A plain agent.\n---\n\nbody\n")
    _w(root / ".claude/agents/exempt-agent.md",
       "---\nname: exempt-agent\ndescription: Documented non-mirror agent.\n---\n\nbody\n")
    _w(root / ".claude/agents/missing-agent.md",
       "---\nname: missing-agent\ndescription: Nowhere else.\n---\n\nbody\n")
    _w(root / ".claude/agents/no-frontmatter.md",
       "# Shared contract doc\n\nNot a real agent definition (no frontmatter).\n")

    # --- .github/ (Copilot) ---
    _w(root / ".github/skills/plain-skill/SKILL.md",
       "---\nname: plain-skill\ndescription: A plain skill.\n---\n\nbody\n")
    _w(root / ".github/prompts/orchestrator-skill.prompt.md",
       "---\nname: orchestrator-skill\ndescription: An orchestrator.\n---\n\nbody\n")
    # principle-skill: 意図的に .github 側に何も置かない（inline 想定・構造的 N/A）
    # missing-everywhere-skill / exempt-skill: 意図的に置かない
    _w(root / ".github/agents/plain-agent.agent.md",
       "---\nname: plain-agent\ndescription: A plain agent.\n---\n\nbody\n")
    # exempt-agent / missing-agent: 意図的に置かない

    # --- .codex/agents/ ---
    _w(root / ".codex/agents/plain-agent.toml",
       'name = "plain-agent"\ndescription = "A plain agent."\n')
    _w(root / ".codex/agents/exempt-agent.toml",
       'name = "exempt-agent"\ndescription = "Documented non-mirror agent."\n')
    # missing-agent: 意図的に置かない
    # 正本に無い extra（orphan-in-mirror 検出用・reverse-direction gap の例）
    _w(root / ".codex/agents/codex-only-agent.toml",
       'name = "codex-only-agent"\ndescription = "Exists only on the Codex side."\n')

    # --- .agents/skills/ (Codex CLI skill discovery) ---
    _w(root / ".agents/skills/plain-skill/SKILL.md",
       "---\nname: plain-skill\ndescription: A plain skill.\n---\n\nbody\n")
    _w(root / ".agents/skills/orchestrator-skill/SKILL.md",
       "---\nname: orchestrator-skill\ndescription: An orchestrator.\n---\n\nbody\n")
    _w(root / ".agents/skills/principle-skill/SKILL.md",
       "---\nname: principle-skill\ndescription: Always-loaded principle.\n---\n\nbody\n")
    _w(root / ".agents/skills/exempt-skill/SKILL.md",
       "---\nname: exempt-skill\ndescription: Documented non-mirror.\n---\n\nbody\n")
    # missing-everywhere-skill: 意図的に置かない

    return root
