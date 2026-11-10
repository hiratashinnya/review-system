from __future__ import annotations

from . import model
from .saturation_groups import group_directive, saturated_groups


def render_saturation_lines(karte: model.Karte) -> list[str]:
    """飽和したアプローチを整形する。"""
    lines: list[str] = []
    groups = saturated_groups(karte)
    if groups:
        lines.append("")
        lines.append("## 飽和したアプローチ（同種の再試行は append が拒否される）")
        lines.append(
            "  以下と**同種**の Attempt（root_cause が同じで change_kind が同じか targets が"
            "重なるもの、あるいは実測 touched-set が一致するもの）を append すると "
            "EXIT_SATURATED で拒否され、カルテには書かれない。"
        )
        lines.append(
            "  ここに挙がっていないアプローチ（root_cause と targets を変えたもの）の append は"
            "拒否されない——この節は「次の append が必ず落ちる」という意味ではなく、"
            "「**このアプローチを繰り返す** append が落ちる」という意味である。"
        )
        for number, members, hits, candidate in groups:
            lines.append(
                f"  - Attempt {number} と同種（root_cause={candidate.root_cause} / "
                f"change_kind={candidate.change_kind} / "
                f"targets={', '.join(candidate.targets)}）: "
                f"衝突する既存 Attempt {', '.join(str(item) for item in members)}"
            )
            directive = group_directive(karte, number, hits, candidate)
            if directive:
                lines.append(directive)

    return lines
