"""Output-format instructions for the standalone triager, built from the per-phase evidence table."""
from finding_triager.assessment import FIELDS
from triage_policy.evidence import required_categories


def triager_instructions(phase: object) -> str:
    categories = ", ".join(required_categories(phase))
    return ("\nReturn only a JSON array. Each item has finding_id, harm, scope, "
            "evidence (nonempty " + categories + " strings), and facts "
            "(booleans for every key: " + ", ".join(sorted(FIELDS)) + ").\n")
