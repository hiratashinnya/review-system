"""Explicit opt-in live accuracy measurement; normal tests never use the API."""
import argparse
import json
from pathlib import Path
from .config import load_config
from .evaluator import make_evaluator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--corpus", default="examples/jev_hooks/semantic-corpus.jsonl")
    args = parser.parse_args()
    evaluator = make_evaluator(load_config(args.config))
    if evaluator.__class__.__name__ != "JevEvaluator":
        parser.error("semantic accuracy evaluation requires explicit evaluator=jev")
    rows = [json.loads(line) for line in Path(args.corpus).read_text().splitlines()]
    outcomes = []
    for row in rows:
        answer = evaluator.evaluate(row["evidence"], [row["question"]])[row["question"]]
        outcomes.append({"id": row["id"], "correct": answer["value"] is row["expected"],
                         "unknown": answer["value"] is None, "fault": bool(answer.get("fault"))})
    print(json.dumps({"model": evaluator.last_model, "results": outcomes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
