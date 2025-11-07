from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from app.core.config import settings

ALLOWED_IMPORTS = {
    "nmc_sdk",
    "datetime",
    "json",
    "math",
    "csv",
    "io",
    "typing",
    "textwrap",
    "base64",
}

BANNED_NAMES = {"open", "__import__", "eval", "exec", "compile"}
BANNED_MODULE_PREFIXES = {"os", "sys", "subprocess", "socket", "requests", "pathlib"}


@dataclass
class Violation:
    line: int
    message: str


class PolicyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            self._check_module(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        self._check_module(module, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id in BANNED_NAMES:
            self.violations.append(Violation(node.lineno, f"Use of '{node.func.id}' is not allowed"))
        if isinstance(node.func, ast.Attribute) and node.func.attr in BANNED_NAMES:
            self.violations.append(Violation(node.lineno, f"Use of '{node.func.attr}' is not allowed"))
        if self._is_email_call(node):
            self._check_email_domains(node)
        self.generic_visit(node)

    def _check_module(self, module: str, lineno: int) -> None:
        if module not in ALLOWED_IMPORTS:
            for prefix in BANNED_MODULE_PREFIXES:
                if module.startswith(prefix):
                    self.violations.append(Violation(lineno, f"Import of module '{module}' is not allowed"))
                    return
            if module:
                self.violations.append(Violation(lineno, f"Import of module '{module}' is not allowed"))

    def _is_email_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name) and node.func.id == "email":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "email":
            return True
        return False

    def _check_email_domains(self, node: ast.Call) -> None:
        allowed = set(settings.allowed_email_domains)
        for keyword in node.keywords:
            if keyword.arg == "to":
                values = self._extract_constant_list(keyword.value)
                for value, lineno in values:
                    domain = value.split("@")[-1]
                    if domain not in allowed:
                        self.violations.append(
                            Violation(lineno, f"Email domain '{domain}' not in allowlist {sorted(allowed)}")
                        )

    def _extract_constant_list(self, node: ast.AST) -> list[tuple[str, int]]:
        results: list[tuple[str, int]] = []
        if isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    results.append((elt.value, elt.lineno))
        return results


def validate_code(code: str) -> list[str]:
    violations: list[str] = []
    if len(code) > 20000:
        violations.append("Code exceeds 20000 characters")
    if code.count("\n") + 1 > 400:
        violations.append("Code exceeds 400 lines")
    if violations:
        return violations

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:  # noqa: BLE001
        return [f"Syntax error at line {exc.lineno}: {exc.msg}"]

    visitor = PolicyVisitor()
    visitor.visit(tree)

    return [f"Line {v.line}: {v.message}" for v in visitor.violations]
