"""Transactional session state and metadata-only audit, safe across processes."""
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .audit_store import initialize, append


@contextmanager
def session_state(directory, session_id, retention=10000):
    directory = Path(directory).expanduser()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    database = directory / "state.sqlite3"
    fd = os.open(database, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    connection = sqlite3.connect(database, timeout=30)
    connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT)")
    initialize(connection)
    connection.commit()
    connection.execute("BEGIN IMMEDIATE")
    key = hashlib.sha256(session_id.encode()).hexdigest()
    row = connection.execute("SELECT data FROM sessions WHERE id=?", (key,)).fetchone()
    state = json.loads(row[0]) if row else {"calls": {}, "results": {}, "blocks": {}, "replays": {}}
    try:
        yield state, lambda record: append(connection, record, key, state, retention)
        state["calls"], state["results"] = {}, {}
        connection.execute("INSERT OR REPLACE INTO sessions VALUES (?,?)", (key, json.dumps(state)))
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
