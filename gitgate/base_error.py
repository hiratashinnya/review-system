"""Failure contract for the limited PR-base integration workflow."""


class BaseIntegrationError(RuntimeError):
    """A rejected operation preserves the current worktree for inspection."""


def require(condition, reason):
    if not condition:
        raise BaseIntegrationError(reason)
