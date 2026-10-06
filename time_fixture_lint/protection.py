"""Resolve clock markers for the enclosing local function scope."""
import ast
from .file_graph import _FileGraph
from .patterns import PROTECTION_MARKER_RE

def _build_graph(text: str) -> _FileGraph | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    return _FileGraph(tree, text)


def _is_protected(graph: _FileGraph | None, text: str, lineno: int) -> bool:
    if graph is not None:
        scope = graph.protection_scope_text(lineno)
        if scope is not None:
            return bool(PROTECTION_MARKER_RE.search(scope))
    # ast 解析に失敗した、またはモジュールレベル参照でスコープを絞れない場合は
    # ファイル全文へフォールバックする（既知の限界。モジュール docstring 参照）。
    return bool(PROTECTION_MARKER_RE.search(text))
