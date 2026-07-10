# asset_parity — cross-platform asset drift/presence detector

Detects presence/absence drift across the four asset trees that exist for this repo
(issue #155, detection half — a separate task handles the currently-known content
gaps such as issue-pipeline porting):

| Tree | Convention | Who reads it |
|---|---|---|
| `.claude/skills/<name>/SKILL.md` / `.claude/agents/<name>.md` | **canonical** | Claude Code |
| `.github/skills/<name>/SKILL.md` (or `.github/prompts/<name>.prompt.md` for `disable-model-invocation: true` orchestrator skills) / `.github/agents/<name>.agent.md` | mirror | GitHub Copilot |
| `.codex/agents/<name>.toml` | mirror (agents only) | Codex CLI (agent) |
| `.agents/skills/<name>/SKILL.md` | mirror (skills only) | Codex CLI (documented repo-scoped skill discovery path — top-level `.agents/`, not nested under `.codex/`) |

**Read-only reporting tool, not a content generator/synchronizer.** A prior
bulk-conversion script (`scripts/lateral_deploy.py`) was deliberately deleted (owner
decision, 2026-06-15 — see `.claude/skills/asset-lateral-deploy/SKILL.md`) because some
divergence between platforms is intentional (env-gated skills don't port everywhere;
wording legitimately differs where one platform has a mechanical hook and another
relies on prompt discipline). This tool only detects and reports; it never writes to
any of the four trees.

## Usage

```bash
python3 -m asset_parity check                        # text matrix, human-readable
python3 -m asset_parity check --format json           # machine-readable, for CI/tools
python3 -m asset_parity check --format both
python3 -m asset_parity check --root /path/to/repo
python3 -m asset_parity check --day-threshold 14 --size-ratio-threshold 1.5
python3 -m asset_parity check --fail-on-stale          # also treat staleness flags as drift
```

Exit codes: `0` no MISSING gaps (and no staleness flags if `--fail-on-stale`) /
`1` at least one MISSING gap (or, with `--fail-on-stale`, at least one staleness flag) /
`2` usage error (argparse default).

## What it reports

1. **Presence/absence matrix** (primary output) — for every canonical `.claude/`
   skill/agent, whether it's present in each of the three mirror trees, using each
   tree's actual naming convention (verified against real files, not assumed).
   Cell states: `OK` present / `MISSING` expected but absent / `exempt` documented or
   structural non-mirror / `n/a` that tree doesn't apply to this asset kind (e.g.
   Codex has no skill-shaped tree, `.agents/skills/` has no agent-shaped tree).
2. **Staleness flags** (secondary, heuristic) — for pairs present in both the
   canonical tree and a mirror: a large last-commit-date gap or line-count ratio is
   flagged as "worth a human/LLM look". This is **not** a semantic diff (that needs an
   LLM/human per the audit that motivated this tool) — false positives are fine, it's
   a flag, not a blocker. Never affects the exit code unless `--fail-on-stale` is set.
3. **Orphans in mirror** (informational) — assets that exist in a mirror tree with no
   canonical `.claude/` counterpart at all (the reverse-direction gap; not counted in
   the missing-count/exit code).

## Documented exceptions

`asset_parity/exceptions.py` holds a short, explicit list of **already-documented**
intentional non-mirrors (currently: `agy-delegate`, `issue-pipeline` +
`issue-implementer`/`pr-reviewer`, all Copilot-only exclusions — see
`.claude/tailoring-registry.md`). It intentionally does not invent new exceptions; if
you make a new deliberate non-mirror decision, record it in `tailoring-registry.md` (or
the asset's own `SKILL.md`/agent `.md`) first, then add the matching entry there.

Two *structural* (not per-asset) rules are handled by `asset_parity/trees.py` instead
of the exception list, because they're a deterministic consequence of a skill's own
frontmatter (per `.claude/skills/asset-lateral-deploy/SKILL.md`'s routing decision
tree), not a one-off documented carve-out:

- `disable-model-invocation: true` (orchestrator skill) → Copilot mirror is a
  **Prompt** (`.github/prompts/<name>.prompt.md`), not a Skill.
- `user-invocable: false` (always-loaded principle, e.g. `spec-principles`) → Copilot
  inlines it into `.github/copilot-instructions.md`; no discrete per-asset file is
  expected there at all, so the cell is reported as `exempt` with a structural reason
  string (kept distinct from `n/a`, which means "this tree doesn't apply to this asset
  kind at all", e.g. Codex agents vs. `.agents/skills`).

## Module map

| Module | Responsibility |
|---|---|
| `frontmatter.py` | Minimal scalar-only frontmatter reader (handles hyphenated keys like `disable-model-invocation` that this repo's existing mini-YAML parser, `review_system.parsing.frontmatter`, can't — see module docstring for why a second parser was written instead of extending the shared one) |
| `inventory.py` | Canonical asset enumeration + invocation-mode classification |
| `trees.py` | Per-tree naming conventions + applicability rules |
| `exceptions.py` | Documented intentional non-mirrors |
| `staleness.py` | Lightweight last-commit-gap / size-ratio heuristic (git boundary injectable for tests) |
| `report.py` | Builds the matrix + orphan list; renders text/JSON |
| `cli.py` | `python3 -m asset_parity check` |

## Design choices (and why)

- **Package, not a single script**: matches this repo's `dsv2/`/`docidx/` convention
  (dedicated stdlib-only package with `__main__.py`/`cli.py`), not `scripts/<name>.py`
  — this tool has enough distinct concerns (inventory, per-tree conventions,
  exceptions, staleness, reporting) to warrant separate modules and their own unit
  tests, same shape as the other two.
- **Text + JSON, one command**: text for a human running it locally, JSON for
  CI/other tooling to parse; `--format both` when you want both at once.
- **CI wiring intentionally left out of this PR** — the task brief called this a
  natural follow-up rather than something to force into this change (scope
  discipline). Wiring it into `.github/workflows/` would need a decision about
  which drift should actually fail a build vs. just annotate a PR; that's a
  separate call for the repo owner.
