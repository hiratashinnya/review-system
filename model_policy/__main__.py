"""python3 -m model_policy check|resolve|prepare-copilot。"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .agents import invalidate_agents, prepare_agents
from .catalog import codex_catalog, copilot_catalog
from .codex_auth import codex_auth_mode
from .checks import check
from .policy import ROOT, SOURCE, load_policy
from .resolver import resolve_models
from .tracked_runtime import check_tracked_runtime


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    preparing = "prepare-copilot" in arguments
    if preparing:
        try:
            invalidate_agents()
        except OSError as exc:
            print(f"model-policy: STOP: runtime を停止できません: {exc}")
            return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "resolve", "prepare-copilot"))
    parser.add_argument("--platform", choices=("codex", "copilot"), default="codex")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--surface", choices=("cli", "ide"))
    args = parser.parse_args(arguments)
    try:
        policy = load_policy()
        check_tracked_runtime(ROOT)
        errors = check(ROOT, policy)
        if errors:
            raise ValueError("STOP: " + "; ".join(errors))
        if args.command == "check":
            print("model-policy: check OK")
            return 0
        platform = "copilot" if args.command == "prepare-copilot" else args.platform
        if platform == "codex":
            auth_mode = codex_auth_mode()
            models = codex_catalog(auth_mode=auth_mode)
            source = {"source": "codex debug models", "surface": "cli", "auth_mode": auth_mode}
        else:
            if args.catalog is None or args.surface is None:
                raise ValueError("STOP: Copilot は --catalog と --surface が必須です")
            models, source = copilot_catalog(args.catalog, args.surface)
            source = {key: source[key] for key in ("source", "surface", "observed_at", "manual_reason")
                      if key in source}
        resolved = resolve_models(policy, platform, models)
        evidence = {"platform": platform, "observed_at": datetime.now(timezone.utc).isoformat(),
                    "policy_sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                    "catalog_sha256": hashlib.sha256(json.dumps(models, sort_keys=True).encode()).hexdigest(),
                    "selection": "numeric-version-max", "resolved": resolved, "catalog": source}
        if args.command == "prepare-copilot":
            evidence["agents"] = prepare_agents(policy, resolved)
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        if args.command == "prepare-copilot":
            try:
                invalidate_agents()
            except OSError as cleanup_error:
                print(f"model-policy: STOP: runtime を停止できません: {cleanup_error}")
        print(f"model-policy: STOP: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
