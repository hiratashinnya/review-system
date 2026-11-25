"""Numeric values carry their measurement definition and provenance."""

def measured(value, definition, source, *, reason=None, **details):
    return {"value": value, "definition": definition, "source": source,
            "reason": reason, **details}


def count(rows, definition, dataset):
    return measured(
        None if rows is None else len(rows), definition, dataset["source"],
        reason=dataset["reason"] if rows is None else None,
    )
