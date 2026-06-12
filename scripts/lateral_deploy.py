#!/usr/bin/env python3
"""
Lateral deployment tool: inventory .claude assets and convert to target platform formats.

Usage:
  python scripts/lateral_deploy.py --target copilot --dry-run
  python scripts/lateral_deploy.py --target copilot --create-pr
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from text. Returns (dict, body).

    Note: review_system/parsing/frontmatter.py exists but cannot be reused here
    because its KEY regex ([a-z_][a-z0-9_]*) does not support hyphenated keys
    such as 'disable-model-invocation' and 'user-invocable' used in SKILL.md files.
    This lenient parser handles the .claude asset format only.
    """
    lines = text.splitlines(keepends=True)

    if not lines or lines[0].strip() != "---":
        return {}, text

    # Find closing --- delimiter
    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        raise ValueError(
            "Frontmatter started with --- but closing --- not found. "
            "Check the file format (frontmatter must be delimited by --- on separate lines)."
        )

    fm_text = "".join(lines[1:closing_idx])
    body = "".join(lines[closing_idx + 1:])

    fm = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip().strip('"\'')

    return fm, body


def scan_assets(claude_dir: Path) -> dict:
    """Scan .claude directory and return asset inventory."""
    assets = {"skills": [], "agents": [], "standards": []}

    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    assets["skills"].append(skill_file)

    agents_dir = claude_dir
    for agent_file in sorted(agents_dir.glob("agents/*.md")):
        assets["agents"].append(agent_file)

    standards_dir = claude_dir / "standards"
    if standards_dir.exists():
        for std_dir in sorted(standards_dir.iterdir()):
            if std_dir.is_dir():
                std_file = std_dir / "SKILL.md"
                if std_file.exists():
                    assets["standards"].append(std_file)

    return assets


def should_skip_conversion(fm: dict) -> bool:
    """Check if asset should be skipped from prompt conversion."""
    if fm.get("user-invocable") == "false":
        return True
    return False


def convert_skill_to_prompt(skill_file: Path, fm: dict, body: str) -> tuple[str, str]:
    """Convert SKILL.md to GitHub Copilot .prompt.md format."""
    name = fm.get("name", skill_file.parent.name)
    description = fm.get("description", "")

    # Escape single quotes and remove newlines for YAML safety
    description_safe = description.replace("'", "''").replace("\n", " ")

    output_path = f".github/prompts/{name}.prompt.md"

    prompt_content = f"""---
mode: 'agent'
description: '{description_safe}'
---
{body}"""

    return output_path, prompt_content


def convert_agent_to_instructions(agent_file: Path, fm: dict, body: str) -> tuple[str, str]:
    """Convert agent .md to GitHub Copilot .instructions.md format."""
    name = fm.get("name", agent_file.stem)
    tools = fm.get("tools", "")
    model = fm.get("model", "inherit")

    output_path = f".github/instructions/{name}.instructions.md"

    # Format tools list as HTML comment
    tools_comment = f"<!-- tools: {tools} | model: {model} -->"

    instructions_content = f"""---
applyTo: '**'
---
{tools_comment}
{body}"""

    return output_path, instructions_content


def extract_spec_principles(principles_file: Path) -> str:
    """Extract PR1-PR10 from spec-principles/SKILL.md for copilot-instructions.md."""
    if not principles_file.exists():
        return ""

    content = principles_file.read_text(encoding='utf-8')
    _, body = parse_frontmatter(content)

    # Extract lines starting with PR# or bullet points (PR1–PR10 section)
    lines = []
    in_principles = False

    for line in body.splitlines():
        if "PR1" in line or "PR2" in line or "PR3" in line or in_principles:
            in_principles = True
            # Skip code-fence markers (```): a lone/odd fence would leak into
            # copilot-instructions.md as an unclosed code block and break the
            # following skill table. Principles are prose, so dropping fences
            # is safe.
            if line.strip().startswith("```"):
                continue
            lines.append(line)
        if in_principles and line.strip().startswith("---"):
            break

    return "\n".join(lines[:50])  # Limit to ~50 lines of principles


def generate_copilot_instructions(
    assets: dict, claude_dir: Path
) -> tuple[str, str]:
    """Generate copilot-instructions.md with principles and skill list."""
    principles_file = claude_dir / "skills" / "spec-principles" / "SKILL.md"
    principles_section = extract_spec_principles(principles_file)

    # Build skill list
    skill_list = []
    for skill_file in assets["skills"]:
        content = skill_file.read_text(encoding='utf-8')
        fm, _ = parse_frontmatter(content)

        if fm.get("user-invocable") != "false":
            name = fm.get("name", skill_file.parent.name)
            description = fm.get("description", "")
            # Escape | and strip newlines to keep the Markdown table valid
            description_cell = description.replace("|", "\\|").replace("\n", " ")
            skill_list.append(f"| `/{name}` | {description_cell} |")

    skills_table = "\n".join(skill_list)

    content = f"""# Repository Instructions for GitHub Copilot

This repository uses a structured spec-design methodology. Below are the core principles and available skills.

## Core Principles (spec-principles)

{principles_section}

## Available Skills

| Skill | Description |
|-------|-------------|
{skills_table}
"""

    return ".github/copilot-instructions.md", content


def write_outputs(outputs: list[tuple[str, str]], dry_run: bool = False):
    """Write converted files to disk or print to stdout."""
    # Check for duplicate output paths (silent overwrites indicate a problem)
    paths_seen = set()
    for path, _ in outputs:
        if path in paths_seen:
            print(f"✗ Error: duplicate output path: {path}")
            print(
                "This likely indicates duplicate asset names or a collision in naming. "
                "Check .claude/ for duplicate `name` attributes in frontmatter."
            )
            sys.exit(1)
        paths_seen.add(path)

        # Validate path stays within .github/ (prevent path traversal)
        resolved = Path(path).resolve()
        github_base = (Path.cwd() / ".github").resolve()
        try:
            resolved.relative_to(github_base)
        except ValueError:
            print(f"✗ Error: output path escapes .github/: {path}")
            print("All output paths must stay within .github/ (no .., no absolute paths).")
            sys.exit(1)

    if dry_run:
        print("=== DRY RUN: Files that would be generated ===\n")
        for path, content in outputs:
            print(f"FILE: {path}")
            print("-" * 60)
            print(content)
            print("-" * 60)
            print()
    else:
        for path, content in outputs:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            print(f"✓ Created {path}")


def create_pr(branch_name: str):
    """Create a git branch and PR using gh CLI."""
    # Check if gh is installed
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ gh CLI not found. Please install GitHub CLI or create PR manually.")
        print(f"Branch name: {branch_name}")
        return

    # Ensure we're on main branch before creating feature branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True
        )
        current_branch = result.stdout.strip()
        if current_branch != "main":
            print(f"✗ Error: must run from main branch (currently on {current_branch})")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("✗ Error: failed to determine current git branch")
        sys.exit(1)

    # Create and push branch
    try:
        # Check for changes before creating a branch to avoid leaving an empty branch
        subprocess.run(["git", "add", ".github/"], check=True)
        # returncode: 0=no diff, 1=diff exists, >1=command error
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"], capture_output=True
        )
        if result.returncode == 0:
            print("ℹ No changes to commit. .github/ is up to date.")
            return
        if result.returncode > 1:
            print(f"✗ git diff --staged failed (returncode={result.returncode})")
            sys.exit(1)

        # Only create the branch when there are changes to commit
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"✓ Created and checked out branch {branch_name}")

        subprocess.run(
            ["git", "commit", "--only", ".github/", "-m", "chore: add GitHub Copilot asset deployments"],
            check=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name], check=True
        )
        print(f"✓ Pushed to {branch_name}")

        # Create PR
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "chore: deploy .claude assets to GitHub Copilot",
                "--body",
                "Lateral deployment: converted .claude skills/agents to GitHub Copilot formats.\n\nAutomatic conversion via scripts/lateral_deploy.py",
                "--base",
                "main",
                "--head",
                branch_name,
            ],
            check=True,
        )
        print("✓ PR created")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy .claude assets to target platform"
    )
    parser.add_argument(
        "--target",
        choices=["copilot", "claude"],
        default="copilot",
        help="Target platform (copilot primary, claude future)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print converted files without writing",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create PR after writing files",
    )
    parser.add_argument(
        "--branch-name",
        default=None,
        help="Git branch name (default: asset-lateral-deploy/YYYYMMDD)",
    )

    args = parser.parse_args()

    if args.target != "copilot":
        print(f"Target '{args.target}' not yet implemented")
        # MVP: claude-to-claude conversion stub
        print("# MVP: --target claude conversion not yet implemented (PR8)")
        return

    # Determine branch name
    if not args.branch_name:
        today = datetime.now().strftime("%Y%m%d")
        args.branch_name = f"asset-lateral-deploy/{today}"

    # Find .claude directory and verify required subdirectories
    repo_root = Path.cwd()
    claude_dir = repo_root / ".claude"

    if not claude_dir.exists():
        print(f"Error: {claude_dir} not found")
        sys.exit(1)

    # Verify required subdirectories (per SKILL.md Phase 1 prerequisites)
    skills_dir = claude_dir / "skills"
    agents_dir = claude_dir / "agents"

    if not skills_dir.exists():
        print(f"Error: {skills_dir} not found (required prerequisite)")
        sys.exit(1)

    if not agents_dir.exists():
        print(f"Error: {agents_dir} not found (required prerequisite)")
        sys.exit(1)

    # Scan assets
    print(f"📦 Scanning {claude_dir}...")
    assets = scan_assets(claude_dir)
    print(f"  Found {len(assets['skills'])} skills")
    print(f"  Found {len(assets['agents'])} agents")
    print(f"  Found {len(assets['standards'])} standards (inventory only; conversion not yet implemented)")

    # Convert assets
    outputs = []

    print("\n🔄 Converting to GitHub Copilot format...")

    # Convert skills to prompts or instructions
    for skill_file in assets["skills"]:
        content = skill_file.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(content)

        if should_skip_conversion(fm):
            print(f"  ⊘ Skip {fm.get('name', skill_file.parent.name)} (user-invocable: false)")
            continue

        name = fm.get('name', skill_file.parent.name)

        # Orchestrators (disable-model-invocation: true) go to instructions
        if fm.get("disable-model-invocation") == "true":
            output_path = f".github/instructions/{name}.instructions.md"
            tools = fm.get("tools", "")
            model = fm.get("model", "inherit")
            tools_comment = f"<!-- tools: {tools} | model: {model} -->" if tools else ""
            instructions_content = f"""---
applyTo: '**'
---
{tools_comment}
{body}"""
            outputs.append((output_path, instructions_content))
            print(f"  ✓ {name} → {output_path} (orchestrator)")
        else:
            # Regular skills go to prompts
            output_path, prompt_content = convert_skill_to_prompt(skill_file, fm, body)
            outputs.append((output_path, prompt_content))
            print(f"  ✓ {name} → {output_path}")

    # Convert agents to instructions
    for agent_file in assets["agents"]:
        content = agent_file.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(content)

        output_path, instructions_content = convert_agent_to_instructions(
            agent_file, fm, body
        )
        outputs.append((output_path, instructions_content))
        print(f"  ✓ {fm.get('name', agent_file.stem)} → {output_path}")

    # Generate copilot-instructions.md
    ci_path, ci_content = generate_copilot_instructions(assets, claude_dir)
    outputs.append((ci_path, ci_content))
    print(f"  ✓ copilot-instructions.md with principles & skill list")

    # Write or preview
    print("\n📝 Writing files...")
    write_outputs(outputs, dry_run=args.dry_run)

    if args.dry_run:
        print("\n✓ Dry run complete. No files were written.")
    elif args.create_pr:
        print("\n🚀 Creating PR...")
        create_pr(args.branch_name)
    else:
        print("\n✓ Files written. Use --create-pr to open a PR.")


if __name__ == "__main__":
    main()
