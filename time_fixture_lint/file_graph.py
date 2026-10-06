"""AST protection-scope graph; known limitations are documented in README.md."""
import ast


class _FileGraph:
    """A per-file undirected local-call graph for clock protection scopes."""

    def __init__(self, tree: ast.Module, text: str) -> None:
        self.tree = tree
        self.text = text
        self._by_name: dict[str, list[ast.AST]] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._by_name.setdefault(node.name, []).append(node)
        self._node_by_id: dict[int, ast.AST] = {
            id(n): n for nodes in self._by_name.values() for n in nodes
        }
        self._adjacency: dict[int, set[int]] = {}
        for func in self._node_by_id.values():
            for call_name in self._called_local_names(func):
                for callee in self._by_name.get(call_name, ()):
                    if callee is func:
                        continue
                    self._adjacency.setdefault(id(func), set()).add(id(callee))
                    self._adjacency.setdefault(id(callee), set()).add(id(func))

    @staticmethod
    def _called_local_names(func_node: ast.AST) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Attribute):
                    names.add(target.attr)
        return names

    def _enclosing(self, lineno: int) -> tuple[ast.AST | None, ast.ClassDef | None]:
        best_func: ast.AST | None = None
        best_class: ast.ClassDef | None = None

        def visit(node: ast.AST, classes: list[ast.ClassDef]) -> None:
            nonlocal best_func, best_class
            if isinstance(node, ast.ClassDef):
                classes = classes + [node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", None) or node.lineno
                if node.lineno <= lineno <= end:
                    best_func = node
                    best_class = classes[-1] if classes else None
            for child in ast.iter_child_nodes(node):
                visit(child, classes)

        visit(self.tree, [])
        return best_func, best_class

    def protection_scope_text(self, lineno: int) -> str | None:
        """``lineno`` を含む参照箇所の保護判定スコープ本文。
        囲み関数が見つからない（モジュールレベル参照）場合は None
        （呼び出し側でファイル全文へフォールバックさせる）。"""
        func, cls = self._enclosing(lineno)
        if func is None:
            return None

        parts: list[str] = []
        seen: set[int] = set()

        def add(node: ast.AST) -> None:
            if id(node) in seen:
                return
            seen.add(id(node))
            segment = ast.get_source_segment(self.text, node)
            if segment:
                parts.append(segment)

        add(func)
        frontier = [id(func)]
        if cls is not None:
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in (
                    "setUp",
                    "setUpClass",
                ):
                    add(item)
                    frontier.append(id(item))

        while frontier:
            current_id = frontier.pop()
            for neighbor_id in self._adjacency.get(current_id, ()):
                if neighbor_id in seen:
                    continue
                add(self._node_by_id[neighbor_id])
                frontier.append(neighbor_id)

        return "\n".join(parts)
