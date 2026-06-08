"""DS1 基準/ポリシーファイルのローダ（filesystem・read-only）。design/05。

criteria の .md：フロントマター（自前パーサ）＝メタ、本文 `## <id> — <title>` セクション＝guidance。
policy の .yaml：matrix（det→{severity:mode}）＋overrides を PolicyMatrix へ。
MVP は org スコープのみ（team/project 継承は MVP 外）。
"""
from __future__ import annotations

from pathlib import Path

from ..domain.enums import (
    DocumentType, Determinism, Severity, OverrideRule, ApplicationMode, InheritanceLayer,
)
from ..domain.ids import RuleId, Provenance, Scope
from ..domain.criteria import RuleMeta, RuleGuidance, ComposedRule
from ..domain.policy import PolicyMatrix
from ..parsing.frontmatter import parse_frontmatter

_SEVERITY = {"error": Severity.ERROR, "warning": Severity.WARNING, "info": Severity.INFO}
_LAYER = {"org": InheritanceLayer.ORG, "team": InheritanceLayer.TEAM, "project": InheritanceLayer.PROJECT}


def load_criteria_file(path: Path) -> tuple[ComposedRule, ...]:
    """1つの基準 .md を ComposedRule 群に読む。"""
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text, is_markdown=True)
    sections = _extract_sections(_body_after_frontmatter(text))
    layer = _layer_of(fm.get("scope"))
    rules: list[ComposedRule] = []
    for r in fm.get("rules") or []:
        rid = RuleId(r["id"])
        meta = RuleMeta(
            determinism=Determinism(r["determinism"]),
            severity=_SEVERITY[r["severity"]],
            override=OverrideRule(r["override"]),
            enabled=bool(r.get("enabled", True)),
        )
        guidance = RuleGuidance(sections.get(r["id"], ""), (), (), ())
        rules.append(ComposedRule(rid, r.get("title", r["id"]), guidance, meta,
                                  Provenance(path, layer)))
    return tuple(rules)


def load_policy_file(path: Path) -> PolicyMatrix:
    """policy .yaml を PolicyMatrix（det→{severity:mode}＋overrides）に読む。"""
    fm = parse_frontmatter(path.read_text(encoding="utf-8"), is_markdown=False)
    matrix: dict[Determinism, dict[str, ApplicationMode]] = {}
    for det_token, row in (fm.get("matrix") or {}).items():
        matrix[Determinism(det_token)] = {
            sev: ApplicationMode(mode) for sev, mode in row.items()
        }
    overrides = {
        RuleId(o["rule"]): ApplicationMode(o["mode"]) for o in (fm.get("overrides") or [])
    }
    return PolicyMatrix(matrix, overrides)


def discover_criteria(
    criteria_dir: Path, doc_type: DocumentType, scope: Scope
) -> tuple[ComposedRule, ...]:
    """ディレクトリ内の同 doc_type の基準ファイルを union（MVP は org のみ）。"""
    found: list[ComposedRule] = []
    for path in sorted(criteria_dir.glob("*.md")):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"), is_markdown=True)
        # doc_type ＋ scope の両方で絞る（#8：同 dir の別 scope 混入を防ぐ。MVP は org 限定）。
        if fm.get("doc_type") == doc_type.value and _layer_of(fm.get("scope")) is scope.layer:
            found.extend(load_criteria_file(path))
    return tuple(found)


def _body_after_frontmatter(text: str) -> str:
    """先頭 `---`…`---` の後ろ（本文）を返す。"""
    lines = text.splitlines()
    fences = [i for i, ln in enumerate(lines) if ln.strip() == "---"]
    if len(fences) >= 2:
        return "\n".join(lines[fences[1] + 1:])
    return ""


def _extract_sections(body: str) -> dict[str, str]:
    """`## <id> — <title>` 見出しごとに本文を抽出（id は em ダッシュ前の語）。"""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            head = line[3:].strip()
            current = head.split("—")[0].strip().split()[0] if head else None
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _layer_of(scope_token: object) -> InheritanceLayer:
    if isinstance(scope_token, str):
        return _LAYER.get(scope_token.split(":", 1)[0], InheritanceLayer.ORG)
    return InheritanceLayer.ORG
