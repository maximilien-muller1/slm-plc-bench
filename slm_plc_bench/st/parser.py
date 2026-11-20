"""Recursive-descent parser for the Structured Text subset.

Supported:
  FUNCTION_BLOCK with VAR_INPUT / VAR_OUTPUT / VAR sections
  types BOOL, INT, DINT, REAL, TIME and the standard blocks TON, R_TRIG
  assignments, IF / ELSIF / ELSE, function block calls with named arguments
  operators (lowest to highest precedence):
    OR, XOR, AND (&), = <>, < > <= >=, + -, * / MOD, unary NOT and -
"""

from __future__ import annotations

from . import ast
from .lexer import STError, Token, tokenize

TYPES = {"BOOL", "INT", "DINT", "REAL", "TIME", "TON", "R_TRIG"}
SECTIONS = {"VAR_INPUT", "VAR_OUTPUT", "VAR"}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ---------- helpers ----------

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def _is(self, kind: str, value: object = None) -> bool:
        token = self.current
        return token.kind == kind and (value is None or token.value == value)

    def _accept(self, kind: str, value: object = None) -> Token | None:
        if self._is(kind, value):
            token = self.current
            self.pos += 1
            return token
        return None

    def _expect(self, kind: str, value: object = None, what: str | None = None) -> Token:
        token = self._accept(kind, value)
        if token is None:
            wanted = what or (repr(value) if value is not None else kind)
            found = self.current.value if self.current.kind != "EOF" else "end of code"
            raise STError("parse", f"expected {wanted}, found {found!r}", self.current.line)
        return token

    # ---------- declarations ----------

    def parse_function_block(self) -> ast.FunctionBlock:
        self._expect("KW", "FUNCTION_BLOCK")
        name = self._expect("IDENT", what="a function block name").value
        fb = ast.FunctionBlock(name=name)
        while self.current.kind == "KW" and self.current.value in SECTIONS:
            self._parse_var_section(fb)
        fb.body = self._parse_statements(stop={"END_FUNCTION_BLOCK"})
        self._expect("KW", "END_FUNCTION_BLOCK")
        self._accept("OP", ";")
        if not self._is("EOF"):
            raise STError("parse", "only one FUNCTION_BLOCK is expected", self.current.line)
        return fb

    def _parse_var_section(self, fb: ast.FunctionBlock) -> None:
        section = self._expect("KW").value
        while not self._accept("KW", "END_VAR"):
            first = self._expect("IDENT", what="a variable name or END_VAR")
            names = [first]
            while self._accept("OP", ","):
                names.append(self._expect("IDENT", what="a variable name"))
            self._expect("OP", ":")
            type_token = self._expect("KW", what="a type")
            if type_token.value not in TYPES:
                raise STError("parse", f"unknown type {type_token.value}", type_token.line)
            init = self._parse_expression() if self._accept("OP", ":=") else None
            self._expect("OP", ";")
            for token in names:
                if token.value in fb.decls:
                    raise STError("semantic", f"variable {token.value} declared twice", token.line)
                fb.decls[token.value] = ast.VarDecl(token.value, type_token.value, section, init, token.line)

    # ---------- statements ----------

    def _parse_statements(self, stop: set[str]) -> list:
        statements = []
        while not (self.current.kind == "KW" and self.current.value in stop):
            if self._is("EOF"):
                raise STError("parse", f"missing {' / '.join(sorted(stop))}", self.current.line)
            if self._accept("OP", ";"):  # empty statement
                continue
            statements.append(self._parse_statement())
        return statements

    def _parse_statement(self):
        if self._is("KW", "IF"):
            return self._parse_if()
        name_token = self._expect("IDENT", what="a statement")
        if self._accept("OP", ":="):
            value = self._parse_expression()
            self._expect("OP", ";", what="';' at the end of the assignment")
            return ast.Assign(name_token.value, value, name_token.line)
        if self._accept("OP", "("):
            args = {}
            if not self._accept("OP", ")"):
                while True:
                    param = self._expect("IDENT", what="a parameter name").value
                    self._expect("OP", ":=", what="':=' (use named arguments, e.g. IN := x)")
                    args[param] = self._parse_expression()
                    if self._accept("OP", ")"):
                        break
                    self._expect("OP", ",")
            self._expect("OP", ";", what="';' after the call")
            return ast.Call(name_token.value, args, name_token.line)
        if self._is("OP", "="):
            raise STError("parse", "use ':=' for assignment, '=' is a comparison", self.current.line)
        raise STError("parse", f"expected ':=' or '(' after {name_token.value}", self.current.line)

    def _parse_if(self) -> ast.If:
        line = self._expect("KW", "IF").line
        branches = []
        condition = self._parse_expression()
        self._expect("KW", "THEN")
        branches.append((condition, self._parse_statements(stop={"ELSIF", "ELSE", "END_IF"})))
        else_body = None
        while True:
            if self._accept("KW", "ELSIF"):
                condition = self._parse_expression()
                self._expect("KW", "THEN")
                branches.append((condition, self._parse_statements(stop={"ELSIF", "ELSE", "END_IF"})))
            elif self._accept("KW", "ELSE"):
                else_body = self._parse_statements(stop={"END_IF"})
            else:
                break
        self._expect("KW", "END_IF")
        self._accept("OP", ";")
        return ast.If(branches, else_body, line)

    # ---------- expressions ----------

    def _parse_expression(self):
        return self._parse_binary(0)

    # one entry per precedence level, lowest first
    _LEVELS = [
        {("KW", "OR")},
        {("KW", "XOR")},
        {("KW", "AND"), ("OP", "&")},
        {("OP", "="), ("OP", "<>")},
        {("OP", "<"), ("OP", ">"), ("OP", "<="), ("OP", ">=")},
        {("OP", "+"), ("OP", "-")},
        {("OP", "*"), ("OP", "/"), ("KW", "MOD")},
    ]

    def _parse_binary(self, level: int):
        if level == len(self._LEVELS):
            return self._parse_unary()
        left = self._parse_binary(level + 1)
        while (self.current.kind, self.current.value) in self._LEVELS[level]:
            token = self.current
            self.pos += 1
            op = "AND" if token.value == "&" else token.value
            right = self._parse_binary(level + 1)
            left = ast.Binary(op, left, right, token.line)
        return left

    def _parse_unary(self):
        token = self.current
        if self._accept("KW", "NOT"):
            return ast.Unary("NOT", self._parse_unary(), token.line)
        if self._accept("OP", "-"):
            return ast.Unary("-", self._parse_unary(), token.line)
        return self._parse_primary()

    def _parse_primary(self):
        token = self.current
        if self._accept("KW", "TRUE"):
            return ast.Literal(True, "BOOL", token.line)
        if self._accept("KW", "FALSE"):
            return ast.Literal(False, "BOOL", token.line)
        if token.kind in ("INT", "REAL", "TIME"):
            self.pos += 1
            return ast.Literal(token.value, token.kind, token.line)
        if self._accept("OP", "("):
            inner = self._parse_expression()
            self._expect("OP", ")")
            return inner
        if self._accept("IDENT"):
            if self._accept("OP", "."):
                member = self._expect("IDENT", what="a member name").value
                return ast.MemberRef(token.value, member, token.line)
            if self._is("OP", "("):
                raise STError("parse", f"call {token.value}(...) as a statement, then read its outputs (e.g. {token.value}.Q)", token.line)
            return ast.VarRef(token.value, token.line)
        found = token.value if token.kind != "EOF" else "end of code"
        raise STError("parse", f"expected an expression, found {found!r}", token.line)


def parse(source: str) -> ast.FunctionBlock:
    """Parse ST source code into a FunctionBlock (raises STError)."""
    return Parser(tokenize(source)).parse_function_block()
