"""Numeric values carry their measurement definition and provenance."""

def measured(value, definition, source, *, reason=None, status=None, **details):
    if status is None:
        if value is not None:
            status = "measured"
        elif details.get("denominator") == 0 or details.get("n") == 0:
            status = "not_calculable"
        else:
            status = "not_measured"
    return {"value": value, "status": status, "definition": definition, "source": source,
            "reason": reason, **details}


def count(rows, definition, dataset):
    return measured(
        None if rows is None else len(rows), definition, dataset["source"],
        reason=dataset["reason"] if rows is None else None,
        status="not_retrieved" if rows is None else None,
    )
