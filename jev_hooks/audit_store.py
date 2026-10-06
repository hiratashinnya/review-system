"""Audit storage assigns anonymous scope IDs and bounds rows and review retention."""
import hashlib
import json


def initialize(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS audit (record TEXT)")
    connection.execute("CREATE TABLE IF NOT EXISTS audit_metadata (name TEXT PRIMARY KEY, value INTEGER)")
    connection.execute("INSERT OR IGNORE INTO audit_metadata VALUES (?,?)",
                       ("total_records", connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0]))
    connection.execute("CREATE TABLE IF NOT EXISTS audit_reviews (record_id TEXT, rule TEXT, verdict TEXT)")


def append(connection, record, scope, state, retention):
    record = dict(record, session_id=scope,
        request_id=hashlib.sha256((scope + ":" + record["request_id"]).encode()).hexdigest(),
        turn_id=hashlib.sha256((scope + ':' + state.get("turn_key", 'unknown')).encode()).hexdigest())
    connection.execute("INSERT INTO audit VALUES (?)", (json.dumps(record),))
    connection.execute("UPDATE audit_metadata SET value=value+1 WHERE name='total_records'")
    connection.execute("INSERT OR REPLACE INTO audit_metadata VALUES (?,?)", ("retention_records", retention))
    connection.execute("DELETE FROM audit WHERE rowid NOT IN (SELECT rowid FROM audit ORDER BY rowid DESC LIMIT ?)",
                       (retention,))
    connection.execute("DELETE FROM audit_reviews WHERE record_id NOT IN (SELECT json_extract(record, '$.record_id') FROM audit)")
    return record["record_id"]
