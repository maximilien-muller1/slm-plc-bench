"""Static checks: declarations, types and use of standard function blocks.

These checks play the role of the compiler in the verification chain:
an output that passes them is counted as *valid*, even if it does not
yet do the right thing.
"""

from __future__ import annotations

from . import ast
from .lexer import STError

NUMERIC = {"INT", "DINT", "REAL"}
FB_TYPES = {
    # type -> (inputs {name: type}, outputs {name: type})
    "TON": ({"IN": "BOOL", "PT": "TIME"}, {"Q": "BOOL", "ET": "TIME"}),
    "R_TRIG": ({"CLK": "BOOL"}, {"Q": "BOOL"}),
}


def value_class(type_name: str) -> str:
    """Collapse concrete types into the classes used for type checking."""
    if type_name in NUMERIC:
        return "NUM"
    return type_name


class Checker:
    def __init__(self, fb: ast.FunctionBlock):
        self.fb = fb

    def check(self) -> None:
        for decl in self.fb.decls.values():
            if decl.type in FB_TYPES and decl.section != "VAR":
                raise STError("semantic", f"{decl.name}: declare {decl.type} instances in VAR, not {decl.section}", decl.line)
            if decl.init is not None:
                if decl.type in FB_TYPES:
                    raise STError("semantic", f"{decl.name}: function block instances cannot have an initial value", decl.line)
                self._expect_class(decl.init, value_class(decl.type), f"initial value of {decl.name}")
        self._check_block(self.fb.body)

    # ---------- statements ----------

    def _check_block(self, statements: list) -> None:
        for statement in statements:
            if isinstance(statement, ast.Assign):
                decl = self._lookup(statement.target, statement.line)
                if decl.type in FB_TYPES:
                    raise STError("semantic", f"cannot assign to function block instance {decl.name}", statement.line)
                if decl.section == "VAR_INPUT":
                    raise STError("semantic", f"cannot assign to input {decl.name}", statement.line)
                self._expect_class(statement.value, value_class(decl.type), f"assignment to {decl.name}")
            elif isinstance(statement, ast.If):
                for condition, body in statement.branches:
                    self._expect_class(condition, "BOOL", "IF condition")
                    self._check_block(body)
                if statement.else_body is not None:
                    self._check_block(statement.else_body)
            elif isinstance(statement, ast.Call):
                decl = self._lookup(statement.instance, statement.line)
                if decl.type not in FB_TYPES:
                    raise STError("semantic", f"{decl.name} is a {decl.type}, not a function block", statement.line)
                inputs, _ = FB_TYPES[decl.type]
                for param, expr in statement.args.items():
                    if param not in inputs:
                        raise STError("semantic", f"{decl.type} has no input {param} (inputs: {', '.join(inputs)})", statement.line)
                    self._expect_class(expr, inputs[param], f"{decl.name}.{param}")

    # ---------- expressions ----------

    def _lookup(self, name: str, line: int) -> ast.VarDecl:
        decl = self.fb.decls.get(name)
        if decl is None:
            raise STError("semantic", f"undeclared variable {name}", line)
        return decl

    def _expect_class(self, expr, expected: str, context: str) -> None:
        found = self.infer(expr)
        if found != expected:
            raise STError("semantic", f"type mismatch in {context}: expected {expected}, got {found}", expr.line)

    def infer(self, expr) -> str:
        if isinstance(expr, ast.Literal):
            return value_class(expr.type)
        if isinstance(expr, ast.VarRef):
            decl = self._lookup(expr.name, expr.line)
            if decl.type in FB_TYPES:
                raise STError("semantic", f"{decl.name} is a function block: read one of its outputs, e.g. {decl.name}.Q", expr.line)
            return value_class(decl.type)
        if isinstance(expr, ast.MemberRef):
            decl = self._lookup(expr.instance, expr.line)
            if decl.type not in FB_TYPES:
                raise STError("semantic", f"{decl.name} has no members", expr.line)
            inputs, outputs = FB_TYPES[decl.type]
            members = {**inputs, **outputs}
            if expr.member not in members:
                raise STError("semantic", f"{decl.type} has no member {expr.member} (outputs: {', '.join(outputs)})", expr.line)
            return value_class(members[expr.member])
        if isinstance(expr, ast.Unary):
            inner = self.infer(expr.operand)
            if expr.op == "NOT" and inner == "BOOL":
                return "BOOL"
            if expr.op == "-" and inner in ("NUM", "TIME"):
                return inner
            raise STError("semantic", f"operator {expr.op} cannot be applied to {inner}", expr.line)
        if isinstance(expr, ast.Binary):
            left, right, op = self.infer(expr.left), self.infer(expr.right), expr.op
            if op in ("AND", "OR", "XOR"):
                if left == right == "BOOL":
                    return "BOOL"
                raise STError("semantic", f"{op} needs BOOL operands, got {left} and {right}", expr.line)
            if op in ("=", "<>"):
                if left == right:
                    return "BOOL"
            elif op in ("<", ">", "<=", ">="):
                if left == right and left in ("NUM", "TIME"):
                    return "BOOL"
            elif op in ("+", "-"):
                if left == right and left in ("NUM", "TIME"):
                    return left
            elif op in ("*", "/"):
                if left == right == "NUM":
                    return "NUM"
                if left == "TIME" and right == "NUM":
                    return "TIME"
            elif op == "MOD":
                if left == right == "NUM":
                    return "NUM"
            raise STError("semantic", f"operator {op} cannot combine {left} and {right}", expr.line)
        raise STError("semantic", f"unsupported expression {type(expr).__name__}")


def check(fb: ast.FunctionBlock) -> None:
    """Raise STError if the function block is not well-formed."""
    Checker(fb).check()
