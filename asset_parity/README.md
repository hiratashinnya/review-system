# asset_parity — cross-platform asset drift/presence detector

Detects presence/absence drift across the four loader-facing asset trees that exist for this repo
(issue #155, detection half — a separate task handles the currently-known content
gaps such as issue-pipeline porting):

| Tree | Convention | Who reads it |
|---|---|---|
| `.claude/skills/<name>/SKILL.md` / `.claude/agents/<name>.md` | **parity seed (loader wrapper)** | Claude Code |
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

1. **Presence/absence matrix** (primary output) — for every parity-seed `.claude/`
   skill/agent, whether it's present in each of the three mirror trees, using each
   tree's actual naming convention (verified against real files, not assumed).
   Cell states: `OK` present / `MISSING` expected but absent / `exempt` documented or
   structural non-mirror / `n/a` that tree doesn't apply to this asset kind (e.g.
   Codex has no skill-shaped tree, `.agents/skills/` has no agent-shaped tree).
2. **Staleness flags** (secondary, heuristic) — for pairs present in both the
   parity seed and a mirror: a large last-commit-date gap or line-count ratio is
   flagged as "worth a human/LLM look". This is **not** a semantic diff (that needs an
   LLM/human per the audit that motivated this tool) — false positives are fine, it's
   a flag, not a blocker. Never affects the exit code unless `--fail-on-stale` is set.
3. **Orphans in mirror** (informational) — assets that exist in a mirror tree with no
   `.claude/` parity-seed counterpart at all (the reverse-direction gap; not counted in
   the missing-count/exit code).

## Non-active shared material (Issue #407)

The parity inventory has an intentionally narrow seed boundary. It enumerates only
`.claude/skills/*/SKILL.md` and `.claude/agents/*.md` as loader-facing comparison
seeds; shared AI material is
not a fifth asset tree and must not create mirror obligations:

| Material | Shared source of truth | Inventory treatment |
|---|---|---|
| Normative skill/agent body | `.ai/skills/` / `.ai/agents/` | linked from a loader wrapper; not scanned as a second asset |
| ADR / rationale | `.ai/rationale/` | inactive record; ignored |
| Troubleshooting | `.ai/troubleshooting/` | inactive record; ignored |
| Shared schema | `.ai/schema/` | inactive contract; ignored |

The placement contract is `.ai/schema/asset-placement-v1.json`. Do not add a new
parity exception for one of these directories: if a record is reported as an
asset, the inventory boundary is wrong and should be fixed instead.

### Terminology migration compatibility

`parity seed` is the primary term and API from `asset-parity-report/v2`. Existing
consumers remain supported during migration: `scan_canonical()`,
`Asset.canonical_path`, `StaleSignal.canonical_epoch` / `canonical_lines`, and JSON
`canonical_path` / `canonical_lines` remain deprecated aliases for the corresponding
`parity_seed_*` names. New integrations should use the v2 names; the JSON payload
publishes both names and a `compatibility.deprecated_keys` map.

Legacy keyword calls are also accepted: `Asset(canonical_path=...)`,
`StaleSignal(canonical_epoch=..., canonical_lines=...)`, and
`compare(canonical_path=...)`. Passing a legacy and v2 name together is accepted only
when the values match; conflicting values raise `TypeError` rather than choosing one.

## Documented exceptions

`asset_parity/exceptions.py` holds a short, explicit list (`EXEMPTIONS`) of
**already-documented** intentional non-mirrors, each keyed by `(name, kind, tree)` with
a reason that cites `.claude/tailoring-registry.md`. This README deliberately does not
repeat the entries — `EXEMPTIONS` is the single source for the current set. It
intentionally does not invent new exceptions; if you make a new deliberate non-mirror
decision, record it in `tailoring-registry.md` (or the asset's own `SKILL.md`/agent
`.md`) first, then add the matching entry there.

Two *structural* (not per-asset) rules are handled by `asset_parity/trees.py` and
`asset_parity/inlining.py` instead of the exception list, because they follow from a
skill's own frontmatter (per `.claude/skills/asset-lateral-deploy/SKILL.md`'s routing
decision tree) rather than from a one-off documented carve-out. The first is decided by
frontmatter alone; the second also depends on the content of
`.github/copilot-instructions.md`:

- `disable-model-invocation: true` (orchestrator skill) → Copilot mirror is a
  **Prompt** (`.github/prompts/<name>.prompt.md`), not a Skill.
- `user-invocable: false` (always-loaded principle, e.g. `spec-principles`) → Copilot
  inlines it into `.github/copilot-instructions.md`; no discrete per-asset file is
  expected there at all, so the cell is reported as `exempt` with a structural reason
  string (kept distinct from `n/a`, which means "this tree doesn't apply to this asset
  kind at all", e.g. Codex agents vs. `.agents/skills`). The structural reason is used
  **only when the skill is actually inlined** (a complete `principles-source:` marker line
  in the *body* of `copilot-instructions.md`: comment end and 64-hex `sha256` field
  included; a truncated or malformed line does not count). The generated header (the lines
  before the first blank line) always carries the same marker for `spec-principles`
  whether or not the body inlines it, so the header is skipped and is no evidence.
  `asset-lateral-deploy` routes a
  `user-invocable: false` skill to Instructions and never to a skill/prompt, so one that is
  not inlined has **no accepted Copilot file at all** (`trees.expected_paths` via
  `inlining.principle_github_paths` expects only its inline slot, a
  `copilot_paths.InlineSlotPath` whose `is_file()` is always false, so nothing on disk can
  satisfy it):
  a plain `.github/skills/<name>/SKILL.md` or prompt does **not** make the cell `OK` (it is
  a misplacement), a documented exemption in `exceptions.py` reports its reason as
  `exempt`, and without one the cell is `MISSING`. The report does not name a stray file;
  remedy a `MISSING` there by removing the misplaced file or by recording a documented
  non-mirror in `exceptions.py`. Inlining is not a remedy for another skill:
  `guidance_sync` writes the `principles-source` marker for `spec-principles` alone
  (`guidance_sync/sync.py::PRINCIPLES_SOURCE`), so a new principle skill needs that tool
  extended first.

## Module map

| Module | Responsibility |
|---|---|
| `frontmatter.py` | Minimal scalar-only frontmatter reader (handles hyphenated keys like `disable-model-invocation` that this repo's existing mini-YAML parser, `review_system.parsing.frontmatter`, can't — see module docstring for why a second parser was written instead of extending the shared one) |
| `inventory.py` | Claude parity-seed enumeration + invocation-mode classification + loader-root boundary |
| `trees.py` | Per-tree applicability rules + the Codex trees' naming conventions (takes every Copilot path from `copilot_paths.py` and delegates the `user-invocable: false` Copilot case to `inlining.py`) |
| `copilot_paths.py` | The one definition of every Copilot (`.github/`) path: plain skill `.github/skills/<name>/SKILL.md`, orchestrator prompt `.github/prompts/<name>.prompt.md`, agent `.github/agents/<name>.agent.md`, `.github/copilot-instructions.md`, the inline slot of a principle skill (`InlineSlotPath`, whose `is_file()` is always false), and the Copilot mirror roots scanned for orphans (path definitions only, no judgement; `tests/unit/test_asset_parity_copilot_paths.py` fails if another module spells a `.github` path itself in a single string constant: bare, with a trailing `/`, with repeated or backslash separators, as part of a longer string, or as a fragment of an f-string or format template; prose mentions such as `（.github/）` are not counted. The check inspects individual string constants only and does not evaluate constant expressions such as `".github" + "/skills"`; it also does not detect a path element that starts with a character outside the pattern's allowed set right after the separator, nor a different letter case such as `.GitHub` (only lowercase `.github` is matched), so it is an aid against hand-spelled paths, not a complete guarantee of a single definition (tracked in #637)) |
| `inlining.py` | Whether a `user-invocable: false` skill is really inlined into `.github/copilot-instructions.md` (its complete `principles-source` marker line in the body, not the generated header; reads the file); if not, only the inline slot is expected — a plain skill file is never accepted |
| `exceptions.py` | Documented intentional non-mirrors |
| `staleness.py` | Lightweight last-commit-gap / size-ratio heuristic (git boundary injectable for tests) |
| `report.py` | Builds the matrix + orphan list; renders text/JSON |
| `cli.py` | `python3 -m asset_parity check` |

## Design choices (and why)

- **Package, not a single script**: matches this repo's `dsv2/`/`archive/docidx-v1/` convention
  (dedicated stdlib-only package with `__main__.py`/`cli.py`), not `scripts/<name>.py`
  — this tool has enough distinct concerns (inventory, per-tree conventions,
  exceptions, staleness, reporting) to warrant separate modules and their own unit
  tests, same shape as the other two.
- **Text + JSON, one command**: text for a human running it locally, JSON for
  CI/other tooling to parse; `--format both` when you want both at once.

## CI wiring (issue #155 follow-up, closed; paths filter corrected in #467)

`.github/workflows/asset-parity.yml` runs `python3 -m asset_parity check` on
every `push`/`pull_request` whose diff touches any of the four asset trees
(`.claude/skills|agents`, `.github/skills|prompts|agents`, `.codex/agents`,
`.agents/skills`) — the `paths:` filter deliberately spans all seven mirror
roots (GitHub Copilot alone has two: `.github/skills/**` for plain skills and
`.github/prompts/**` for `disable-model-invocation: true` orchestrator
skills), so the check fires regardless of which platform/tool made the
change (Claude Code, Copilot, Codex CLI, or a human), not just when
`.claude/` changes. It also fires on `.ai/**` (the shared normative source
under "Non-active shared material" above) as a *trigger-only* addition —
this does not add `.ai/` to the inventory `check` reads (that boundary is
Issue #407's decision and is unchanged), it only makes sure a PR that edits
`.ai/` doesn't skip the check that verifies the `.claude/` wrapper linking to
it. `.github/copilot-instructions.md` is a second trigger-only path: `inlining.py`
reads its `principles-source` markers to decide whether a `user-invocable: false`
skill is really inlined, so a change there can flip a cell between `exempt` and
`MISSING` even though it is not an asset tree.
`tests/unit/test_asset_parity_ci_paths.py` cross-checks this `paths:`
list against `asset_parity/trees.py`/`inventory.py` so the two can't drift
apart silently again (Issue #467 — a prior drift where `trees.py` already
scanned `.github/prompts/` but `paths:` omitted it went undetected until a
manual audit).

Failure policy: the workflow uses the tool's **default** exit-code contract
(no `--fail-on-stale`) — a genuine `MISSING` gap (present in `.claude/`,
absent from a mirror, not in the documented exception list) is a concrete,
verifiable fact, so it **fails the build**. Staleness flags stay
informational-only (heuristic, false positives expected) and never block —
consistent with this repo's discipline against tooling unilaterally blocking
merges on fuzzy judgment calls. The matrix is also written to
`$GITHUB_STEP_SUMMARY` so it renders as a readable table in the Actions UI
regardless of pass/fail.

Note: at the time this workflow was added, the parity-seed tree already had a
few genuine `MISSING` entries against `.github` (see `check` output) that
predate this PR. Wiring the check into CI surfaces them as an actionable
red build rather than fixing them — fixing pre-existing mirror gaps is a
separate, subsequent piece of work, not folded into the CI-wiring change
itself.
