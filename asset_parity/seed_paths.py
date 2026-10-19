"""Loader-facing inventory roots and asset modes."""

from ai_layout import NON_ACTIVE_SHARED_DIRS

SKILL = "skill"
AGENT = "agent"

COMMON_SOT_SKILLS_DIR = ".ai/skills"
COMMON_SOT_AGENTS_DIR = ".ai/agents"

PARITY_SEED_SKILLS_DIR = ".claude/skills"
PARITY_SEED_AGENTS_DIR = ".claude/agents"
NON_NORMATIVE_SHARED_DIRS: tuple[str, ...] = NON_ACTIVE_SHARED_DIRS + (".ai/guidance",)

# Invocation modes — meaningful for SKILL kind only (None for AGENT).
MODE_SKILL = "skill"                # default: a model-invocable capability
MODE_ORCHESTRATOR = "orchestrator"  # `disable-model-invocation: true` — user-invoked pipeline
MODE_PRINCIPLE = "principle"        # `user-invocable: false` — always-loaded doctrine



