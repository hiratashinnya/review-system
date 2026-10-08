"""Content-only records returned by the time fixture scanners."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    name: str
    value: str
    status: str  # "protected" | "violation" | "allowlisted" | "no_consumer"
    detail: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def violations(self) -> list[Finding]:
        return [f for f in self.findings if f.status in ("violation", "no_consumer")]
