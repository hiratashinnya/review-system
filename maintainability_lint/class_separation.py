"""データクラスと具体ロジッククラスのファイル分離を検査する。"""

from __future__ import annotations

import ast
from pathlib import Path

from .model import Finding


RULE = "data-and-logic-class-cohabitation"


def _ends_with_name(node: ast.expr, suffix: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id.endswith(suffix)
    if isinstance(node, ast.Attribute):
        return node.attr.endswith(suffix)
    return False


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if _ends_with_name(target, "dataclass"):
            return True
    return False


def _is_exception(node: ast.ClassDef) -> bool:
    return any(
        _ends_with_name(base, "Error") or _ends_with_name(base, "Exception")
        for base in node.bases
    )


def _method_has_logic(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = list(method.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    inert = (ast.Pass,)
    for statement in body:
        if isinstance(statement, inert):
            continue
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if statement.value.value is Ellipsis:
                continue
        if isinstance(statement, ast.Raise) and isinstance(statement.exc, ast.Call):
            if _ends_with_name(statement.exc.func, "NotImplementedError"):
                continue
        return True
    return False


def _class_roles(path: Path) -> tuple[list[ast.ClassDef], list[ast.ClassDef]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    data_classes = [node for node in classes if _is_dataclass(node)]
    logic_classes = [
        node
        for node in classes
        if node not in data_classes
        and not _is_exception(node)
        and any(
            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and _method_has_logic(item)
            for item in node.body
        )
    ]
    return data_classes, logic_classes


def inspect_class_separation(
    root: Path,
    path: Path,
    baseline_mixed: dict[str, dict[str, list[str]]],
) -> tuple[list[Finding], dict[str, dict[str, list[str]]]]:
    data_classes, logic_classes = _class_roles(path)
    if not data_classes or not logic_classes:
        return [], {}
    relative = path.relative_to(root).as_posix()
    roles = {
        "data": sorted(node.name for node in data_classes),
        "logic": sorted(node.name for node in logic_classes),
    }
    status = "accepted-debt" if baseline_mixed.get(relative) == roles else "violation"
    detail = f"data={roles['data']} logic={roles['logic']}; place data and behavior in separate files"
    line = min(node.lineno for node in data_classes + logic_classes)
    return [Finding(RULE, relative, line, status, detail, relative)], {relative: roles}
