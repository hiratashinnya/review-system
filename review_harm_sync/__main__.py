"""Render or check the generated Claude skill."""
import argparse
from pathlib import Path
from . import check, render

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('check', 'render'))
args = parser.parse_args()
root = Path.cwd()
if args.action == 'render':
    render(root)
else:
    problems = check(root)
    for problem in problems:
        print(f'out of date: {problem}')
    raise SystemExit(bool(problems))
