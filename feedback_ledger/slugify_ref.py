"""doc-system-v2 の slugify 参照実装を fail-close で読み込む。"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import cast

SLUGIFY_PATH = Path(__file__).resolve().parents[1] / "doc-system-v2" / "slugify.py"


class SlugifyReferenceError(RuntimeError):
    """正本の slugify 実装を読み込めない。"""


@lru_cache(maxsize=1)
def _load_slugify() -> Callable[[str], str]:
    try:
        spec = spec_from_file_location("_feedback_ledger_doc_system_slugify", SLUGIFY_PATH)
        if spec is None or spec.loader is None:
            raise ImportError("Python の動的 import spec を作成できない")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        slugify = getattr(module, "slugify")
        if not callable(slugify):
            raise TypeError("slugify が callable でない")
        return cast(Callable[[str], str], slugify)
    except Exception as exc:
        raise SlugifyReferenceError(f"{SLUGIFY_PATH}: {exc}") from exc


def slugify_topic(topic: str) -> str:
    """正本から読み込んだ slugify を呼び出す。"""
    return _load_slugify()(topic)
