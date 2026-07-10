"""Import helper for the archived v1-legacy docidx package (``archive/docidx-v1/``).

issue #172 moved the v1-legacy-only ``docidx/`` package (minus ``nodeyaml.py``, which is
now ``dsv2/nodeyaml.py``) to ``archive/docidx-v1/`` to reduce mistaken-invocation risk during
v2 work. The directory name contains a hyphen (matches the existing ``archive/backref-v1/``
convention), so it cannot be named in a dotted ``import`` statement (``import archive.docidx-v1``
is a syntax error), but ``importlib.import_module()`` accepts arbitrary module-name strings and
resolves the hyphenated segment just fine — this helper centralizes that string-based import so
each test file does not need to repeat it.
"""

from __future__ import annotations

import importlib
from types import ModuleType

_PACKAGE = "archive.docidx-v1"


def import_docidx_v1(submodule: str = "") -> ModuleType:
    """Import ``archive.docidx-v1`` or one of its submodules (e.g. ``"scan"``, ``"model"``).

    Must be called with the repo root on ``sys.path`` (true by default when tests are run via
    ``python3 -m unittest discover -s tests -p "test_*.py"`` from the repo root).
    """
    name = f"{_PACKAGE}.{submodule}" if submodule else _PACKAGE
    return importlib.import_module(name)
