"""Managed Issue dispatch 直前の blocker policy adapter。

Codex は暗号化される prompt を binding に使わず、平文 task_name を main worktree の
durable ownership ledger に事前記録された workspace/Git facts へ一度だけ照合する。Claude は既存の
prompt marker 契約を維持する。branch-source policy は ``gitgate new-branch`` の
独立 gate であり、dispatch 直前の blocker 判定には混ぜない。
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot
from blocker_gate.snapshot import (
    RepositorySnapshotError,
    parse_repository_snapshot,
    project_issue_snapshot,
)

from . import worktree_ledger


ISSUE_START_POLICY_VERSION = "issue-start/1.0"
BINDING_MARKER = "ISSUE_START_BINDING_V1="
# Issue #354 PR-4: `isolation_only` 区分を足した manifest v2 が唯一の正本。
# v1（`archive/issue-start-manifest-v1/managed-entrypoints-v1.json`）は**退役済みで一切読まない**
# ——同ファイルは履歴保全のため archive/ へ git mv して残してあるだけで（PR8 区分1）、
# 編集しても gate の挙動は変わらない。
MANIFEST_SCHEMA_VERSION = "managed-issue-entrypoints/2"
ENTRYPOINT_MANIFEST = Path(__file__).with_name("managed-entrypoints-v2.json")
# 是正ラウンド（`issue-fixer`）用の軽量 binding marker（Issue #354 PR-4）。
# managed 側の7 field marker とは別契約で、GitHub API を一切叩かない
# （blocker 判定は初回実装の dispatch で済んでいる＝`_ISOLATION_ONLY_FIELDS` の docstring 参照）。
FIX_BINDING_MARKER = "ISSUE_FIX_BINDING_V1="

# Issue #345［A］: GitHub API へ到達できない実行環境のための snapshot fallback。
# 孤立ブランチなので main と履歴を共有せず、既定ブランチを汚さない。
# Actions が cron 5分で単一 commit を force-push し、gate は git fetch で読む。
SNAPSHOT_BRANCH = "blocker-snapshot"
SNAPSHOT_PATH = "snapshot.json"
SNAPSHOT_REMOTE_REF = "refs/remotes/origin/" + SNAPSHOT_BRANCH
# staleness 上限（オーナー承認済み）。cron 間隔 5分の 2倍を許容上限とする。
SNAPSHOT_MAX_AGE_SECONDS = 600
SNAPSHOT_GIT_TIMEOUT_SECONDS = 30.0
# fallback の機械的な引き金。到達できているのに stale な材料を使わないため、
# 「GitHub まで届かなかった」ことを表すこの reason だけを引き金にする。
SNAPSHOT_FALLBACK_REASON = "API_UNREACHABLE"
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_BRANCH = _REF
# 是正 marker の `handoff_path`（作業ツリールート相対・`tmp/_handoff/` 直下の1ファイル）。
# 受理条件の正本は `.claude/agents/issue-fixer.md`「入力」で、ここはその機械側の前段——
# 役割側の STOP より dispatch 側の deny の方が早く・具体的に直せる。
_HANDOFF_PATH = re.compile(r"^tmp/_handoff/(?P<name>[A-Za-z0-9._-]+)\.yaml$")
_HTTPS_REMOTE = re.compile(
    r"^https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/"
    r"([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)
_SSH_REMOTE = re.compile(
    r"^(?:git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)


class IssueStartError(Exception):
    """identity/contract/API を一意に検証できない fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class IssueStartGitHubCollector(GitHubCollector):
    """resolver snapshot に加え、deny report 用の title/URL を fresh read する。"""

    def issue_metadata(self, repository: str, number: int) -> Mapping[str, Any]:
        value, _headers = self._get(f"/repos/{repository}/issues/{number}")
        if not isinstance(value, dict):
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        return value


@dataclass(frozen=True)
class IssueStartRequest:
    entrypoint: str
    repository: str
    issue: int


@dataclass(frozen=True)
class CodexIssueStartRequest(IssueStartRequest):
    """durable binding を非破壊検証済みの Codex 初回実装 request。"""

    round: int
    branch_name: str
    handoff_path: str
    expected_oid: str
    workspace: str
    task_key: str
    ledger_entry_id: str


@dataclass(frozen=True)
class IsolationOnlyAck:
    """`isolation_only` 区分の dispatch を受理したことの記録（Issue #354 PR-4）。

    **blocker 判定（GitHub API）を伴わない**のが :class:`IssueStartRequest` との本質的な差。
    是正ラウンドは既に開いた PR への処置であり、Issue の着手可否（open blocker の有無）は
    初回実装の dispatch で判定済みだから、ラウンドごとに再判定する意味が無い。むしろ
    毎ラウンド API を叩くと、API 不通のときレビュー是正まで fail-close で止まる——
    「直せない」ではなく「直しに行けない」という、統制の目的から外れた停止になる。

    したがってこの区分に掛かるのは shape 検証（必須/禁止 field・`required_isolation`）と
    軽量 marker の検証だけで、通れば dispatch は ALLOW（stdout 無出力）になる。
    marker を要求する理由は台帳（FR-W4）——`{issue, round, branch_name, handoff_path}` が
    正確に載っていなければ、どの worktree がどのラウンドのものか事後に辿れない。
    """

    entrypoint: str
    agent_type: str
    issue: int | None
    round: int | None
    branch_name: str | None
    handoff_path: str | None
    expected_oid: str | None
    repository: str | None


@dataclass(frozen=True)
class CodexIsolationOnlyAck(IsolationOnlyAck):
    """durable binding を非破壊検証済みの Codex 是正 dispatch。"""

    workspace: str
    task_key: str
    ledger_entry_id: str


def _manifest() -> Mapping[str, Any]:
    try:
        raw = json.loads(ENTRYPOINT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IssueStartError("ISSUE_START_MANIFEST_ERROR") from exc
    if (
        not isinstance(raw, dict)
        or raw.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or raw.get("policy_version") != ISSUE_START_POLICY_VERSION
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return raw


def _entries(key: str, *, required: bool) -> list[Mapping[str, Any]]:
    value = _manifest().get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value) or not all(
        isinstance(item, dict) for item in value
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return value


def _managed_entries() -> list[Mapping[str, Any]]:
    return _entries("managed", required=True)


def _isolation_only_entries() -> list[Mapping[str, Any]]:
    """`isolation_only` 区分のエントリ（未宣言の manifest では空）。"""
    return _entries("isolation_only", required=False)


def _agent_types(entries: Sequence[Mapping[str, Any]]) -> set[str]:
    raw = [item.get("agent_type") for item in entries]
    if not all(isinstance(value, str) and value for value in raw):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return set(raw)


def _request(raw: Mapping[str, Any]) -> IssueStartRequest:
    expected = {"entrypoint", "repository", "issue"}
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    entrypoint = raw.get("entrypoint")
    repository = raw.get("repository")
    issue = raw.get("issue")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN")
    if entrypoint not in {item.get("entrypoint") for item in _managed_entries()}:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", entrypoint)
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    return IssueStartRequest(entrypoint, repository, issue)


def _claude_request(raw: Mapping[str, Any]) -> IssueStartRequest:
    """Claude の既存 V1 marker schema を変えず、blocker binding だけを返す。"""
    expected = {
        "entrypoint", "repository", "issue", "branch_name", "base_ref", "base_oid", "base_pr"
    }
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    branch_name = raw.get("branch_name")
    base_ref = raw.get("base_ref")
    base_oid = raw.get("base_oid")
    base_pr = raw.get("base_pr")
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise IssueStartError("ISSUE_START_BRANCH_INVALID")
    if not isinstance(base_ref, str) or not _REF.fullmatch(base_ref):
        raise IssueStartError("ISSUE_START_BASE_REF_INVALID")
    if not isinstance(base_oid, str) or not _OID.fullmatch(base_oid):
        raise IssueStartError("ISSUE_START_BASE_OID_INVALID")
    if base_pr is not None and (
        not isinstance(base_pr, int) or isinstance(base_pr, bool) or base_pr < 1
    ):
        raise IssueStartError("ISSUE_START_BASE_PR_INVALID")
    return _request({key: raw[key] for key in ("entrypoint", "repository", "issue")})


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    try:
        completed = runner(
            list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False
        )
    except OSError as exc:
        raise IssueStartError("ISSUE_START_GIT_ERROR", type(exc).__name__) from exc
    if completed.returncode != 0:
        raise IssueStartError("ISSUE_START_GIT_ERROR", argv[1] if len(argv) > 1 else "git")
    output = completed.stdout
    if not isinstance(output, str) or "\0" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    if output.endswith("\n"):
        output = output[:-1]
    if "\n" in output or "\r" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    return output


def _canonical_github_repository(remote_url: str) -> str:
    if "\n" in remote_url or "\r" in remote_url:
        raise IssueStartError("ISSUE_START_ORIGIN_INVALID")
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote_url)
        if match:
            repository = f"{match.group(1)}/{match.group(2)}"
            if _REPOSITORY.fullmatch(repository):
                return repository
    raise IssueStartError("ISSUE_START_ORIGIN_INVALID")


def _codex_repository(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    payload_cwd = payload.get("cwd")
    if not isinstance(payload_cwd, str) or not payload_cwd or not Path(payload_cwd).is_absolute():
        raise IssueStartError("ISSUE_START_CWD_INVALID")
    try:
        payload_root = Path(payload_cwd).resolve(strict=True)
        hook_root = (Path.cwd() if cwd is None else cwd).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_CWD_INVALID") from exc
    if not payload_root.is_dir() or payload_root != hook_root:
        raise IssueStartError("ISSUE_START_CWD_MISMATCH")
    if _run_git(["git", "rev-parse", "--is-inside-work-tree"], cwd=hook_root, runner=runner) != "true":
        raise IssueStartError("ISSUE_START_NOT_WORKTREE")
    top_level = _run_git(
        ["git", "rev-parse", "--show-toplevel"], cwd=hook_root, runner=runner
    )
    try:
        git_root = Path(top_level).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_WORKTREE_ROOT_INVALID") from exc
    if git_root != hook_root:
        raise IssueStartError("ISSUE_START_WORKTREE_ROOT_MISMATCH")
    origin = _run_git(
        ["git", "remote", "get-url", "origin"], cwd=hook_root, runner=runner
    )
    return _canonical_github_repository(origin)


def _managed_transport(
    tool_name: str,
    agent_type: str,
    entries: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[Mapping[str, Any], str, Mapping[str, Any]]:
    """`entries` に一致する transport を1件だけ探す（F-354-13）。

    名前は managed 専用に見えるが、`entries` を明示すれば **`isolation_only` 区分の
    :func:`_parse_isolation_only` からも呼ばれる**——`entries=None` のときだけ
    :func:`_managed_entries` を既定にする。managed 経路と同じ「重複/欠落は fail-close」
    ロジックを isolation_only 側でも再利用するための共通化であり、isolation_only の
    entry が managed 側の shape 検証を経ていないわけではない。
    """
    matches: list[tuple[Mapping[str, Any], str, Mapping[str, Any]]] = []
    for entry in (_managed_entries() if entries is None else entries):
        if entry.get("agent_type") != agent_type:
            continue
        transports = entry.get("binding_transports")
        if not isinstance(transports, dict):
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
        for harness, transport in transports.items():
            if not isinstance(harness, str) or not isinstance(transport, dict):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            tool_names = transport.get("tool_names")
            if not isinstance(tool_names, list) or not all(isinstance(name, str) for name in tool_names):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            if tool_name in tool_names:
                matches.append((entry, harness, transport))
    if not matches:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", tool_name)
    if len(matches) != 1:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_AMBIGUOUS", tool_name)
    return matches[0]


def _require_transport_available(harness: str, transport: Mapping[str, Any]) -> None:
    """manifest で unavailable と宣言した transport を parser 入口で拒否する。

    Codex の project hook trust は group index 単位である。新しい all-tool hook が
    untrusted で実行対象に入っていない状態でも、既存 index の issue-start hook が
    この検査を実行して dispatch を fail-close する。
    """

    if harness == "codex" and "availability" not in transport:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    availability = transport.get("availability", "available")
    if availability == "available":
        return
    if availability != "unavailable":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    missing = transport.get("missing_observations")
    if (
        not isinstance(missing, list)
        or not missing
        or not all(isinstance(item, str) and item for item in missing)
        or len(missing) != len(set(missing))
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    raise IssueStartError(
        "ISSUE_START_TRANSPORT_UNAVAILABLE",
        f"harness={harness}; missing_observations={','.join(missing)}",
    )


def _validate_tool_input_shape(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any]
) -> None:
    """manifest が宣言する harness 固有 field の必須・混在禁止を検証する。"""
    required = transport.get("required_tool_input_fields")
    forbidden = transport.get("forbidden_tool_input_fields")
    for fields in (required, forbidden):
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or len(fields) != len(set(fields))
        ):
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if set(required) & set(forbidden):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    missing = [field for field in required if field not in tool_input]
    mixed = [field for field in forbidden if field in tool_input]
    if missing or mixed:
        detail = "missing=" + ",".join(missing) + ";mixed=" + ",".join(mixed)
        raise IssueStartError("ISSUE_START_TOOL_INPUT_SHAPE_INVALID", detail)
    _validate_isolation(tool_input, transport)


def _validate_isolation(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any]
) -> None:
    """worktree 分離を dispatch の必須条件として強制する（Issue #350）。

    `issue-implementer` は「isolated worktree で実装する」契約だが、その分離は
    role 側では実現できない——gitgate に worktree verb は無く、agent-command-gate の
    層2 が `cd` を deny するため、仮に worktree を作れてもそこへ潜れない。分離を
    与えられるのは dispatch 側だけで、Claude harness では Agent tool の `isolation`
    パラメータがそれを担う（cwd が `.claude/worktrees/agent-<id>` の locked worktree
    になり、呼び出し元の main worktree は branch switch されない）。

    指定を欠いた dispatch は main worktree を共有したまま branch switch する＝
    呼び出し元の作業ツリーを巻き込むので、dispatch 自体を fail-close で拒否する。
    `required_isolation` を宣言しない transport（Codex の `spawn_agent` には
    isolation 概念が無い）は素通しする＝claude 側の要求を持ち込まない。
    """
    if "required_isolation" not in transport:
        return
    expected = transport.get("required_isolation")
    if not isinstance(expected, str) or not expected:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    actual = tool_input.get("isolation")
    if actual != expected:
        raise IssueStartError(
            "ISSUE_START_ISOLATION_NOT_WORKTREE",
            f"expected isolation={expected}; actual={actual!r}",
        )


def _marker_payload(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any], marker: str
) -> Mapping[str, Any]:
    """prompt から binding marker 行をちょうど1つ取り出して JSON として読む。"""
    prompt_field = transport.get("prompt_field")
    if not isinstance(prompt_field, str) or not isinstance(marker, str) or not marker:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    prompt = tool_input.get(prompt_field)
    if not isinstance(prompt, str):
        raise IssueStartError("ISSUE_START_BINDING_MISSING")
    lines = [line for line in prompt.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise IssueStartError("ISSUE_START_BINDING_MISSING_OR_DUPLICATE")
    try:
        raw = json.loads(lines[0][len(marker):])
    except json.JSONDecodeError as exc:
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON") from exc
    if not isinstance(raw, dict):
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON")
    return raw


def _fix_binding(
    raw: Mapping[str, Any], *, entrypoint: str, agent_type: str
) -> IsolationOnlyAck:
    """`ISSUE_FIX_BINDING_V1` marker（exact 6 field）を検証して ack を返す。

    `base_*` を欠くのは、この区分が **GitHub API を叩かない**から——blocker 判定と
    branch-source 判定の材料はどちらもここでは行わない。一方 `repository` は持つ：
    是正者は `gitgate adopt-branch --repository OWNER/REPO --expected-oid` で既存 PR
    ブランチを自分の worktree へ取得するが、是正者は生 `git remote` を deny されており
    OWNER/REPO を機械的に得る手段が無い（F-354-10）。`expected_oid` と同じ理由で、
    値の出所を dispatch 契約側に固定しておく（出所が曖昧なまま是正者に推測させると、
    掴む repository/commit が dispatch と食い違いうる）。
    """
    expected = {"issue", "round", "branch_name", "repository", "expected_oid", "handoff_path"}
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    issue = raw.get("issue")
    round_ = raw.get("round")
    branch_name = raw.get("branch_name")
    repository = raw.get("repository")
    expected_oid = raw.get("expected_oid")
    handoff_path = raw.get("handoff_path")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    if not isinstance(round_, int) or isinstance(round_, bool) or round_ < 1:
        raise IssueStartError("ISSUE_START_ROUND_INVALID")
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise IssueStartError("ISSUE_START_BRANCH_INVALID")
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(expected_oid, str) or not _OID.fullmatch(expected_oid):
        raise IssueStartError("ISSUE_START_EXPECTED_OID_INVALID")
    match = _HANDOFF_PATH.fullmatch(handoff_path) if isinstance(handoff_path, str) else None
    if match is None:
        raise IssueStartError(
            "ISSUE_START_HANDOFF_PATH_INVALID",
            "expected tmp/_handoff/<name>.yaml (作業ツリールート相対)",
        )
    # ファイル名を `{agent_type}--issue-{issue}` に束縛する。境界の1文字（`-` か `.`）まで
    # 見るのは、`issue-354` の dispatch が `…--issue-3541.yaml`（別 Issue のファイル）を
    # 受理しないため（`.claude/agents/issue-fixer.md` と同じ検査を dispatch 側でも掛ける）。
    prefix = f"{agent_type}--issue-{issue}"
    name = match.group("name")
    if not (name == prefix or (name.startswith(prefix) and name[len(prefix)] in "-.")):
        raise IssueStartError(
            "ISSUE_START_HANDOFF_PATH_INVALID", f"expected file name to start with {prefix}"
        )
    return IsolationOnlyAck(
        entrypoint=entrypoint,
        agent_type=agent_type,
        issue=issue,
        round=round_,
        branch_name=branch_name,
        handoff_path=handoff_path,
        expected_oid=expected_oid,
        repository=repository,
    )


def parse_dispatch_payload(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None = None,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> IssueStartRequest | IsolationOnlyAck | None:
    """Codex/Claude の tool payload から dispatch binding を読む。

    manifest の3区分に対応する:

    * ``managed``（`issue-implementer`）→ :class:`IssueStartRequest`。
      marker 欠如・重複・tool mismatch をすべて拒否し、呼び出し側が blocker 判定へ進む。
    * ``isolation_only``（`issue-fixer`）→ :class:`IsolationOnlyAck`。
      shape/isolation/軽量 marker だけを検証し、**GitHub API へは行かない**（理由＝
      :class:`IsolationOnlyAck` の docstring）。
    * どちらにも載っていない agent_type → ``None``（unmanaged・素通し）。
    """
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
    targets = [tool_input.get(field) for field in ("agent_type", "subagent_type")]
    present_targets = [target for target in targets if target is not None]
    if len(present_targets) != 1 or not isinstance(present_targets[0], str) or not present_targets[0]:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    agent_type = present_targets[0]
    managed_types = _agent_types(_managed_entries())
    isolation_only_entries = _isolation_only_entries()
    isolation_only_types = _agent_types(isolation_only_entries)
    # 同じ agent_type が両区分に載っていたら、どちらの契約で判定すべきか一意に決まらない。
    # 「厳しい方」を勝手に選ばず manifest 側の誤りとして fail-close する。
    if managed_types & isolation_only_types:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if agent_type in isolation_only_types:
        return _parse_isolation_only(
            tool_name,
            tool_input,
            agent_type,
            isolation_only_entries,
            payload=payload,
            cwd=cwd,
            now=datetime.now(timezone.utc) if now is None else now,
            runner=runner,
        )
    if agent_type not in managed_types:
        return None
    entry, harness, transport = _managed_transport(tool_name, agent_type)
    _require_transport_available(harness, transport)
    _validate_tool_input_shape(tool_input, transport)
    expected_field = transport.get("agent_type_field")
    if expected_field not in {"agent_type", "subagent_type"} or tool_input.get(expected_field) != agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    entrypoint = entry.get("entrypoint")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if harness == "codex":
        task_name = tool_input.get("task_name")
        pattern = transport.get("task_name_pattern")
        if not isinstance(task_name, str) or not isinstance(pattern, str):
            raise IssueStartError("ISSUE_START_TASK_NAME_INVALID")
        try:
            match = re.fullmatch(pattern, task_name)
        except re.error as exc:
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR") from exc
        if match is None or match.lastindex != 1:
            raise IssueStartError("ISSUE_START_TASK_NAME_INVALID")
        issue = int(match.group(1))
        binding = _validate_codex_binding(
            payload,
            tool_input,
            agent_type=agent_type,
            cwd=cwd,
            now=datetime.now(timezone.utc) if now is None else now,
            runner=runner,
        )
        if binding["issue"] != issue:
            raise IssueStartError("CODEX_BINDING_TASK_KEY_MISMATCH", task_name)
        request = _request({
            "entrypoint": entrypoint,
            "repository": binding["repository"],
            "issue": binding["issue"],
        })
        return CodexIssueStartRequest(
            entrypoint=request.entrypoint,
            repository=request.repository,
            issue=request.issue,
            round=binding["round"],
            branch_name=binding["branch_name"],
            handoff_path=binding["handoff_path"],
            expected_oid=binding["expected_oid"],
            workspace=binding["workspace"],
            task_key=binding["task_key"],
            ledger_entry_id=binding["entry_id"],
        )
    if harness != "claude":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    raw = _marker_payload(tool_input, transport, transport.get("binding_marker"))
    request = _claude_request(raw)
    if request.entrypoint != entrypoint:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", request.entrypoint)
    return request


def _parse_isolation_only(
    tool_name: str,
    tool_input: Mapping[str, Any],
    agent_type: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    payload: Mapping[str, Any],
    cwd: Path | None,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> IsolationOnlyAck:
    """`isolation_only` 区分の dispatch を検証する（GitHub API へは一切行かない）。

    managed 経路と**同じ** :func:`_validate_tool_input_shape` を通すので、
    `required_isolation` の強制（`ISSUE_START_ISOLATION_NOT_WORKTREE`）は分岐で
    弱まらない——ここが本区分の存在理由（分離だけを課したい）そのものだから。
    """
    entry, harness, transport = _managed_transport(tool_name, agent_type, entries)
    _require_transport_available(harness, transport)
    _validate_tool_input_shape(tool_input, transport)
    expected_field = transport.get("agent_type_field")
    if expected_field not in {"agent_type", "subagent_type"} or tool_input.get(expected_field) != agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    entrypoint = entry.get("entrypoint")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if harness == "codex":
        binding = _validate_codex_binding(
            payload, tool_input, agent_type=agent_type, cwd=cwd, now=now, runner=runner
        )
        return CodexIsolationOnlyAck(
            entrypoint=entrypoint,
            agent_type=agent_type,
            issue=binding["issue"],
            round=binding["round"],
            branch_name=binding["branch_name"],
            handoff_path=binding["handoff_path"],
            expected_oid=binding["expected_oid"],
            repository=binding["repository"],
            workspace=binding["workspace"],
            task_key=binding["task_key"],
            ledger_entry_id=binding["entry_id"],
        )
    if harness != "claude":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    raw = _marker_payload(tool_input, transport, transport.get("binding_marker"))
    return _fix_binding(raw, entrypoint=entrypoint, agent_type=agent_type)


def _validate_codex_binding(
    payload: Mapping[str, Any],
    tool_input: Mapping[str, Any],
    *,
    agent_type: str,
    cwd: Path | None,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    """Codex spawn を durable task binding へ非破壊で照合する。

    spawn payload の ``cwd`` は turn/session cwd であり child workspace ではないため、
    workspace として使わない。検証対象は prepare 時に Git facts を固定した
    ledger entry 自身であり、この処理は ``open`` から状態遷移させない。
    """

    from .codex_binding import CodexBindingError, validate_spawn_binding

    task_key = tool_input.get("task_name")
    if not isinstance(task_key, str):
        raise IssueStartError("ISSUE_START_TASK_NAME_INVALID")
    try:
        hook_root = (Path.cwd() if cwd is None else cwd).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_CWD_INVALID") from exc
    try:
        return validate_spawn_binding(
            repo_root=hook_root,
            role=agent_type,
            task_key=task_key,
            now=now,
            runner=runner,
        )
    except CodexBindingError as exc:
        raise IssueStartError(exc.reason, exc.detail) from exc


def _error_evidence(request: IssueStartRequest | None, reason: str, detail: str = "") -> dict[str, Any]:
    return {
        "schema_version": "issue-start-evidence/1",
        "policy_version": ISSUE_START_POLICY_VERSION,
        "result": "ERROR",
        "exit_code": 20,
        "reason": reason,
        "detail": detail,
        "binding": asdict(request) if request is not None else None,
        "blocker_evidence": None,
        "blockers": [],
        # 判定へ到達していないので取得経路も確定していない。
        "source": None,
        "snapshot_generated_at": None,
    }


def _git_output(
    argv: Sequence[str],
    *,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    reason: str,
) -> str:
    """snapshot fallback 用の raw git 実行（複数行 stdout を許す）。"""
    try:
        completed = runner(
            list(argv),
            cwd=None if cwd is None else str(cwd),
            text=True,
            capture_output=True,
            shell=False,
            timeout=SNAPSHOT_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise IssueStartError(reason, type(exc).__name__) from exc
    if completed.returncode != 0 or not isinstance(completed.stdout, str):
        raise IssueStartError(reason, argv[1] if len(argv) > 1 else "git")
    return completed.stdout


def read_repository_snapshot(
    *,
    repository: str,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Mapping[str, Any]:
    """孤立ブランチ ``blocker-snapshot`` の ``snapshot.json`` を fetch して読む。

    ローカルの作業ツリーやローカル cache は材料にしない（改竄と stale を
    同時に許すため）。必ず ``origin`` から fetch した ref を読む。

    ``origin`` が invocation の repository を指すことを **fetch より前に**
    検証する（Issue #345 F-345-02）。これが無いと identity 束縛が snapshot の
    自己申告 ``repository`` field だけになり、origin を自分の管理下へ向けられる
    者が対象 repository を名乗る snapshot を配って ALLOW を作れてしまう
    ——policy §3.3.1 の「偽造には対象 repository への push 権限が要る」という
    論拠がその経路で成立しなくなる。正規化は Codex 経路
    （``_codex_repository`` → ``_canonical_github_repository``）と同一とする。
    """
    top_level = _git_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_GIT_ERROR",
    ).strip()
    if not top_level:
        raise IssueStartError("ISSUE_START_SNAPSHOT_GIT_ERROR", "rev-parse")
    try:
        root = Path(top_level).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_GIT_ERROR", "toplevel") from exc
    # `_run_git` ではなく `_git_output` を使うのは、snapshot 経路の git 実行に
    # 揃えて timeout を掛けるため（到達不能環境で git がぶら下がると gate ごと
    # 止まる）。複数行・空文字は `_canonical_github_repository` が弾く。
    origin = _canonical_github_repository(
        _git_output(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            runner=runner,
            reason="ISSUE_START_SNAPSHOT_GIT_ERROR",
        ).strip()
    )
    if origin != repository:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_ORIGIN_MISMATCH",
            f"origin={origin}; request={repository}",
        )
    _git_output(
        [
            "git",
            "fetch",
            "--no-tags",
            "--quiet",
            "origin",
            f"+refs/heads/{SNAPSHOT_BRANCH}:{SNAPSHOT_REMOTE_REF}",
        ],
        cwd=root,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_FETCH_FAILED",
    )
    raw = _git_output(
        ["git", "show", f"{SNAPSHOT_REMOTE_REF}:{SNAPSHOT_PATH}"],
        cwd=root,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_UNREADABLE",
    )
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID_JSON") from exc
    try:
        return parse_repository_snapshot(value)
    except RepositorySnapshotError as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID", exc.reason) from exc


def _assert_snapshot_fresh(
    snapshot: Mapping[str, Any], now: datetime | None
) -> None:
    """上限付き staleness を機械的に強制する。期限切れも未来時刻も fail-close。"""
    current = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    age = (current - snapshot["generated_at_datetime"]).total_seconds()
    if age < 0:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_FUTURE",
            f"generated_at={snapshot['generated_at']}; now={current.isoformat()}",
        )
    if age > SNAPSHOT_MAX_AGE_SECONDS:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_STALE",
            f"age={int(age)}s; max={SNAPSHOT_MAX_AGE_SECONDS}s;"
            f" generated_at={snapshot['generated_at']}",
        )


class SnapshotIssueMetadata:
    """snapshot 由来 BLOCK の deny report を、API を叩かずに組み立てる。

    到達不能環境では title/URL を API から引けない。引きに行くと fallback の
    意味が消えるので、snapshot が同梱する値だけを使う。
    """

    def __init__(self, metadata: Mapping[str, Mapping[str, str]]) -> None:
        self._metadata = metadata

    def issue_metadata(self, repository: str, number: int) -> Mapping[str, Any]:
        value = self._metadata.get(f"{repository}#{number}")
        if value is None:
            raise IssueStartError(
                "ISSUE_START_SNAPSHOT_REPORT_MISSING", f"{repository}#{number}"
            )
        return value


def _snapshot_fallback_required(
    blocker: Mapping[str, Any], collected: Mapping[str, Any]
) -> bool:
    """当該 invocation が GitHub を**一度も観測できていない**ときだけ真を返す。

    条件は3つの AND であり、どれか一つでも欠ければ従来どおり ERROR のまま
    fail-close する。

    1. verdict が ``ERROR`` である。
    2. ``reasons`` に ``API_UNREACHABLE`` を含む。``primary_reason`` ではなく
       membership で見るのは、到達不能環境の実測形が
       ``["API_UNREACHABLE", "RELATION_TARGET_UNREADABLE"]`` であり canonical
       sort の先頭が別 reason になるため（この理由は F-345-01 の是正後も有効）。
    3. **収集できた node が1つも無い。** reasons membership だけを引き金にすると、
       API へ到達できている環境で1 node が一過性 timeout / URLError を起こした
       だけでも fallback が起動し、本来 fail-close だった invocation が最大10分
       stale な材料で ALLOW になりうる（F-345-01）。1 node でも読めていれば
       その invocation は GitHub provenance を観測している＝「到達不能」では
       ないので、stale な材料を使う理由がない。

    3 は「空である」ことを**積極的に確認**する（key 欠落・型不正では真を返さない）。
    fallback は許容側の経路なので、観測できないときは開かない。
    """
    reasons = blocker.get("reasons")
    nodes = collected.get("nodes")
    return (
        blocker.get("result") == "ERROR"
        and isinstance(reasons, list)
        and SNAPSHOT_FALLBACK_REASON in reasons
        and isinstance(nodes, dict)
        and not nodes
    )


def _blocker_report(collector: Any, blocker: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not hasattr(collector, "issue_metadata"):
        raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
    report: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in blocker.get("findings", []):
        if finding.get("code") != "OPEN_BLOCKER" or finding.get("waiver_id") is not None:
            continue
        path = finding.get("path")
        if not isinstance(path, list) or not path or not isinstance(path[-1], str):
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        blocker_ref = path[-1]
        if "#" not in blocker_ref:
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        repository, raw_number = blocker_ref.rsplit("#", 1)
        if not raw_number.isdigit():
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        if blocker_ref in seen:
            continue
        seen.add(blocker_ref)
        try:
            metadata = collector.issue_metadata(repository, int(raw_number))
        except IssueStartError:
            raise
        except Exception as exc:
            raise IssueStartError("ISSUE_START_REPORT_API_ERROR", type(exc).__name__) from exc
        title = metadata.get("title")
        url = metadata.get("html_url")
        if not isinstance(title, str) or not title or not isinstance(url, str) or not url:
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        report.append({
            "number": int(raw_number),
            "repository": repository,
            "title": title,
            "url": url,
            "path": path,
            "next_action": "blockerをcloseするかblocking relationを解消し、fresh invocationで再試行する",
        })
    return report


def evaluate_issue_start(
    request: IssueStartRequest,
    *,
    collector_factory: Callable[[str | None], Any] = IssueStartGitHubCollector,
    token: str | None = None,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: datetime | None = None,
    snapshot_reader: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """fresh blocker read を行い、同じ repository/Issue へ再束縛する。

    Issue #345［A］: **API 優先**。fresh read が ``API_UNREACHABLE`` を返し、かつ
    node を1つも読めなかった invocation だけが孤立ブランチ snapshot へ fallback
    する。到達できる環境の挙動は一切変わらない（従来どおり invocation ごとの
    fresh read）し、部分的に読めた invocation も fallback しない（F-345-01）。
    """
    try:
        collector = collector_factory(token)
        # #299 完了前は waiver provider を渡さない。collector に機能があっても bypass 不可。
        collected = collector.collect_issue(request.repository, request.issue)
        blocker = evaluate_snapshot(collected, waiver_provider=None)
        source = "api"
        snapshot_generated_at: str | None = None
        report_provider: Any = collector
        if _snapshot_fallback_required(blocker, collected):
            read = read_repository_snapshot if snapshot_reader is None else snapshot_reader
            repository_snapshot = read(
                repository=request.repository, cwd=cwd, runner=runner
            )
            _assert_snapshot_fresh(repository_snapshot, now)
            try:
                projected, metadata = project_issue_snapshot(
                    repository_snapshot, request.repository, request.issue
                )
            except RepositorySnapshotError as exc:
                raise IssueStartError(
                    "ISSUE_START_SNAPSHOT_BINDING_MISMATCH", exc.detail or exc.reason
                ) from exc
            # 判定は API 経路と同一の evaluator を通す（ロジックを分岐させない）。
            blocker = evaluate_snapshot(projected, waiver_provider=None)
            source = "snapshot"
            snapshot_generated_at = repository_snapshot["generated_at"]
            report_provider = SnapshotIssueMetadata(metadata)
        validate_result_semantics(blocker, int(blocker["exit_code"]))
        subject = blocker.get("subject")
        if (
            blocker.get("mode") != "issue-start"
            or blocker.get("repository") != request.repository
            or not isinstance(subject, dict)
            or subject.get("type") != "issue"
            or subject.get("number") != request.issue
        ):
            raise IssueStartError("ISSUE_START_BLOCKER_BINDING_MISMATCH")
        if blocker["result"] != "ALLOW":
            blockers = (
                _blocker_report(report_provider, blocker)
                if blocker["result"] == "BLOCK"
                else []
            )
            return {
                "schema_version": "issue-start-evidence/1",
                "policy_version": ISSUE_START_POLICY_VERSION,
                "result": blocker["result"],
                "exit_code": blocker["exit_code"],
                "reason": blocker["primary_reason"],
                "fetched_at": blocker["fetched_at"],
                "binding": asdict(request),
                "blocker_evidence": blocker,
                "blockers": blockers,
                "source": source,
                "snapshot_generated_at": snapshot_generated_at,
            }
        return {
            "schema_version": "issue-start-evidence/1",
            "policy_version": ISSUE_START_POLICY_VERSION,
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
            "fetched_at": blocker["fetched_at"],
            "binding": asdict(request),
            "blocker_evidence": blocker,
            "blockers": [],
            "source": source,
            "snapshot_generated_at": snapshot_generated_at,
        }
    except IssueStartError:
        raise
    except ContractError as exc:
        raise IssueStartError("ISSUE_START_CONTRACT_ERROR", str(exc)) from exc
    except RepositorySnapshotError as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID", exc.reason) from exc
    except Exception as exc:
        raise IssueStartError("ISSUE_START_EVALUATION_ERROR", type(exc).__name__) from exc


def fail_closed(request: IssueStartRequest | None, exc: IssueStartError) -> dict[str, Any]:
    return _error_evidence(request, exc.reason, exc.detail)


def _ledger_metadata(payload: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """台帳起票に載せる付随情報（``agent_type`` / ``branch_name``）を best-effort で読む。

    ここは**判定に使わない**（起票の材料にするだけ）。`parse_dispatch_payload` が既に
    受理した payload を読み直しているので厳格な検証はせず、読めなければ ``None`` を返す。
    ``branch_name`` は Claude の marker にしか無い（Codex 経路は ``None``）。
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, Mapping):
        return None, None
    agent_type = None
    for field in ("agent_type", "subagent_type"):
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            agent_type = value
            break
    branch_name = None
    prompt = tool_input.get("prompt")
    if isinstance(prompt, str):
        lines = [line for line in prompt.splitlines() if line.startswith(BINDING_MARKER)]
        if len(lines) == 1:
            try:
                raw = json.loads(lines[0][len(BINDING_MARKER):])
            except json.JSONDecodeError:
                raw = None
            if isinstance(raw, dict) and isinstance(raw.get("branch_name"), str):
                branch_name = raw["branch_name"]
    return agent_type, branch_name


def _residue_root(repo_root: Path | None) -> Path:
    """台帳の置き場（main worktree root）を決める。``LedgerError`` はそのまま送出する。"""
    return worktree_ledger.main_worktree_root(
        Path.cwd() if repo_root is None else Path(repo_root)
    )


def _residue_items(entries: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(
        f"{entry.get('entry_id')}[{entry.get('status')}]"
        f"@{entry.get('worktree_path') or '<unbound>'}"
        for entry in entries
    )


def assert_no_worktree_residue(
    *,
    repo_root: Path | None = None,
    now: datetime,
) -> dict[str, Any]:
    """残留 worktree がある状態での次 dispatch を deny する（Issue #354・PR-3・候補C）。

    **`issue-implementer` に限らず全 `Task` dispatch へ掛ける。** #354 が実測した事象は
    「残留 worktree があるのに `pr-reviewer` を dispatch し、レビューアが古い作業ツリーを
    掴んだ」というものであり、managed dispatch だけを見張っていては正面から塞げない。
    過剰 deny の緩和は **deny 文言に必ず解消コマンドを載せる**ことと
    ``worktree-forget --reason`` の逃げ道で行う（deny を弱めることでは行わない）。

    判定の前に :func:`worktree_ledger.sweep_orphans` を1回走らせる。掃引は「占有を主張して
    いるのに worktree が実在しない」エントリだけを ``stale`` へ落とす状態→状態の照合で、
    落とす候補が無ければ台帳へ書き込まない（正常系では no-op）。

    ==============================================  ===================================
    reason                                          条件
    ==============================================  ===================================
    ``ISSUE_START_WORKTREE_RESIDUE``                ``stale`` / ``stopped`` / ``collected``
                                                    のエントリが1件以上ある
    ``ISSUE_START_WORKTREE_UNCLAIMED``              ディスク上の ``agent-*`` が
                                                    ``running`` / ``stopped`` のどれにも
                                                    紐づかない
    ``ISSUE_START_WORKTREE_LEDGER_ERROR``           台帳が読めない／壊れている（fail-close）
    ==============================================  ===================================

    ``open`` / ``running`` / ``stopped`` の worktree は live もしくは回収処理中なので
    ``unclaimed`` としては扱わない。``stopped`` だけは **residue としても検出する**
    ——``SubagentStop`` が停止を記録したのに ``collected`` まで進んでいない＝回収段が
    失敗したか実行されていない、という意味だから（:func:`worktree_ledger.residue_report`
    の docstring に二重の性質の説明がある）。

    残留が無ければ組み立てた report を返す（呼び出し側が evidence に載せる）。
    """
    try:
        root = _residue_root(repo_root)
        swept = worktree_ledger.sweep_orphans(root, now=now)
        report = worktree_ledger.residue_report(root)
    except worktree_ledger.LedgerError as exc:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_LEDGER_ERROR",
            f"{exc.reason}{': ' + exc.detail if exc.detail else ''}"
            "（台帳を一意に読めない間は dispatch を通さない＝fail-close）",
        ) from exc
    except Exception as exc:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_LEDGER_ERROR", type(exc).__name__
        ) from exc

    if report["stale"]:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_RESIDUE",
            f"未回収の worktree が残っている: {_residue_items(report['stale'])}"
            "。解消: python3 -m gitgate collect-worktree --entry <entry-id>"
            "（回収不能なら python3 -m gitgate worktree-forget --entry <entry-id>"
            " --reason <text>）",
        )
    if report["unclaimed"]:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_UNCLAIMED",
            f"台帳のどのエントリにも紐づかない worktree がある: {', '.join(report['unclaimed'])}"
            "。解消: python3 -m gitgate worktree-release <path> --force-uncollected"
            " --reason <text>",
        )
    return {"swept": swept, **report}


def record_open_entry(
    payload: Mapping[str, Any],
    request: IssueStartRequest,
    *,
    now: datetime,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """ALLOW した dispatch を worktree 所有台帳へ ``open`` 起票する（Issue #309・PR-1）。

    **この関数は dispatch を deny しない。** 台帳の書込に失敗しても例外を投げず、
    ``{"entry_id": None, "error": "<reason>"}`` を返して呼び出し側は ALLOW のまま進む
    （本 PR は fail-open）。deny へ倒すのは PR-3（統制の発効）——「統制を先に、付与は別 PR」
    と同じ理由で、**観測が正確になったことを実測してから** deny を有効にする。

    ``round`` / ``handoff_path`` は現行の ``ISSUE_START_BINDING_V1`` marker schema に無いので
    ``None`` のまま起票する（marker 拡張は PR-4）。
    """
    if isinstance(request, CodexIssueStartRequest):
        # Codex は spawn 前 prepare で既に open。parse は非破壊で、trusted start
        # observer が actual identity/workspace を観測するまで running へ遷移しない。
        # Claude 用の best-effort open を重ねると ownership が二重になる。
        return {"entry_id": request.ledger_entry_id, "error": None, "platform": "codex"}
    try:
        root = worktree_ledger.main_worktree_root(
            Path.cwd() if repo_root is None else Path(repo_root)
        )
        agent_type, branch_name = _ledger_metadata(payload)
        if agent_type is None:
            return {"entry_id": None, "error": "LEDGER_AGENT_TYPE_UNREADABLE"}
        entry_id = worktree_ledger.open_entry(
            root,
            issue=request.issue,
            agent_type=agent_type,
            round=None,
            branch_name=branch_name,
            handoff_path=None,
            now=now,
        )
        return {"entry_id": entry_id, "error": None}
    except worktree_ledger.LedgerError as exc:
        return {"entry_id": None, "error": exc.reason, "detail": exc.detail}
    except Exception as exc:  # 台帳の事故で dispatch を止めない（本 PR は fail-open）
        return {"entry_id": None, "error": type(exc).__name__}


def record_isolation_only_entry(
    ack: IsolationOnlyAck,
    *,
    now: datetime,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """`isolation_only` の ALLOW を worktree 所有台帳へ ``open`` 起票する（Issue #354 PR-4）。

    **起票は省略できない**——`isolation: "worktree"` を課した以上、是正ラウンドも
    `.claude/worktrees/agent-<id>/` を占有する。`open` エントリが無いと
    `SubagentStart`（`worktree_ledger.bind_agent`）が束縛先を見つけられず、その worktree は
    台帳のどのエントリにも紐づかない＝次の dispatch が `ISSUE_START_WORKTREE_UNCLAIMED` で
    deny される（統制が機能不全ではなく**過剰 deny**として現れる）。

    managed 側（:func:`record_open_entry`）と違い ``round`` / ``handoff_path`` を
    **推測せず marker の値で埋める**（FR-W4 の完全化）。台帳の書込失敗は dispatch を
    止めない（fail-open）＝managed 側と同じ扱い。
    """
    if isinstance(ack, CodexIsolationOnlyAck):
        # Codex の prepare-only open を返す。actual identity を観測していないこの段で
        # running や回収可能と推測しない。
        return {"entry_id": ack.ledger_entry_id, "error": None, "platform": "codex"}
    try:
        root = worktree_ledger.main_worktree_root(
            Path.cwd() if repo_root is None else Path(repo_root)
        )
        entry_id = worktree_ledger.open_entry(
            root,
            issue=ack.issue,
            agent_type=ack.agent_type,
            round=ack.round,
            branch_name=ack.branch_name,
            handoff_path=ack.handoff_path,
            now=now,
        )
        return {"entry_id": entry_id, "error": None}
    except worktree_ledger.LedgerError as exc:
        return {"entry_id": None, "error": exc.reason, "detail": exc.detail}
    except Exception as exc:
        return {"entry_id": None, "error": type(exc).__name__}
