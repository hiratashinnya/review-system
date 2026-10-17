"""dispatch前に全artifactの参照・木・DAGとcommitされた参照実体を検査する。"""
from pathlib import Path
from issue_envelope.check import check
from issue_envelope.query import index
from .committed_artifact import read_committed_artifact


def verify_repository_artifacts(root: Path) -> dict[Path, str]:
    errors = check(root)
    if errors:
        raise ValueError("repository artifact validation: " + "; ".join(errors))
    nodes = index(root)["nodes"]
    for node in nodes:
        read_committed_artifact(Path(node["yaml_path"]), root)
    return {Path(node["yaml_path"]).resolve(): node["id"] for node in nodes}
