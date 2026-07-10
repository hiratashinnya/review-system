"""Minimal scalar-only frontmatter reader for `SKILL.md` / agent `*.md` files.

This is intentionally **not** a general YAML parser. It only needs to read flat
`key: value` scalar lines from the first ``---``…``---`` block — including hyphenated
keys like ``disable-model-invocation`` and ``user-invocable`` that this repo's existing
mini-YAML parser (``review_system.parsing.frontmatter``, key regex ``[a-z_][a-z0-9_]*``)
cannot parse. Building a second one here (rather than extending the shared one) avoids
touching production parsing code owned by the code-review-criteria domain for an
unrelated asset-tooling need.

Values are returned as raw strings (surrounding matching quotes stripped). Multi-line
values, lists, and nested mappings are not needed for the keys this tool reads
(``name``, ``description``, ``disable-model-invocation``, ``user-invocable``, ``tools``,
``model``) and are simply ignored line-by-line (best-effort, not fail-close — this tool
only *reads* frontmatter, it never writes it).
"""

from __future__ import annotations


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Return the first ``---``…``---`` block as a flat ``{key: value}`` dict.

    Returns ``None`` if the file has no frontmatter block at all (no leading ``---``
    or no closing ``---``) — callers should treat that as "not an asset with a
    recognizable frontmatter contract" rather than an error (some `.claude/agents/*.md`
    files are shared reference docs, not real subagent definitions).
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return None

    result: dict[str, str] = {}
    for line in lines[i + 1:]:
        if line.strip() == "---":
            return result
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue  # list item / continuation line — not a scalar key we need
        key, _, value = line.partition(":")
        key = key.strip()
        if not key or " " in key:
            continue  # not a top-level `key:` line (e.g. indented list under a key)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key] = value
    return None  # unterminated block — no closing `---`
