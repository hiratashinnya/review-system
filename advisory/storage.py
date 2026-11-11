"""CAS and atomic single-file update under a repository-local writer lock."""

import hashlib
import os
import tempfile
from pathlib import Path

from .audit import seal_last_event
from .catalog import check_catalog, load_catalog
from .gitbase import base_for_write, compare_to_base
from .paths import WRITER_TEMP_PREFIX, directory, record_path, writer_lock
from .records import validate_record
from .serialization import render


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(root: Path, entry: dict, *, expected_sha256: str | None,
         base_ref: str) -> str:
    root = Path(root).resolve()
    with writer_lock(root):
        catalog = load_catalog(root)
        errors = check_catalog(catalog)
        drift, remote = compare_to_base(root, catalog, base_ref)
        if errors or drift:
            raise ValueError("; ".join(errors + drift))
        path = record_path(root, entry["id"])
        current = path.read_bytes() if path.exists() else None
        if expected_sha256 is None and current is not None:
            raise ValueError("advisory already exists")
        if expected_sha256 is not None and (
                current is None or sha(current) != expected_sha256):
            raise ValueError("lost update: expected sha256 mismatched")
        if current is not None:
            entry["base_sha256"] = base_for_write(
                root, base_ref, entry["id"], current, entry["base_sha256"])
        elif entry["id"] in remote:
            raise ValueError("advisory ID exists on base branch")
        if entry["id"] in remote:
            raise ValueError("cannot create duplicate advisory on base")
        seal_last_event(entry)
        catalog[entry["id"]] = entry
        local_errors = check_catalog(catalog)
        if local_errors:
            raise ValueError("; ".join(local_errors))
        combined = {**remote, **catalog}
        errors = check_catalog(combined)
        if errors:
            raise ValueError("; ".join(errors))
        body = render(entry)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                     prefix=WRITER_TEMP_PREFIX, dir=directory(root), delete=False) as out:
                temporary = out.name
                out.write(body)
                out.flush()
                os.fsync(out.fileno())
            if path.is_symlink():
                raise ValueError("symlink appeared during write")
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return sha(body.encode("utf-8"))
