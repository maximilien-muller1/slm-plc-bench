"""Tokenizer for the IEC 61131-3 Structured Text subset used by the benchmark.

Structured Text is case-insensitive, so keywords and identifiers are
normalised to upper case here. Every token keeps its line number so that
error messages can point the model (or the human) to the right place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class STError(Exception):
    """Any problem found while lexing, parsing, checking or running ST code.

    `stage` is one of: "parse", "semantic", "interface", "runtime".
    """

    def __init__(self, stage: str, message: str, line: int | None = None):
        self.stage = stage
        self.line = line
        self.detail = message
        location = f"line {line}: " if line else ""
        super().__init__(f"{stage} error: {location}{message}")


KEYWORDS = {
    "FUNCTION_BLOCK", "END_FUNCTION_BLOCK",
    "VAR_INPUT", "VAR_OUTPUT", "VAR", "END_VAR",
    "IF", "THEN", "ELSIF", "ELSE", "END_IF",
    "AND", "OR", "XOR", "NOT", "MOD",
    "TRUE", "FALSE",
    "BOOL", "INT", "DINT", "REAL", "TIME", "TON", "R_TRIG",
}

# Valid ST, but outside the subset this benchmark supports. We reject them
# with an explicit message rather than a confusing syntax error.
UNSUPPORTED = {
    "WHILE": "loops are not allowed: a PLC scan must never block, use timers instead",
    "FOR": "loops are not supported in this benchmark subset",
    "REPEAT": "loops are not allowed: a PLC scan must never block, use timers instead",
    "CASE": "CASE is not supported yet, use IF / ELSIF",
    "PROGRAM": "write a FUNCTION_BLOCK, not a PROGRAM",
    "FUNCTION": "write a FUNCTION_BLOCK, not a FUNCTION",
    "METHOD": "methods are not supported",
    "RETURN": "RETURN is not supported",
    "EXIT": "EXIT is not supported",
    "GOTO": "GOTO is not supported",
    "TOF": "only TON and R_TRIG are available as standard function blocks",
    "TP": "only TON and R_TRIG are available as standard function blocks",
    "CTU": "only TON and R_TRIG are available as standard function blocks",
    "F_TRIG": "only TON and R_TRIG are available as standard function blocks",
    "VAR_IN_OUT": "VAR_IN_OUT is not supported",
    "STRING": "STRING is not supported",
}


@dataclass(frozen=True)
class Token:
    kind: str  # "KW", "IDENT", "INT", "REAL", "TIME", "OP", "EOF"
    value: object
    line: int


_TIME_PART = re.compile(r"(\d+(?:\.\d+)?)(ms|d|h|m|s)", re.IGNORECASE)
_TIME_FACTORS_MS = {"d": 86_400_000, "h": 3_600_000, "m": 60_000, "s": 1_000, "ms": 1}

_TOKEN_RE = re.compile(
    r"""
    (?P<newline>\n)
  | (?P<space>[ \t\r]+)
  | (?P<block_comment>\(\*.*?\*\))
  | (?P<line_comment>//[^\n]*)
  | (?P<time>(?:TIME|T)\#-?[0-9_.a-zA-Z]+)
  | (?P<real>\d[\d_]*\.\d[\d_]*)
  | (?P<int>\d[\d_]*)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>:=|<>|<=|>=|[;:,().=<>+\-*/&])
    """,
    re.VERBOSE | re.DOTALL | re.IGNORECASE,
)


def parse_time_literal(text: str, line: int) -> int:
    """Convert `T#1m30s` / `TIME#500ms` into milliseconds."""
    body = text.split("#", 1)[1].replace("_", "")
    negative = body.startswith("-")
    body = body.lstrip("-")
    position, total = 0, 0.0
    while position < len(body):
        match = _TIME_PART.match(body, position)
        if not match:
            raise STError("parse", f"invalid time literal {text!r}", line)
        total += float(match.group(1)) * _TIME_FACTORS_MS[match.group(2).lower()]
        position = match.end()
    if position == 0:
        raise STError("parse", f"invalid time literal {text!r}", line)
    value = int(round(total))
    return -value if negative else value


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, position = 1, 0
    while position < len(source):
        match = _TOKEN_RE.match(source, position)
        if not match:
            raise STError("parse", f"unexpected character {source[position]!r}", line)
        kind, text = match.lastgroup, match.group()
        if kind == "newline":
            line += 1
        elif kind == "block_comment":
            line += text.count("\n")
        elif kind in ("space", "line_comment"):
            pass
        elif kind == "time":
            tokens.append(Token("TIME", parse_time_literal(text, line), line))
        elif kind == "real":
            tokens.append(Token("REAL", float(text.replace("_", "")), line))
        elif kind == "int":
            tokens.append(Token("INT", int(text.replace("_", "")), line))
        elif kind == "ident":
            upper = text.upper()
            if upper in UNSUPPORTED:
                raise STError("parse", f"{upper}: {UNSUPPORTED[upper]}", line)
            tokens.append(Token("KW" if upper in KEYWORDS else "IDENT", upper, line))
        else:  # operator
            tokens.append(Token("OP", text, line))
        position = match.end()
    if source.count("(*") != source.count("*)"):
        raise STError("parse", "unterminated comment (* ... *)", line)
    tokens.append(Token("EOF", None, line))
    return tokens
