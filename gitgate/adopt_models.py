"""Immutable adopt request/result schemas and exact-OID constraints."""
from __future__ import annotations
import re
from dataclasses import dataclass
ADOPT_POLICY_VERSION = "branch-adopt/1.0"

# stage 1 の `git fetch` 用タイムアウト（秒）。到達不能/認証待ちで無期限にハングしないよう、
# CI/自動化文脈での妥当な既定値として 30 秒を採る（Issue #426・F-426-05。worktree.py 側の
# `_cleanup_branch_ref` と同じ既定値・同じ根拠）。
FETCH_TIMEOUT_SECONDS = 30

# adopt は「その worktree が掴む commit」を一意に固定するのが目的なので、abbrev も 64hex も
# 受け付けない（40hex の full OID ちょうど）。
_ADOPT_OID = re.compile(r"^[0-9a-f]{40}$")
_POSITIVE_INT = re.compile(r"^[1-9][0-9]*$")

# git が「そのブランチは別 worktree が使用中」を伝えるときの文言（バージョン差を吸収するため
# 部分一致の集合で持つ。ここに無い文言なら汎用の BRANCH_GIT_ERROR に落ちるだけで fail-open しない）。
_ALREADY_CHECKED_OUT_MARKERS = (
    "already checked out",
    "already used by worktree",
    "is already used by worktree",
)


@dataclass(frozen=True)
class AdoptBranchRequest:
    branch_name: str
    repository: str
    expected_oid: str
    pr: int | None = None


@dataclass(frozen=True)
class AdoptBranchResult:
    branch_name: str
    repository: str
    expected_oid: str
    pr: int | None
    policy_version: str = ADOPT_POLICY_VERSION
