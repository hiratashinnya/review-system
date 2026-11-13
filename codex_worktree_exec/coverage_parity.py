"""Full-test coverage parity on one commit/interpreter, without checkout bytecode."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SUITE = ["-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", "test_*.py"]


def failures(result) -> set[str]:
    return set(re.findall(r"^(?:FAIL|ERROR): ([^\n]+)",
                          result.stdout + result.stderr, re.MULTILINE))


def validate(plain, covered) -> None:
    a, b = failures(plain), failures(covered)
    if a != b or plain.returncode or covered.returncode:
        raise ValueError(f"coverage parity incomplete: plain exit={plain.returncode}, "
                         f"covered exit={covered.returncode}, missing={sorted(a-b)}, "
                         f"extra={sorted(b-a)}, matching_failures={sorted(a&b)}")


def _run(command, *, cwd, env):
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)


def execute(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = output.resolve()
    if output.is_relative_to(root):
        raise ValueError("parity output must be outside the worktree")
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "diff", "--exit-code", "HEAD", "--"],
                   check=True, capture_output=True)
    oid = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                         check=True, text=True, capture_output=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="issue655-parity-") as temp:
        plain_root = Path(temp) / "checkout"
        subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach",
                        "-q", str(plain_root), oid], check=True)
        try:
            normal_env = os.environ.copy()
            for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX",
                        "COVERAGE_FILE", "COVERAGE_OUTPUT_DIR"):
                normal_env.pop(key, None)
            plain = _run([sys.executable, *SUITE], cwd=plain_root, env=normal_env)
            (output / "plain.log").write_text(plain.stdout + plain.stderr)
            covered_env = dict(normal_env, PYTHONDONTWRITEBYTECODE="1",
                               COVERAGE_FILE=str(output / ".coverage"))
            uv = ["uv", "run", "--no-project", "--python", sys.executable, "--with", "coverage"]
            covered = _run([*uv, "coverage", "run", *SUITE], cwd=root, env=covered_env)
            (output / "covered.log").write_text(covered.stdout + covered.stderr)
            details = {"head_oid": oid, "interpreter": sys.executable,
                       "plain_exit": plain.returncode, "covered_exit": covered.returncode,
                       "plain_failures": sorted(failures(plain)),
                       "covered_failures": sorted(failures(covered))}
            (output / "parity.json").write_text(json.dumps(details, indent=2) + "\n")
            print(f"full parity head={oid} plain={plain.returncode} "
                  f"coverage={covered.returncode}; details={output / 'parity.json'}", flush=True)
            validate(plain, covered)
            subprocess.run([*uv, "coverage", "html", "-d", str(output / "htmlcov")],
                           cwd=root, env=covered_env, check=True)
            subprocess.run([*uv, "coverage", "report"], cwd=root, env=covered_env, check=True)
        finally:
            subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force",
                            str(plain_root)], capture_output=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    output = options.output or Path(tempfile.mkdtemp(prefix="review-system-coverage-"))
    execute(output)
    print(f"coverage HTML: {output.resolve() / 'htmlcov/index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
