"""P4 検証・参照除外・仕分け（純粋・副作用なし）。design/02・13 S1/S2。

検証→参照除外→仕分け の順は不変条件（S1）。仕分けは安全側（S2）：
determinism のメタが無い／matrix が当該を持たない場合は 🤖 にせず HUMAN_ONLY に倒す。
"""
from __future__ import annotations

from pathlib import Path

from ..domain.criteria import CriteriaPack, MetaIndex
from ..domain.enums import ApplicationMode
from ..domain.policy import PolicyMatrix
from ..domain.review import (
    Finding, UnmatchedFinding, TriagedFinding, TriageResult,
)

# S2 安全側デフォルト：確証が持てないものは人へ
_SAFE_DEFAULT = ApplicationMode.HUMAN_ONLY


def validate(
    findings: tuple[Finding, ...], pack: CriteriaPack
) -> tuple[tuple[Finding, ...], tuple[UnmatchedFinding, ...]]:
    """⑤ rule_id 検証（S1）。パックに在れば valid、無ければ ❓未分類へ退避（取りこぼしゼロ）。"""
    valid: list[Finding] = []
    unclassified: list[UnmatchedFinding] = []
    for f in findings:
        if pack.contains(f.rule_id):
            valid.append(f)
        else:
            unclassified.append(UnmatchedFinding(
                description=f"未知の rule_id={f.rule_id.value}: {f.rationale}",
                location=f.location,
                suggested_fix=f.suggested_fix,
            ))
    return tuple(valid), tuple(unclassified)


def exclude_reference(
    findings: tuple[Finding, ...], reference_files: set[Path]
) -> tuple[Finding, ...]:
    """参照集合に属する指摘を破棄（参照は評価しない）。判定はパスで行う。"""
    return tuple(f for f in findings if f.location.file not in reference_files)


def triage(
    findings: tuple[Finding, ...], meta_index: MetaIndex, policy: PolicyMatrix
) -> TriageResult:
    """rule_id→メタ→determinism×severity→ポリシー→mode で 🤖/✋/💬 に振り分ける。"""
    auto: list[TriagedFinding] = []
    approve: list[TriagedFinding] = []
    judge: list[TriagedFinding] = []
    for f in findings:
        mode = _resolve_mode(f, meta_index, policy)
        tf = TriagedFinding(f, mode)
        if mode is ApplicationMode.AUTO_FIX_LOG_ONLY:
            auto.append(tf)
        elif mode is ApplicationMode.AUTO_FIX_SUGGEST:
            approve.append(tf)
        else:
            judge.append(tf)
    return TriageResult(tuple(auto), tuple(approve), tuple(judge), ())


def _resolve_mode(f: Finding, meta_index: MetaIndex, policy: PolicyMatrix) -> ApplicationMode:
    meta = meta_index.get(f.rule_id)
    if meta is None:                                   # S2：メタ未宣言 → 🤖 にしない
        return _SAFE_DEFAULT
    mode = policy.resolve(meta.determinism, meta.severity, f.rule_id)
    return mode if mode is not None else _SAFE_DEFAULT  # S2：matrix 欠落 → HUMAN_ONLY
