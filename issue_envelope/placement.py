"""包含上の役割からcanonicalな物理配置を決める。"""
from pathlib import Path
from .schema import CONTRACTS


def validate_placement(path, data, repo=None):
    target = Path(path)
    prefix = CONTRACTS[data["artifact_type"]][2]
    number = data["issue"]
    kind = data["artifact_type"]
    directories = {"ChangePlan": "change_plan", "VerificationDesign": "verification_design",
                   "InvestigationReport": "investigation_report", "TestDesign": "test_design"}
    if target.parent.name != directories[kind]:
        raise ValueError("artifact_typeと配置directoryが不一致")
    tree = kind in ("ChangePlan", "VerificationDesign")
    leaf = tree and data["parent"] and not data["children"]
    stem = f"{prefix}-{number}" if leaf else data["id"]
    if target.name != stem + ".toml":
        raise ValueError("包含役割とファイル名が不一致")
    if tree and not data["parent"] and data["id"] != f"{prefix}-{number}":
        raise ValueError("ルートidが不一致")
    if repo is not None and tree:
        relative = target.relative_to(Path(repo))
        if not data["parent"] or data["children"]:
            if len(relative.parts) != 2:
                raise ValueError("ルート/中間グループはrepo直下に置く")
        elif len(relative.parts) < 3:
            raise ValueError("葉は対象scope配下へ置く")
