"""モデル選択 policy の読込と契約検査。"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ".ai/model-policy.json"


def load_policy(root=ROOT):
    policy = json.loads((root / SOURCE).read_text(encoding="utf-8"))
    validate_policy(policy)
    return policy


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"platforms", "copilot_agents"}:
        raise ValueError("STOP: policy の構造が不正です")
    platforms = policy["platforms"]
    if not isinstance(platforms, dict) or set(platforms) != {"codex", "copilot"}:
        raise ValueError("STOP: codex/copilot の設定が必要です")
    for platform, configuration in policy["platforms"].items():
        if not isinstance(configuration, dict):
            raise ValueError("STOP: platform 設定は object が必要です")
        expected = {"tiers", "families", "budgets"} if platform == "codex" else {"tiers", "families"}
        if set(configuration) != expected:
            raise ValueError("STOP: platform 設定に未定義の項目があります")
        if not isinstance(configuration.get("tiers"), dict):
            raise ValueError("STOP: tiers は object が必要です")
        if not isinstance(configuration.get("families"), dict) or not configuration["families"]:
            raise ValueError("STOP: families は空でない object が必要です")
        required = {"low", "mid", "top"} if platform == "codex" else {"mid", "top"}
        if set(configuration["tiers"]) != required:
            raise ValueError(f"STOP: {platform} の層が不正です")
        for family in configuration["families"].values():
            if not isinstance(family, dict) or set(family) != {"prefix", "major", "suffix", "separator"}:
                raise ValueError("STOP: family の構造が不正です")
            if type(family["major"]) is not int or family["major"] < 1:
                raise ValueError("STOP: major は正の整数で指定してください")
            if (not isinstance(family["prefix"], str) or not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", family["prefix"])
                    or not isinstance(family["suffix"], str) or not re.fullmatch(r"[a-z]*", family["suffix"])
                    or family["separator"] not in (".", "-")):
                raise ValueError("STOP: family の形式が不正です")
        for family in configuration["tiers"].values():
            if not isinstance(family, str) or family not in configuration["families"]:
                raise ValueError("STOP: 層の family がありません")
    budgets = platforms["codex"].get("budgets")
    if not isinstance(budgets, dict) or set(budgets) != {"最小", "小", "中", "大", "最大"}:
        raise ValueError("STOP: Codex の全予算が必要です")
    if set(budgets.values()) != {"low", "medium", "high", "xhigh", "max"}:
        raise ValueError("STOP: Codex 予算は独立した5段階が必要です")
    agents = policy["copilot_agents"]
    if not isinstance(agents, dict) or not agents:
        raise ValueError("STOP: Copilot agent 分類が必要です")
    for name, tier in agents.items():
        if (not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name)
                or not isinstance(tier, str) or tier not in platforms["copilot"]["tiers"]):
            raise ValueError("STOP: Copilot agent 名または層が不正です")
