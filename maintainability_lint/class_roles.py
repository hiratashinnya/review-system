"""トップレベル class の data / logic 役割を構文木から分類する。"""

from __future__ import annotations

import ast
from pathlib import Path

from .import_bindings import record_module_imports


def _ends_with_name(node: ast.expr, suffix: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id.endswith(suffix)
    if isinstance(node, ast.Attribute):
        return node.attr.endswith(suffix)
    return False


def _is_dataclass(node: ast.ClassDef, bindings: dict[str, str]) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            if bindings.get(target.id) == "dataclasses.dataclass":
                return True
        elif isinstance(target, ast.Attribute) and target.attr == "dataclass":
            if isinstance(target.value, ast.Name):
                if bindings.get(target.value.id) == "dataclasses":
                    return True
    return False


def _is_exception(node: ast.ClassDef) -> bool:
    return any(
        _ends_with_name(base, "Error") or _ends_with_name(base, "Exception")
        for base in node.bases
    )


def _is_not_implemented_raise(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Raise) or statement.exc is None:
        return False
    target = statement.exc.func if isinstance(statement.exc, ast.Call) else statement.exc
    return isinstance(target, ast.Name) and target.id == "NotImplementedError"


def _method_has_logic(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = list(method.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    for statement in body:
        if isinstance(statement, ast.Pass) or _is_not_implemented_raise(statement):
            continue
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if statement.value.value is Ellipsis:
                continue
        return True
    return False


def classify_top_level_classes(path: Path) -> tuple[list[ast.ClassDef], list[ast.ClassDef]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    bindings: dict[str, str] = {}
    data_classes: list[ast.ClassDef] = []
    logic_classes: list[ast.ClassDef] = []
    for node in tree.body:
        record_module_imports(node, bindings)
        if isinstance(node, ast.ClassDef):
            if _is_dataclass(node, bindings):
                data_classes.append(node)
            elif not _is_exception(node) and any(
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and _method_has_logic(item)
                for item in node.body
            ):
                logic_classes.append(node)
            bindings.pop(node.name, None)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bindings.pop(node.name, None)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                    bindings.pop(child.id, None)
    return data_classes, logic_classes
