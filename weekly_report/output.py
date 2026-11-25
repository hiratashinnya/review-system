"""Write one report bundle to a new directory, outside the checkout."""

from pathlib import Path
from tempfile import mkdtemp

from . import render, snapshot
from .report_evidence import chat_summary


def write(data, analysis, location, root):
    documents = {
        "snapshot.json": snapshot.dumps(data),
        "report.html": render.report(data, analysis),
        "summary.txt": chat_summary(data, analysis),
    }
    if location is None:
        destination = Path(mkdtemp(prefix="weekly-report-")).resolve()
        if destination.is_relative_to(root):
            destination.rmdir()
            raise ValueError("一時出力先が作業ツリー内です。作業ツリー外の --out を指定してください")
    else:
        requested = Path(location).absolute()
        destination = requested.parent.resolve() / requested.name
        if destination.is_relative_to(root):
            raise ValueError("--out は作業ツリーの外を指定してください")
        destination.mkdir()
    created = []
    try:
        for name, content in documents.items():
            path = destination / name
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except (OSError, UnicodeError):
        for path in created:
            path.unlink()
        destination.rmdir()
        raise
    return destination
