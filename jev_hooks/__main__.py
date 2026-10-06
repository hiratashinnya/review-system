"""stdin JSON / stdout JSON only; no settings, installation, or activation."""
import argparse
import json
import sys
from .config import load_config
from .configuration_failure import ConfigurationFault, configuration_failure, fault_decision
from .evaluator import make_evaluator
from .runner import run_event


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    event, config = {}, {}
    try:
        event = json.load(sys.stdin)
        config = load_config(args.config)
        result = run_event(event, config, make_evaluator(config))
    except ConfigurationFault:
        print("jev-hooks: missing_api_key", file=sys.stderr)
        result = fault_decision(event, config)
    except Exception:
        # Never leak input, exception payloads, or credentials to logs/stdout.
        result, fault = configuration_failure(event, config)
        print("jev-hooks: missing_api_key" if fault else
              "jev-hooks: input/config/storage failure; passed through", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
