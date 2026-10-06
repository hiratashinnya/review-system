"""Ask individual relevance questions without certifying execution success."""
from .fingerprints import matches
from .configuration_failure import ConfigurationFault


def related(selector, event, definition, evidence, evaluator, observations, role, threshold=.9):
    if not selector.get("semantic") and matches(selector, event.get("tool_name"), event.get("tool_input", {})):
        return True
    if selector.get("tool") != event.get("tool_name") or evaluator is None:
        return False
    identifier = "r4_" + role + "_relevant"
    context = {"id": definition["id"], "selector": selector, "role": role,
               "current_tool": {"name": event.get("tool_name"), "input": event.get("tool_input", {})},
               "protected_operations": definition["operations"]}
    request = dict(evidence, skill_context=context)
    try:
        answer = evaluator.evaluate(request, [identifier]).get(identifier, {})
    except ConfigurationFault:
        raise
    except Exception:
        answer = {"value": None, "confidence": 0, "fault": "evaluation_error"}
    observations.append((identifier, answer))
    return answer.get("value") is True and not answer.get("fault") and answer.get("confidence", 0) >= threshold


def applicable(definition, evidence, evaluator, observations, threshold=.9):
    if not definition.get("applicability"):
        return True
    if evaluator is None:
        return False
    request = dict(evidence, skill_context={"id": definition["id"],
        "applicability": definition["applicability"], "role": "applicability"})
    try:
        answer = evaluator.evaluate(request, ["r4_skill_applies"]).get("r4_skill_applies", {})
    except ConfigurationFault:
        raise
    except Exception:
        answer = {"value": None, "confidence": 0, "fault": "evaluation_error"}
    observations.append(("r4_skill_applies", answer))
    return answer.get("value") is True and not answer.get("fault") and answer.get("confidence", 0) >= threshold
