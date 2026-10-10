"""Fixed unittest execution with a content CAS before committing its tested tree."""

import os
import subprocess
import sys
import re
from .base_error import BaseIntegrationError, require
from .base_snapshot import snapshot


def run_tests(workspace, modules, before):
    args = list(modules) if modules else ["discover", "-s", "tests/unit"]
    command = [sys.executable, "-m", "unittest", *args]
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(command, cwd=workspace, capture_output=True,
                                   text=True, timeout=900, check=False,
                                   env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BaseIntegrationError("BASE_TEST_UNAVAILABLE") from exc
    require(snapshot(workspace) == before, "BASE_TEST_CONTENT_CAS_MISMATCH")
    ran = re.search(r"Ran ([1-9][0-9]*) tests?", completed.stderr)
    passed = completed.returncode == 0 and ran is not None
    return {"command": " ".join(command), "result": "pass" if passed else "fail",
            "summary": (completed.stdout + completed.stderr)[-4000:],
            "exit_code": completed.returncode}
