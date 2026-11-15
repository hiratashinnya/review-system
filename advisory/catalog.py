"""Read the sole TOML ledger and validate identities, references and audit."""

import tomllib
from pathlib import Path

from .identity import duplicate_errors
from .paths import WRITER_TEMP_PREFIX, directory
from .records import validate_record
from .serialization import render


def _writer_artifact(path: Path) -> bool:
    if path.name == ".writer.lock":
        return True
    return (path.name.startswith(WRITER_TEMP_PREFIX)
            and path.suffix != ".toml" and path.is_file()
            and not path.is_symlink())


def load_catalog(root: Path) -> dict[str, dict]:
    result = {}
    folder = directory(root)
    if not folder.exists():
        return result
    for path in sorted(folder.iterdir()):
        if _writer_artifact(path):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix != ".toml":
            raise ValueError("unexpected ledger entry: " + str(path))
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("id") != path.stem:
            raise ValueError("ledger filename/id mismatch: " + str(path))
        result[path.stem] = document
    return result


def _valid(document: dict) -> bool:
    try:
        return not validate_record(document)
    except (TypeError, ValueError, AttributeError, KeyError, IndexError):
        return False


def check_catalog(catalog: dict[str, dict], *, canonical: bool = False,
                  raw_files: dict[str, str] | None = None) -> list[str]:
    errors = []
    for key, doc in catalog.items():
        try:
            findings = validate_record(doc)
        except (TypeError, ValueError, AttributeError, KeyError, IndexError) as exc:
            findings = ["malformed schema: " + str(exc)]
        errors.extend(key + ": " + error for error in findings)
        if findings:
            continue
        if canonical and raw_files is not None and key in raw_files:
            try:
                if render(doc) != raw_files[key]:
                    errors.append(key + ": noncanonical TOML")
            except (TypeError, ValueError, KeyError) as exc:
                errors.append(key + ": cannot serialize: " + str(exc))
        for ref in doc.get("related_ids", []):
            if ref not in catalog:
                errors.append(key + ": missing related advisory: " + str(ref))
        valid_peers = {name: item for name, item in catalog.items() if name != key
                       and _valid(item)}
        errors.extend(key + ": " + error for error in duplicate_errors(doc, valid_peers))
    return sorted(set(errors))


def read_raw(root: Path) -> dict[str, str]:
    folder = directory(root)
    if not folder.exists():
        return {}
    result = {}
    for path in folder.iterdir():
        if _writer_artifact(path):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix != ".toml":
            raise ValueError("unexpected ledger entry: " + str(path))
        result[path.stem] = path.read_text(encoding="utf-8")
    return result
