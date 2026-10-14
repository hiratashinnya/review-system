"""一覧順によらず、許可された系統・層内の数値版最大を解決する。"""

import re


def model_version(model_id, selector):
    separator = re.escape(selector["separator"])
    suffix = "-" + re.escape(selector["suffix"]) if selector["suffix"] else ""
    pattern = (re.escape(selector["prefix"]) + "-" + str(selector["major"])
               + f"((?:{separator}[0-9]+)*)" + suffix)
    match = re.fullmatch(pattern, model_id)
    if not match:
        return None
    parts = tuple(int(part) for part in match[1].split(selector["separator"]) if part)
    while parts and parts[-1] == 0:
        parts = parts[:-1]
    return parts


def resolve_models(policy, platform, models):
    if not isinstance(models, list) or not models:
        raise ValueError("STOP: 利用可能モデル一覧が空または不正です")
    configuration = policy["platforms"][platform]
    resolved = {}
    for tier, family in configuration["tiers"].items():
        selector = configuration["families"][family]
        candidates = {}
        for model in models:
            if not isinstance(model, dict) or not isinstance(model.get("id"), str):
                raise ValueError("STOP: モデル一覧の id が不正です")
            version = model_version(model["id"], selector)
            if version is not None:
                candidates.setdefault(version, set()).add(model["id"])
        if not candidates:
            raise ValueError(f"STOP: {platform}/{tier} に合致するモデルがありません")
        latest = candidates[max(candidates)]
        if len(latest) != 1:
            raise ValueError(f"STOP: {platform}/{tier} の最新モデルが曖昧です")
        resolved[tier] = latest.pop()
    return resolved
