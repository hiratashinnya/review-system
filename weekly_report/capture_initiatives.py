"""Compare verified child membership in two initiative observations."""


def _parents(snapshot):
    inventory = snapshot.get("inventory") or {}
    parents = inventory.get("initiative_progress") or {}
    return {str(number): parent for number, parent in parents.items()}


def _children(parent):
    if not isinstance(parent.get("children"), list):
        return None
    children = {child["id"]: child for child in parent["children"]}
    return children if len(children) == parent.get("total") == len(parent["children"]) else None


def _difference(current, previous, reason):
    result = {"previous_total": previous.get("total"), "current_total": current.get("total"),
              "added": None, "removed": None, "delta": None, "reason": reason}
    if reason:
        return result
    before, after = _children(previous), _children(current)
    if before is None or after is None:
        return result | {"reason": "両時点の完全な子 Issue 一覧を確認できません"}
    return result | {"added": [after[key] for key in sorted(after.keys() - before.keys())],
                     "removed": [before[key] for key in sorted(before.keys() - after.keys())],
                     "delta": len(after) - len(before)}


def compare_initiatives(current, previous, reason):
    before, after = _parents(previous), _parents(current)
    return {key: _difference(after.get(key, {}), before.get(key, {}), reason)
            for key in sorted(before.keys() | after.keys())}
