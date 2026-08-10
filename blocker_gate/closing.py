"""PR merge で default branch へ届く message と closing Issue を決定する。"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from .model import fingerprint


_KEYWORD = re.compile(
    r"(?<![A-Za-z0-9_])(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\b",
    re.ASCII | re.IGNORECASE,
)
_KEYWORD_SEPARATOR = re.compile(r"(?:\s*:\s*|\s+)")
_LOCAL_REF = re.compile(r"#([1-9][0-9]*)$")
_QUALIFIED_REF = re.compile(
    r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#([1-9][0-9]*)$"
)
_ISSUE_URL = re.compile(
    r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$"
)
_TRAILING_PUNCTUATION = ".,;:!?)]}"


class ClosingReferenceError(ValueError):
    """closing message を一意に解釈できない。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class CommitMessageSource:
    """message再構築に必要な、順序付きsource commitの完全な材料。"""

    oid: str
    message: str
    tree_oid: str
    parent_oids: tuple[str, ...]
    first_parent_tree_oid: str | None


@dataclass(frozen=True)
class DeliveredMessageBundle:
    """method別に再構築したmessageと、そのsource/result fingerprint。"""

    messages: tuple[str, ...]
    message_source_fingerprint: str
    delivered_message_fingerprint: str


def parse_closing_references(messages: Sequence[str], repository: str) -> tuple[str, ...]:
    """Policy 1.0 の closing-keyword grammar で全messageを解析する。"""
    if repository.count("/") != 1 or any(type(message) is not str for message in messages):
        raise ClosingReferenceError("CLOSING_KEYWORD_PARSE")
    references: set[str] = set()
    for message in messages:
        for match in _KEYWORD.finditer(message):
            tail = message[match.end():]
            separator = _KEYWORD_SEPARATOR.match(tail)
            if separator is None:
                continue
            tail = tail[separator.end():]
            raw = re.match(r"\S+", tail)
            if raw is None:
                continue
            token = raw.group(0).rstrip(_TRAILING_PUNCTUATION)
            parsed = _LOCAL_REF.fullmatch(token)
            if parsed is not None:
                references.add(f"{repository}#{int(parsed.group(1))}")
                continue
            parsed = _QUALIFIED_REF.fullmatch(token) or _ISSUE_URL.fullmatch(token)
            if parsed is not None:
                qualified = f"{parsed.group(1)}/{parsed.group(2)}"
                if qualified.casefold() != repository.casefold():
                    raise ClosingReferenceError("CROSS_REPOSITORY_UNSUPPORTED")
                references.add(f"{repository}#{int(parsed.group(3))}")
                continue
            lowered = token.casefold()
            looks_like_reference = (
                token.startswith("#")
                or bool(re.match(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#", token))
                or lowered.startswith("https://github.com/")
            )
            if looks_like_reference:
                raise ClosingReferenceError("CLOSING_KEYWORD_PARSE")
    return tuple(sorted(references))


def build_delivered_messages(
    *,
    repository: str,
    number: int,
    merge_method: str,
    pr_title: str,
    pr_body: str,
    head_label: str,
    commits: Sequence[CommitMessageSource],
    settings: Mapping[str, str] | None,
    commit_title: str | None,
    commit_message: str | None,
) -> DeliveredMessageBundle:
    """GitHubへ届く完全なmessage列を、Policy 1.0 のmethod表から再構築する。"""
    if merge_method not in {"merge", "rebase", "squash"}:
        raise ClosingReferenceError("MERGE_METHOD_UNKNOWN")
    if not commits:
        raise ClosingReferenceError("MESSAGE_SOURCE_INCOMPLETE")
    source = {
        "formatter_version": "github-delivered-message/1",
        "repository": repository,
        "number": number,
        "merge_method": merge_method,
        "pr_title": pr_title,
        "pr_body": pr_body,
        "head_label": head_label,
        "settings": dict(sorted(settings.items())) if settings is not None else None,
        "commit_title_override": commit_title,
        "commit_message_override": commit_message,
        "commits": [
            {
                "oid": item.oid,
                "message": item.message,
                "tree_oid": item.tree_oid,
                "parent_oids": list(item.parent_oids),
                "first_parent_tree_oid": item.first_parent_tree_oid,
            }
            for item in commits
        ],
    }
    if merge_method == "rebase":
        if commit_title is not None or commit_message is not None:
            raise ClosingReferenceError("MERGE_OVERRIDE_AMBIGUOUS")
        delivered: list[str] = []
        for item in commits:
            if len(item.parent_oids) > 1:
                raise ClosingReferenceError("REBASE_MESSAGE_AMBIGUOUS")
            if len(item.parent_oids) == 1 and item.first_parent_tree_oid is None:
                raise ClosingReferenceError("REBASE_MESSAGE_AMBIGUOUS")
            if item.first_parent_tree_oid == item.tree_oid:
                continue
            delivered.append(item.message)
        if not delivered:
            raise ClosingReferenceError("REBASE_MESSAGE_AMBIGUOUS")
    elif merge_method == "merge":
        if settings is None:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        title_setting = settings.get("merge_commit_title")
        body_setting = settings.get("merge_commit_message")
        if title_setting not in {"PR_TITLE", "MERGE_MESSAGE"}:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        if body_setting not in {"PR_TITLE", "PR_BODY", "BLANK"}:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        effective_title = commit_title
        if effective_title is None:
            effective_title = (
                pr_title
                if title_setting == "PR_TITLE"
                else f"Merge pull request #{number} from {head_label}"
            )
        effective_body = commit_message
        if effective_body is None:
            effective_body = {"PR_TITLE": pr_title, "PR_BODY": pr_body, "BLANK": ""}[body_setting]
        merge_message = effective_title + (f"\n\n{effective_body}" if effective_body else "")
        delivered = [item.message for item in commits] + [merge_message]
    else:
        if settings is None:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        title_setting = settings.get("squash_merge_commit_title")
        body_setting = settings.get("squash_merge_commit_message")
        if title_setting not in {"PR_TITLE", "COMMIT_OR_PR_TITLE"}:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        if body_setting not in {"PR_BODY", "COMMIT_MESSAGES", "BLANK"}:
            raise ClosingReferenceError("MERGE_SETTINGS_AMBIGUOUS")
        effective_title = commit_title
        if effective_title is None:
            if title_setting == "COMMIT_OR_PR_TITLE" and len(commits) == 1:
                effective_title = commits[0].message.splitlines()[0]
            else:
                effective_title = pr_title
        effective_body = commit_message
        if effective_body is None:
            effective_body = {
                "PR_BODY": pr_body,
                "COMMIT_MESSAGES": "\n\n".join(item.message for item in commits),
                "BLANK": "",
            }[body_setting]
        delivered = [effective_title + (f"\n\n{effective_body}" if effective_body else "")]
    messages = tuple(delivered)
    return DeliveredMessageBundle(
        messages=messages,
        message_source_fingerprint=fingerprint(source),
        delivered_message_fingerprint=fingerprint({"messages": list(messages)}),
    )
