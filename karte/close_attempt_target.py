"""close_attempt_target の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import int_args, model
from .errors import KarteUsageError

def resolve_close_attempt_number(args, karte) -> int:
    """未クローズ Attempt を解決する。"""
    if args.attempt is not None:
        return int_args.parse_int(args.attempt, "attempt")
    unclosed = [item.number for item in karte.attempts if not karte.results_for(item.number)]
    if len(unclosed) > 1:
        raise KarteUsageError(
            "--attempt が未指定で、未クローズの Attempt が複数ある（"
            + ", ".join(f"Attempt {number}" for number in unclosed)
            + "）。どの Attempt に記録するか --attempt で明示すること（Issue #378）"
        )
    if len(unclosed) == 1:
        return unclosed[0]
    if not karte.attempts:
        raise KarteUsageError(
            "--attempt が未指定で、カルテに Attempt が1件も無い。"
            "先に `append` すること（Issue #378）"
        )
    raise KarteUsageError(
        "--attempt が未指定で、全 Attempt が既にクローズ済み。"
        "--attempt を明示するか、先に `append` すること（Issue #378）"
    )


def validate_outcome(value: str) -> str:
    text = model.check_scalar(value, "outcome")
    if text not in model.OUTCOMES:
        raise KarteUsageError(f"outcome は {list(model.OUTCOMES)} のいずれか: {value!r}")
    return text
