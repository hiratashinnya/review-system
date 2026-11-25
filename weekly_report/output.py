"""Write one report bundle to a new directory, outside the checkout."""

from . import render, snapshot
from .report_evidence import chat_summary
from .worktree_output import destination


def write(data, analysis, location, root):
    documents = {
        "snapshot.json": snapshot.dumps(data),
        "report.html": render.report(data, analysis),
        "summary.txt": chat_summary(data, analysis),
    }
    directory = destination(location, root)
    created = []
    try:
        for name, content in documents.items():
            path = directory / name
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except (OSError, UnicodeError):
        for path in created:
            path.unlink()
        directory.rmdir()
        raise
    return directory
