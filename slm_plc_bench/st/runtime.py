"""Cycle-by-cycle simulation of a checked function block.

A PLC runs its program in a loop called the scan cycle:
read inputs -> execute the program once -> write outputs.
`Simulator.scan()` executes exactly one such cycle at the current
simulated time, then advances the clock by the cycle time.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ast
from .lexer import STError


@dataclass
class TonState:
    IN: bool = False
    PT: int = 0
    Q: bool = False
    ET: int = 0
    start_ms: int | None = None

    def execute(self, now_ms: int) -> None:
        """IEC 61131-3 on-delay timer: Q goes TRUE once IN has been TRUE for PT."""
        if self.IN:
            if self.start_ms is None:
                self.start_ms = now_ms
            self.ET = min(now_ms - self.start_ms, self.PT)
            self.Q = self.ET >= self.PT
        else:
            self.start_ms = None
            self.ET = 0
            self.Q = False


@dataclass
class RTrigState:
    CLK: bool = False
    Q: bool = False
    previous: bool = False

    def execute(self, now_ms: int) -> None:
        """Rising-edge detector: Q is TRUE for exactly one scan after CLK rises."""
        self.Q = self.CLK and not self.previous
        self.previous = self.CLK


_DEFAULTS = {"BOOL": False, "INT": 0, "DINT": 0, "REAL": 0.0, "TIME": 0}


class Simulator:
    def __init__(self, fb: ast.FunctionBlock, cycle_ms: int = 10):
        self.fb = fb
        self.cycle_ms = cycle_ms
        self.now_ms = 0
        self.values: dict[str, object] = {}
        self.instances: dict[str, object] = {}
        for decl in fb.decls.values():
            if decl.type == "TON":
                self.instances[decl.name] = TonState()
            elif decl.type == "R_TRIG":
                self.instances[decl.name] = RTrigState()
            else:
                initial = self._eval(decl.init) if decl.init is not None else _DEFAULTS[decl.type]
                self.values[decl.name] = self._coerce(decl.type, initial)

    # ---------- public API ----------

    def set_inputs(self, inputs: dict[str, object]) -> None:
        for name, value in inputs.items():
            key = name.upper()
            decl = self.fb.decls.get(key)
            if decl is None or decl.section != "VAR_INPUT":
                raise STError("interface", f"the function block has no input {name}")
            self.values[key] = self._coerce(decl.type, value)

    def scan(self) -> None:
        """Run one PLC cycle, then advance the simulated clock."""
        self._exec_block(self.fb.body)
        self.now_ms += self.cycle_ms

    def read(self, name: str) -> object:
        key = name.upper()
        if key not in self.values:
            raise STError("interface", f"the function block has no variable {name}")
        return self.values[key]

    # ---------- execution ----------

    def _coerce(self, type_name: str, value):
        if type_name == "BOOL":
            return bool(value)
        if type_name in ("INT", "DINT", "TIME"):
            return int(value)
        return float(value)

    def _exec_block(self, statements: list) -> None:
        for statement in statements:
            if isinstance(statement, ast.Assign):
                decl = self.fb.decls[statement.target]
                self.values[statement.target] = self._coerce(decl.type, self._eval(statement.value))
            elif isinstance(statement, ast.If):
                for condition, body in statement.branches:
                    if self._eval(condition):
                        self._exec_block(body)
                        break
                else:
                    if statement.else_body is not None:
                        self._exec_block(statement.else_body)
            elif isinstance(statement, ast.Call):
                instance = self.instances[statement.instance]
                for param, expr in statement.args.items():
                    setattr(instance, param, self._eval(expr))
                instance.execute(self.now_ms)

    def _eval(self, expr):
        if isinstance(expr, ast.Literal):
            return expr.value
        if isinstance(expr, ast.VarRef):
            return self.values[expr.name]
        if isinstance(expr, ast.MemberRef):
            return getattr(self.instances[expr.instance], expr.member)
        if isinstance(expr, ast.Unary):
            value = self._eval(expr.operand)
            return (not value) if expr.op == "NOT" else -value
        if isinstance(expr, ast.Binary):
            op = expr.op
            if op == "AND":  # short-circuit has no side effect here, it is just faster
                return bool(self._eval(expr.left)) and bool(self._eval(expr.right))
            if op == "OR":
                return bool(self._eval(expr.left)) or bool(self._eval(expr.right))
            left, right = self._eval(expr.left), self._eval(expr.right)
            if op == "XOR":
                return bool(left) != bool(right)
            if op == "=":
                return left == right
            if op == "<>":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op in ("/", "MOD"):
                if right == 0:
                    raise STError("runtime", "division by zero", expr.line)
                if op == "MOD":
                    return int(left) % int(right)
                if isinstance(left, int) and isinstance(right, int):
                    return int(left / right)  # integer division truncates toward zero in ST
                return left / right
        raise STError("runtime", f"cannot evaluate {type(expr).__name__}")
