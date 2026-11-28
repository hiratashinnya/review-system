"""Capture existing advisory history and derive per-window events."""

from advisory.catalog import check_catalog, load_catalog
from advisory.paths import directory

from .period import parse_jst
from .quantities import measured

SOURCE = ".ai/advisory/ledger"
DEFINITIONS = {"advisories_created": "期間内に登録された Advisory",
               "advisories_closed": "期間内に closed になった Advisory の遷移"}


def capture(root):
    try:
        if not directory(root).is_dir():
            return {"source": SOURCE, "events": None, "reason": "台帳ディレクトリがありません"}
        catalog = load_catalog(root)
        if check_catalog(catalog):
            return {"source": SOURCE, "events": None, "reason": "台帳の検証に失敗しました"}
        events = [{"id": name, "topic": item["topic"], "event": event}
                  for name, item in catalog.items() for event in item["history"]]
        return {"source": SOURCE, "events": events, "reason": None, "records": len(catalog)}
    except (OSError, ValueError, TypeError) as exc:
        return {"source": SOURCE, "events": None, "reason": f"台帳を取得できません ({type(exc).__name__})"}


def measure(period, evidence):
    source = evidence["source"]
    if evidence["events"] is None:
        return {key: measured(None, text, source, reason=evidence["reason"], status="not_retrieved")
                for key, text in DEFINITIONS.items()}
    events = [row for row in evidence["events"] if period.contains(parse_jst(row["event"]["at"]))]
    selected = {
        "advisories_created": [row for row in events if row["event"]["action"] == "create"],
        "advisories_closed": [row for row in events if row["event"]["to_status"] == "closed"
                              and row["event"]["from_status"] != "closed"],
    }
    return {key: measured(len(rows), DEFINITIONS[key], source, events=rows,
                          observed_ledger_records=evidence["records"]) for key, rows in selected.items()}
