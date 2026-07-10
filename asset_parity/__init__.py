"""asset_parity — cross-platform asset drift/presence detector (issue #155, detection half).

Four asset trees mirror the canonical `.claude/` skills/agents onto other AI-coding
platforms: `.github/` (GitHub Copilot), `.codex/agents/` (Codex CLI agents), and
`.agents/skills/` (Codex CLI's documented repo-scoped skill discovery path). Nothing
previously checked whether these trees stay in sync after the canonical tree changes.

This package is a **read-only reporting tool**, not a content generator/synchronizer
(a prior bulk-conversion script, `scripts/lateral_deploy.py`, was deliberately deleted
by owner decision 2026-06-15 — see `.claude/skills/asset-lateral-deploy/SKILL.md` —
because some divergence between platforms is intentional; hand-written per-platform
adaptation replaced it). `asset_parity` only detects and reports; it never writes to
any of the four trees.

See ``python3 -m asset_parity --help`` for usage.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
