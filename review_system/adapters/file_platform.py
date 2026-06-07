"""findings JSON を読む PlatformPort 実装（PF 駆動 MVP の実体）。design/04・DD8。

Claude（LLM 役）が L1 出力スキーマで書いた findings.json を読み、ドメイン型へ。
schema 不適合は ❓未分類化せず、ここでは素直にパースだけ（検証は core/triage）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ..domain.ids import RuleId, Location, LineRange
from ..domain.review import Finding, UnmatchedFinding, SuggestedFix
from ..ports.platform import PlatformCapabilities, RawReviewResponse


class FilePlatformAdapter:
    def __init__(self, findings_path: Path, model_id: str = "claude-code") -> None:
        self._path = findings_path
        self._model = model_id

    def capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(True, False, False, self._model, "claude-code")

    def review(self, pack, targets, references) -> RawReviewResponse:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        findings = tuple(_finding(d) for d in data.get("findings", []))
        unmatched = tuple(_unmatched(d) for d in data.get("unmatched", []))
        return RawReviewResponse(findings, unmatched)


def _location(d: dict) -> Location:
    loc = d["location"]
    lr = loc.get("line_range")
    return Location(Path(loc["file"]), LineRange(lr[0], lr[1]) if lr else None)


def _fix(d: dict | None) -> SuggestedFix | None:
    return SuggestedFix(d["description"], d["diff"]) if d else None


def _finding(d: dict) -> Finding:
    return Finding(RuleId(d["rule_id"]), _location(d), d.get("rationale", ""),
                   d.get("quote"), _fix(d.get("suggested_fix")))


def _unmatched(d: dict) -> UnmatchedFinding:
    return UnmatchedFinding(d.get("description", ""), _location(d), _fix(d.get("suggested_fix")))
