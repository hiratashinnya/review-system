"""Validate the plain-text analysis supplied by the reporting Skill."""

SECTIONS = {
    "overview": "概要・今週実現した価値",
    "delivery": "開発実績",
    "initiatives": "主要施策の進捗",
    "quality_safety": "品質・安全性",
    "maintainability": "保守性",
    "efficiency": "開発効率・自律性・滞留",
    "next_week": "次週の推奨着手順",
    "owner": "オーナー判断",
}
KINDS = {"fact": "確認事実", "inference": "推定", "recommendation": "推奨", "unmeasured": "未計測"}
OPTIONAL_SECTIONS = {"open_pulls": "オープン PR の残課題"}
CASE_CATEGORIES = {
    "planned_improvement": "計画的改善",
    "design_discovery": "設計発掘",
    "known_remaining": "既知残課題",
    "new_defect": "新規欠陥",
    "unknown": "不明",
}


def validate(value):
    if not isinstance(value, dict) or not {"sections", "summary"} <= set(value) <= {"sections", "summary", "derived_cases"}:
        raise ValueError("分析は sections と summary を指定してください")
    sections = value["sections"]
    if not isinstance(sections, dict) or not set(SECTIONS) <= set(sections) <= set(SECTIONS | OPTIONAL_SECTIONS):
        raise ValueError("分析の sections には定義された全項目を指定してください")
    if not _nonblank(value["summary"]):
        raise ValueError("分析の summary は簡潔な文字列を指定してください")
    for name, entries in sections.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"分析の {name} には1項目以上を指定してください")
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {"kind", "text", "sources"}
                    or entry["kind"] not in KINDS or not _nonblank(entry["text"])
                    or not _sources(entry["sources"])):
                raise ValueError(f"分析の {name} に不正な項目があります")
    if "derived_cases" in value:
        _validate_cases(value["derived_cases"])
    return value


def _validate_cases(cases):
    if not isinstance(cases, list):
        raise ValueError("派生事例の分類は derived_cases の配列で指定してください")
    seen = set()
    for entry in cases:
        if (not isinstance(entry, dict) or set(entry) != {"number", "category", "kind", "text", "sources"}
                or type(entry["number"]) is not int or entry["number"] <= 0 or entry["number"] in seen
                or entry["category"] not in CASE_CATEGORIES or entry["kind"] not in ("fact", "inference", "unmeasured")
                or not _nonblank(entry["text"]) or not _sources(entry["sources"])):
            raise ValueError("派生事例の分類に不正な項目があります")
        seen.add(entry["number"])


def _sources(values):
    return isinstance(values, list) and bool(values) and all(_nonblank(source) for source in values)


def _nonblank(value):
    return isinstance(value, str) and bool(value.strip())
