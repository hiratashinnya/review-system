"""Use the same tool input projection in every R4 semantic evidence copy."""
from .outbound_inputs import project_input
from .redaction import redact


def project_tool(record, secrets):
    if not isinstance(record, dict):
        return {}
    selected = {key: redact(value, secrets) for key, value in record.items()
                if key in {"name", "tool", "semantic", "requires"}}
    if "input" in record:
        selected["input"] = project_input(record["input"], secrets, record.get("name", record.get("tool", "")))
    return selected


def project_context(context, secrets):
    if not isinstance(context, dict):
        return {}
    selected = {key: redact(value, secrets) for key, value in context.items()
                if key in {"id", "applicability", "role"}}
    for key in ("current_tool", "selector"):
        if key in context:
            selected[key] = project_tool(context[key], secrets)
    if isinstance(context.get("protected_operations"), list):
        selected["protected_operations"] = [project_tool(record, secrets) for record in context["protected_operations"]]
    return selected
