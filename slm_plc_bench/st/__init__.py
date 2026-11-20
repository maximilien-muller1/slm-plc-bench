"""A small, dependency-free simulator for a subset of IEC 61131-3 Structured Text.

It replaces a vendor compiler during prototyping so that the benchmark can
check generated code (does it compile?) and run functional tests on it
(does it do the right thing?) on any machine.
"""

from .lexer import STError
from .parser import parse
from .runtime import Simulator
from .semantic import check

__all__ = ["STError", "parse", "check", "Simulator", "compile_st"]


def compile_st(source: str):
    """Parse and statically check ST source; return the FunctionBlock AST."""
    fb = parse(source)
    check(fb)
    return fb
