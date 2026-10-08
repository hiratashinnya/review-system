"""Explicit validation command wrapper emitting a machine-readable exit receipt."""
import json
import subprocess
import sys

PREFIX = "JEV_VERIFICATION_RECEIPT="


def main():
    command = sys.argv[1:]
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        return 2
    result = subprocess.run(command, check=False)
    print("\n" + PREFIX + json.dumps({"exit_code": result.returncode}), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
