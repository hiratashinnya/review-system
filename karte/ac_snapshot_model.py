"""AC identity and deterministic checksum, shared by reviewers and owner update."""
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class AC:
    text: str
    checked: bool | None
    line_number: int


def digest(items: tuple[AC, ...]) -> str:
    """Bind ordered AC text and checkbox states to a deterministic SHA-256."""
    data = [{"text": item.text, "checked": item.checked} for item in items]
    return sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
