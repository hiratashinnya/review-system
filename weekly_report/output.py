"""Write one report bundle to a new directory, outside the checkout."""

from . import render, snapshot
from .report_evidence import chat_summary
from .worktree_output import destination


def write(data, analysis, location, root):
    return _write({"": _documents(data, analysis)}, location, root)


def _documents(data, analysis):
    return {
        "snapshot.json": snapshot.dumps(data),
        "report.html": render.report(data, analysis),
        "summary.txt": chat_summary(data, analysis),
    }


def write_batch(results, location, root):
    documents, entries, index = {}, [], []
    for data in results:
        name = "week-" + data["period"]["start"][:10]
        link = None
        if data.get("status") != "not_arrived":
            documents[name] = _documents(data, None)
            link = name + "/report.html"
        entries.append((data, link))
        index.append({"period": data["period"], "report": link, "status": data.get("status", "generated"),
                      "reason": data.get("reason")})
    documents[""] = {"index.json": snapshot.dumps({"schema_version": snapshot.SCHEMA_VERSION,
                                                  "repository": results[0]["repository"], "weeks": index}),
                     "index.html": render.batch_report(entries)}
    return _write(documents, location, root)


def _write(groups, location, root):
    directory = destination(location, root)
    created = []
    subdirectories = []
    try:
        for group, documents in groups.items():
            child = directory / group
            if group:
                child.mkdir()
                subdirectories.append(child)
            for name, content in documents.items():
                path = child / name
                with path.open("x", encoding="utf-8") as stream:
                    created.append(path)
                    stream.write(content)
    except (OSError, UnicodeError):
        for path in created:
            path.unlink()
        for child in subdirectories:
            child.rmdir()
        directory.rmdir()
        raise
    return directory
