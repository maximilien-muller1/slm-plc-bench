"""Abstract syntax tree for the Structured Text subset."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------- expressions ----------

@dataclass
class Literal:
    value: object
    type: str  # "BOOL", "INT", "REAL", "TIME"
    line: int


@dataclass
class VarRef:
    name: str
    line: int


@dataclass
class MemberRef:  # e.g. Tempo.Q
    instance: str
    member: str
    line: int


@dataclass
class Unary:
    op: str  # "NOT" or "-"
    operand: object
    line: int


@dataclass
class Binary:
    op: str
    left: object
    right: object
    line: int


# ---------- statements ----------

@dataclass
class Assign:
    target: str
    value: object
    line: int


@dataclass
class If:
    branches: list  # list of (condition, list_of_statements)
    else_body: list | None
    line: int


@dataclass
class Call:  # e.g. Tempo(IN := x, PT := T#5S);
    instance: str
    args: dict  # parameter name -> expression
    line: int


# ---------- declarations ----------

@dataclass
class VarDecl:
    name: str
    type: str
    section: str  # "VAR_INPUT", "VAR_OUTPUT", "VAR"
    init: object | None
    line: int


@dataclass
class FunctionBlock:
    name: str
    decls: dict = field(default_factory=dict)  # name -> VarDecl, in declaration order
    body: list = field(default_factory=list)
