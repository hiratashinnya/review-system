"""Read the Issue #812 Markdown contract and evaluate the genuine gate without executing gh."""
import ast
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".claude/agents/gh-create-issue.md"
GATE = ROOT / ".claude/hooks/agent-command-gate.sh"


def section(text, name):
    start = f"<!-- gh-create-issue-gate-{name}:start -->"
    end = f"<!-- gh-create-issue-gate-{name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise AssertionError(f"gate contract must have one {name} section")
    return text.split(start, 1)[1].split(end, 1)[0]


def table_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if parts[0] not in {"subcommand", "判定", "---"} and not parts[0].startswith("---"):
            rows.append(parts)
    return rows


def embedded_gate_ast():
    shell = GATE.read_text(encoding="utf-8")
    script = shell.split("<<'PYEOF'\n", 1)[1].split("\nPYEOF", 1)[0]
    return ast.parse(script)


def gate_decision(command):
    result = subprocess.run(
        [str(GATE)],
        input=json.dumps({"agent_type": "gh-create-issue",
                          "tool_input": {"command": command}}),
        text=True, capture_output=True, cwd=ROOT, check=True,
        env={**os.environ, "AGENT_COMMAND_GATE_TRACE_LOG": "",
             "GH_REPO": "", "GH_HOST": ""},
    )
    if result.stderr.strip():
        raise AssertionError(f"gate wrote to stderr: {result.stderr}")
    if not result.stdout.strip():
        return "allow"
    payload = json.loads(result.stdout)
    if payload["hookSpecificOutput"]["permissionDecision"] != "deny":
        raise AssertionError(f"unexpected gate response: {result.stdout}")
    return "deny"
