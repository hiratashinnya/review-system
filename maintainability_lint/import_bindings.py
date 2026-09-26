"""module scope で有効になり得る import 束縛を収集する。"""

from __future__ import annotations

import ast


def record_module_imports(node: ast.stmt, bindings: dict[str, str]) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            local = alias.asname or alias.name.split(".", 1)[0]
            bindings[local] = alias.name
        return
    if isinstance(node, ast.ImportFrom):
        if node.level or node.module is None:
            return
        for alias in node.names:
            if alias.name == "*":
                if node.module == "dataclasses":
                    bindings["dataclass"] = "dataclasses.dataclass"
                continue
            bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        return

    branches: list[list[ast.stmt]] = []
    if isinstance(node, (ast.If, ast.For, ast.While)):
        branches.extend((node.body, node.orelse))
    elif isinstance(node, ast.With):
        branches.append(node.body)
    elif isinstance(node, ast.Try):
        branches.extend((node.body, node.orelse, node.finalbody))
        branches.extend(handler.body for handler in node.handlers)
    for branch in branches:
        for statement in branch:
            record_module_imports(statement, bindings)
