"""close_attempt_report の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import model, paths
from .saturation_groups import group_directive as _group_directive
from .saturation_groups import saturated_groups as _saturated_groups

def print_result(issue, number, result, attempt, measured):
    print(f"=== close-attempt: issue-{issue} Attempt {number} ===")
    print(f"  outcome: {result.outcome}")
    print(f"  実測 touched: {', '.join(result.touched) or '(差分なし・no-change)'}")

    target_files = {item.split("::", 1)[0] for item in attempt.targets}
    touched_files = {item.split("::", 1)[0] for item in measured}
    if measured and not (target_files & touched_files):
        print(
            "  注意: 宣言 targets（"
            + ", ".join(attempt.targets)
            + "）と実測 touched（"
            + ", ".join(measured)
            + "）が重ならない。誤った Attempt に記録した可能性がある"
            "（Issue #378 C）"
        )



def print_saturation(path, number):
    karte = model.parse(paths.read_text(path))
    for candidate_number, members, hits, candidate in _saturated_groups(karte):
        if number not in members:
            continue
        print("")
        print(
            f"  注意: Attempt {candidate_number} と同種のアプローチは飽和した"
            f"（衝突する既存 Attempt {', '.join(str(item) for item in members)}）。"
            "同種の append は拒否される"
        )
        print(_group_directive(karte, candidate_number, hits, candidate))
    print(f"  カルテ: {path}")
