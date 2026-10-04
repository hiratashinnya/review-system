"""stdin JSON / stdout JSON only; no settings, installation, or activation."""
import argparse
import json
import sys
from .config import load_config
from .evaluator import make_evaluator
from .runner import run_event


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    try:
        event = json.load(sys.stdin)
        config = load_config(args.config)
        result = run_event(event, config, make_evaluator(config))
    except Exception:
        # Never leak input, exception payloads, or credentials to logs/stdout.
        print("jev-hooks: input/config/storage failure; passed through", file=sys.stderr)
        result = {}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
