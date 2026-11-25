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


def validate(value):
    if not isinstance(value, dict) or set(value) != {"sections", "summary"}:
        raise ValueError("分析は sections と summary を指定してください")
    sections = value["sections"]
    if not isinstance(sections, dict) or set(sections) != set(SECTIONS):
        raise ValueError("分析の sections には定義された全項目を指定してください")
    if not _nonblank(value["summary"]):
        raise ValueError("分析の summary は簡潔な文字列を指定してください")
    for name, entries in sections.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"分析の {name} には1項目以上を指定してください")
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {"kind", "text", "sources"}
                    or entry["kind"] not in KINDS or not _nonblank(entry["text"])
                    or not isinstance(entry["sources"], list) or not entry["sources"]
                    or not all(_nonblank(source) for source in entry["sources"])):
                raise ValueError(f"分析の {name} に不正な項目があります")
    return value


def _nonblank(value):
    return isinstance(value, str) and bool(value.strip())
