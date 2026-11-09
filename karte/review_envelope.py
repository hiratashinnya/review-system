"""pr-reviewer の handoff を共通 envelope（#371）の期待値へ束縛する（Issue #375）。

束縛キーは :data:`issue_envelope.handoff.BINDINGS`（工程 artifact の語彙）から ``input_refs`` を除いたもの。
``karte`` は単独で配置されても動く（標準ライブラリだけ）設計なので語彙はここへ写し、一致は
``tests/unit/test_issue_envelope_review.py`` が機械検査する（``issue_envelope.review_envelope`` は再公開）。
review 固有の 9 項目 finding は payload（handoff 本文）として別に維持し、ここでは扱わない。
期待値は呼出側（主文脈・trusted wrapper）が与え、handoff の自己申告から補わない。
"""
import re

SCHEMA = "review-handoff/v1"
SCHEMA_VERSION = 1
PRODUCER = "pr-reviewer"
ARTIFACT_TYPE = "ReviewReport"
PHASES = ("test_design", "implementation")
BOUND = ("producer", "phase", "issue", "run_id", "target_key", "input_digest", "snapshot_oid", "artifact_type")
DECLARED = ("schema", "schema_version", "status", "next_expected_artifact") + BOUND
_TEXT = ("run_id", "target_key")


def _fixed(data, errors):
    for key, want in (("schema", SCHEMA), ("schema_version", SCHEMA_VERSION),
                      ("producer", PRODUCER), ("artifact_type", ARTIFACT_TYPE)):
        if data[key] != want:
            errors.append(f"{key} が契約と不一致")
    if data["phase"] not in PHASES:
        errors.append(f"phase は {list(PHASES)} のいずれか")
    if data["status"] != "ready" or data["next_expected_artifact"]:
        errors.append("status は ready のみ・next_expected_artifact は空のみ（STOP/未完の review は取り込まない）")


def normalize(raw: dict) -> dict:
    """ヘッダの ``key=value``（文字列）を型付きの envelope へ。欠落・未知キー・書式違反は ValueError。"""
    data = {"next_expected_artifact": "", **raw}
    unknown, missing = set(data) - set(DECLARED), set(DECLARED) - set(data)
    if unknown or missing:
        raise ValueError(f"envelope のキー不正（欠落 {sorted(missing)}・未知 {sorted(unknown)}）")
    errors = []
    for key in ("issue", "schema_version"):
        text = data[key]
        if isinstance(text, bool) or not (isinstance(text, int) or re.fullmatch(r"[0-9]{1,9}", str(text))):
            errors.append(f"{key} は整数")
        else:
            data[key] = int(text)
    if not errors:
        _fixed(data, errors)
        if data["issue"] <= 0:
            errors.append("issue は正の整数")
    errors += [f"{key} が空" for key in _TEXT if not str(data[key]).strip()]
    if not re.fullmatch(r"[0-9a-f]{40}", str(data["snapshot_oid"])):
        errors.append("snapshot_oid は40桁のOIDが必要")
    if not re.fullmatch(r"[0-9a-f]{64}", str(data["input_digest"])):
        errors.append("input_digest はsha256が必要")
    if errors:
        raise ValueError("; ".join(errors))
    return data


def expected_of(*, issue, phase, run_id, target_key, input_digest, snapshot_oid) -> dict:
    """呼出側が持つ値から期待値を作る。書式は handoff と同じ規則で検査する。"""
    return {key: value for key, value in normalize({
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION, "status": "ready",
        "producer": PRODUCER, "artifact_type": ARTIFACT_TYPE, "phase": phase, "issue": issue,
        "run_id": run_id, "target_key": target_key, "input_digest": input_digest,
        "snapshot_oid": snapshot_oid,
    }).items() if key in BOUND}


def validate_review_envelope(declared: dict, expected: dict) -> dict:
    """handoff の申告を期待値へ完全に束縛する。stale・別 run・別 snapshot は ValueError。"""
    data = normalize(declared)
    missing = set(BOUND) - set(expected)
    if missing:
        raise ValueError(f"照合期待値が欠落: {sorted(missing)}")
    for key in BOUND:
        if data[key] != expected[key]:
            raise ValueError(f"artifact束縛不一致/stale: {key}")
    return data
