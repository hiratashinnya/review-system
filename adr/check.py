"""参照・canonical・履歴不変性の read-only 検査。"""
import subprocess
import tomllib
from pathlib import Path
from dsv2.query import deps
from feedback_ledger.tomlwrite import dumps
from .index import index
from .schema import ADR_SPEC
from .store import load


def check(root, repo, *, base="origin/main", require_base=False, envelopes=()):
    records = load(root)
    meta = index(root, repo, envelopes)
    errors = []
    for data, path in records:
        if path.read_text(encoding="utf-8") != dumps(ADR_SPEC, data):
            errors.append(f"L7: canonical 不一致: {path}")
        for edge in deps(meta, data["id"]):
            if not edge["exists"]:
                errors.append(f"L3: 参照が存在しない: {edge['to']}")
        for asset in data["affected_assets"]:
            target = (Path(repo) / asset).resolve()
            if not target.is_relative_to(Path(repo).resolve()) or not target.exists():
                errors.append(f"L2: 資産が存在しない: {asset}")
    by_id = {data["id"]: data for data, _ in records}
    for identifier in by_id:
        seen, current = set(), identifier
        while current:
            if current in seen:
                errors.append(f"L3: supersedes が循環: {identifier}")
                break
            seen.add(current)
            current = by_id.get(current, {}).get("supersedes", "")
    errors.extend(immutability(root, repo, base, require_base))
    return errors


def immutability(root, repo, base, require_base):
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)
    resolved = git("merge-base", base, "HEAD")
    if resolved.returncode:
        message = "L6: base 未解決、immutability を検査できない"
        if require_base:
            return [message]
        import warnings
        warnings.warn(message, stacklevel=2)
        return []
    directory = Path(root).resolve()
    if not directory.is_relative_to(Path(repo).resolve()):
        return ["L6: ADR root は repo 配下であること"]
    prefix = directory.relative_to(Path(repo).resolve()).as_posix()
    revision = resolved.stdout.decode().strip()
    listed = git("ls-tree", "-r", "--name-only", "-z", revision, "--", prefix)
    if listed.returncode:
        return ["L6: base tree を読めない"]
    errors = []
    for name in listed.stdout.decode().split("\0"):
        if not name.endswith(".toml"):
            continue
        old = git("show", f"{revision}:{name}")
        path = Path(repo) / name
        if old.returncode or not path.exists():
            errors.append(f"L6: 既存ADRを削除できない: {name}")
            continue
        if old.stdout != path.read_bytes():
            before = tomllib.loads(old.stdout.decode())
            after = tomllib.loads(path.read_text())
            old_decision, new_decision = before.pop("decision"), after.pop("decision")
            tracking = {"tracking_status", "tracking_issue"}
            allowed = (before == after and old_decision["tracking_status"] == "pending"
                       and new_decision["tracking_status"] == "filed"
                       and new_decision["tracking_issue"] > 0
                       and {k: v for k, v in old_decision.items() if k not in tracking}
                       == {k: v for k, v in new_decision.items() if k not in tracking})
            if not allowed:
                errors.append(f"L6: 既存ADRの設計判断変更は禁止: {name}")
    return errors
