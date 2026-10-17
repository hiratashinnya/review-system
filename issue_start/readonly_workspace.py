"""trusted主文脈がread-only Codex実行を既存linked作業面へ固定する入口。"""
import argparse
import json
import subprocess
from pathlib import Path
from codex_worktree_exec.arguments import parse_request
from codex_worktree_exec.cli import main as execute
from codex_worktree_exec.committed_artifact import read_committed_artifact
from codex_worktree_exec.worktree_binding import bind_worktree
from .gated_roles import READ_ONLY_ROLES
from .phase_dispatch import validate_phase_dispatch
from .readonly_phase_dispatch import parse_readonly_phase


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _input_path(root, relative):
    name = Path(relative)
    path = root / name
    if (name.is_absolute() or ".." in name.parts
            or any(part.is_symlink() for part in (path, *path.parents))
            or not path.resolve().is_relative_to(root.resolve())):
        raise ValueError("readonly input outside worktree")
    return path


def prepare_readonly_workspace(source, target, role, marker, prompt_file):
    """role自身には渡さない準備API。新規worktree作成・trust/profile変更はしない。"""
    source, target = Path(source).resolve(), Path(target).resolve()
    if role not in READ_ONLY_ROLES:
        raise ValueError("readonly role required")
    bind_worktree(target, target)
    if (Path(_git(source, "rev-parse", "--path-format=absolute", "--git-common-dir"))
            != Path(_git(target, "rev-parse", "--path-format=absolute", "--git-common-dir"))
            or _git(source, "rev-parse", "HEAD") != _git(target, "rev-parse", "HEAD")):
        raise ValueError("readonly workspace repository/HEAD mismatch")
    for root in (source, target):
        _git(root, "diff", "--exit-code", "HEAD", "--")
    parse_readonly_phase("Agent", dict(subagent_type=role, prompt=
                        "ISSUE_PHASE_INPUT_V1=" + json.dumps(marker)), role, source)
    binding = json.loads(_input_path(source, marker["binding_file"]).read_text())
    paths = [marker["binding_file"], marker["approval_file"], str(prompt_file)]
    if "input_file" in binding:
        paths.append(binding["input_file"])
    if "consultation" in binding:
        paths.extend(ref["path"] for ref in binding["consultation"]["input_refs"])
    for relative in paths:
        original, destination = _input_path(source, relative), _input_path(target, relative)
        content = original.read_bytes()
        if Path(relative).parts[0] != "tmp":
            if read_committed_artifact(destination, target) != content:
                raise ValueError("readonly committed input mismatch")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError("readonly tmp input already differs")
        destination.write_bytes(content)
    validate_phase_dispatch(marker, role, target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--approval-file", required=True)
    options, executor_args = parser.parse_known_args(argv)
    request = parse_request(executor_args)
    if request.binding_file is None:
        raise ValueError("readonly binding required")
    marker = dict(binding_file=str(request.binding_file), approval_file=options.approval_file)
    target = prepare_readonly_workspace(options.source, request.worktree, request.role,
                                        marker, request.prompt_file)
    return execute(executor_args, cwd=target)


if __name__ == "__main__":
    raise SystemExit(main())
