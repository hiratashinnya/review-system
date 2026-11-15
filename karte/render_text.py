from __future__ import annotations

from . import model
from .render_attempt_lines import render_attempt_lines
from .render_finding_lines import render_finding_lines
from .render_saturation_lines import render_saturation_lines


def render_lines(issue, path, round_no, karte: model.Karte) -> list[str]:
    """カルテの現在状態を本文の行に整形する。"""
    lines = [f"=== Karte: issue-{issue}" + (f" / round {round_no}" if round_no else "") + " ==="]
    lines.append(
        f"これは Issue #{issue} の是正ループの診断カルテ（{path}）から機械生成した現在状態である。"
    )
    lines.append(
        "同じ失敗を繰り返さないために、以下の Prior attempts と同じ診断・同じ変更箇所を"
        "もう一度なぞらないこと。新しい試行は着手前に "
        f"`python3 -m karte append --issue {issue} --finding-ids <ID...> --root-cause <slug> "
        "--change-kind <kind> --targets <file::symbol...>` で宣言し、修正後に "
        f"`python3 -m karte close-attempt --issue {issue} --outcome <fixed|partial|no-change|regressed>` "
        "で実測差分を記録すること（記録しないと `check` が通らず停止できない）。"
    )
    lines.append("")
    lines.extend(render_attempt_lines(karte))
    lines.append("")
    lines.extend(render_finding_lines(karte))
    lines.extend(render_saturation_lines(karte))
    return lines
