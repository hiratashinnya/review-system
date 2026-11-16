"""オーナーが決めた処置方針・scope の覆しを台帳へ記録する（主文脈専用 verb ``decide``）。

どのロールの許可集合にも入れない。レビューアが書いたレポートを経由しない記録経路。
"""

from . import model, paths
from .errors import KarteUsageError
from .vocabulary import DIAGNOSIS_OWNERS

DISPOSITION_OPTIONS = ("disposition", "deferred_to", "waived_by", "waived_reason")


def record_decision(karte, finding_id, options, scope, override_ref=None, diagnosis_owner=None) -> list:
    """``karte`` の finding に決定を反映し、変更内容の説明行を返す（検証失敗は例外・何も書かない）。"""
    finding = karte.finding(finding_id)
    if finding is None:
        raise KarteUsageError(f"台帳に無い finding ID: {finding_id}")
    given = {key: value for key, value in options.items() if value}
    if not given and not scope and not override_ref and not diagnosis_owner:
        raise KarteUsageError("--disposition / --scope / --override-ref / --diagnosis-owner のいずれかは必要")
    lines = []
    if given:
        decided = model.parse_disposition(model.Block(None, finding_id, given, 0))
        if not decided.kind:
            raise KarteUsageError("付随キーだけでは決められない（--disposition を指定する）")
        previous = finding.disposition
        finding.disposition = decided.kind
        if decided.kind != "fix-here" or previous != "fix-here":
            finding.diagnosis_owner = "fixer"
        finding.deferred_to = decided.deferred_to
        finding.waived_by = decided.waived_by
        finding.waived_reason = decided.waived_reason
        lines.append(f"disposition: {decided.kind}")
    if diagnosis_owner:
        if diagnosis_owner not in DIAGNOSIS_OWNERS:
            raise KarteUsageError(f"--diagnosis-owner は {DIAGNOSIS_OWNERS} のいずれか")
        if finding.disposition != "fix-here" or not finding.is_open:
            raise KarteUsageError("--diagnosis-owner は未解消の fix-here finding にだけ指定できる")
        finding.diagnosis_owner = diagnosis_owner
        lines.append(f"diagnosis_owner: {diagnosis_owner}")
    if scope:
        if scope not in model.SCOPES:
            raise KarteUsageError(f"--scope は {list(model.SCOPES)} のいずれか: {scope!r}")
        finding.scope = scope
        lines.append(f"scope: {scope}（申告原本にオーナー印を記録し、台帳へ即時反映）")
    if override_ref:
        finding.override_ref = override_ref
        lines.append(f"override_ref: {override_ref}")
    return lines


def write_karte(path, karte) -> None:
    paths.write_text_atomic(path, model.dumps(karte))
