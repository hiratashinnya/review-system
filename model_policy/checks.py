"""model-free 正本参照と停止状態 template を CI で検査する。"""

import re

from .frontmatter import stopped_frontmatter

REFERENCE = ".ai/model-policy.json"
REFERENCERS = (
    ".agents/skills/bloom-model-tier/SKILL.md",
    ".github/skills/bloom-model-tier/SKILL.md",
    ".ai/Individually-managed-lists.md",
)
PINNED_ID = re.compile(r"\b(?:gpt-\d+(?:\.\d+)*-[a-z]+|claude-(?:sonnet|opus)-\d+(?:-\d+)*)\b")


def check(root, policy):
    errors = []
    for relative in REFERENCERS:
        body = (root / relative).read_text(encoding="utf-8")
        if REFERENCE not in body or PINNED_ID.search(body):
            errors.append(f"{relative}: 正本参照欠落またはモデル ID 固定")
    agents = policy["copilot_agents"]
    paths = {path.stem.removesuffix(".agent"): path
             for path in (root / ".github/agents").glob("*.agent.md")
             if not path.name.startswith("runtime-")}
    if set(paths) != set(agents):
        errors.append("Copilot agent 一覧が policy と一致しません")
    for name, path in paths.items():
        body = path.read_text(encoding="utf-8")
        marker = f"<!-- model-policy: {REFERENCE}; agent: {name} -->"
        if marker not in body or PINNED_ID.search(body) or re.search(r"^model:", body, re.M):
            errors.append(f"{path.name}: model-free template が不正です")
        if not stopped_frontmatter(body):
            errors.append(f"{path.name}: 一意な停止 flags または単純 frontmatter がありません")
        if agents.get(name) not in policy["platforms"]["copilot"]["tiers"]:
            errors.append(f"{path.name}: 有効な層がありません")
    return errors
