"""Subagent lifecycle hooks が束縛・回収するロール。"""

from .gated_roles import WRITE_ROLES

TARGET_ROLES = tuple(sorted(WRITE_ROLES))
KARTE_ROLE = "issue-fixer"
