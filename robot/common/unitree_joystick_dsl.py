"""
Joystick DSL (Domain Specific Language) for Unitree Robotics Joystick
(Python port of unitree_joystick_dsl.hpp)

This DSL allows users to define complex joystick button combinations and
interactions in a human-readable format. It supports logical expressions
combining button states with AND (+), OR (|), NOT (!), and parentheses.

Example expressions:

--- Basic ---
- "A"                  # A is pressed
- "A.on_pressed"       # A is just pressed (single frame trigger)
- "A.on_released"      # A is just released (single frame trigger)

--- Multi-key Combinations ---
- "A+B"                # A and B are pressed simultaneously
- "RB+X.on_pressed"    # RB is pressed + X is just pressed

--- Directional Key Combinations ---
- "up+right"           # Up and right directions are pressed simultaneously (diagonal)

--- Long Press Detection ---
- "LT(2s) + up"        # LT is pressed for more than 2 seconds and up is pressed
- "LT(3s).pressed"     # Equivalent to above (explicitly specifying .pressed)

--- Multi-condition OR ---
- "X|Y"                # Either X or Y is pressed
- "A.on_pressed|B.on_pressed"  # Either A or B is just pressed

--- Logical NOT ---
- "!A + B"             # A is not pressed and B is pressed
- "!(A + B)"           # A and B are not pressed simultaneously
- "!LT(1s)"            # LT is not pressed for 1 second (i.e., LT.pressed_time < 1 or not pressed)

--- Nested Grouping ---
- "(A + B) | (X + Y)"  # A+B or X+Y is satisfied
- "!(A + B | X)"       # A+B or X is not allowed

--- Mixed Directions and Buttons ---
- "LT + up.on_pressed" # LT is pressed + up is just pressed

--- Multi-level Complex Combinations ---
- "((LT(1s) + up) | (RB + X.on_pressed)) + !Y"
  # LT long press + up or RB + X trigger, while Y is not pressed

--- Axes and Trigger Keys ---
- "LX + LY"            # Left joystick exceeds threshold in any direction
- "RX(1s) + B"         # Right joystick holds beyond threshold for 1s + B is pressed

--- Start/Exit Actions ---
- "start.on_pressed"   # Start button is just pressed
- "back.on_pressed"    # Back button is just pressed
- "!start + !back"     # Neither is pressed (commonly used for "idle state")

--- Combined Long Press Actions (Complex Example) ---
- "(LT(2s) + RT(2s)) + A"
  # LT and RT are both long pressed for more than 2 seconds, and A is pressed
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict


# ======================== Key State ========================

class KeyBase:
    """State of a single joystick key (mirrors the C++ ``KeyBase``).

    ``pressed``, ``on_pressed``, ``on_released`` and ``pressed_time`` are
    expected to be maintained by the caller (e.g. from the joystick driver).
    """

    __slots__ = ("pressed", "on_pressed", "on_released", "pressed_time")

    def __init__(self) -> None:
        self.pressed: bool = False
        self.on_pressed: bool = False
        self.on_released: bool = False
        self.pressed_time: float = 0.0


class UnitreeJoystick:
    """Joystick state container holding every key supported by the DSL."""

    def __init__(self) -> None:
        self.back = KeyBase()
        self.start = KeyBase()
        self.LS = KeyBase()
        self.RS = KeyBase()
        self.LB = KeyBase()
        self.RB = KeyBase()
        self.A = KeyBase()
        self.B = KeyBase()
        self.X = KeyBase()
        self.Y = KeyBase()
        self.up = KeyBase()
        self.down = KeyBase()
        self.left = KeyBase()
        self.right = KeyBase()
        self.F1 = KeyBase()
        self.F2 = KeyBase()
        self.lx = KeyBase()
        self.ly = KeyBase()
        self.rx = KeyBase()
        self.ry = KeyBase()
        self.LT = KeyBase()
        self.RT = KeyBase()


# Lowercase DSL key name -> attribute name on the joystick object.
_KEY_ATTRS: Dict[str, str] = {
    "back": "back",
    "start": "start",
    "ls": "LS",
    "rs": "RS",
    "lb": "LB",
    "rb": "RB",
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "f1": "F1",
    "f2": "F2",
    "lx": "lx",
    "ly": "ly",
    "rx": "rx",
    "ry": "ry",
    "lt": "LT",
    "rt": "RT",
}


def get_key(joy: UnitreeJoystick, name: str) -> KeyBase:
    """Retrieve a :class:`KeyBase` from ``joy`` by DSL key name (case-insensitive)."""
    attr = _KEY_ATTRS.get(name.lower())
    if attr is None:
        raise ValueError("Unknown key name: " + name)
    return getattr(joy, attr)


# ======================== Lexical Analysis ========================

class TokenKind(Enum):
    IDENT = auto()
    NUMBER = auto()
    PLUS = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    DOT = auto()
    END = auto()


@dataclass
class Token:
    kind: TokenKind
    text: str = ""


class Lexer:
    def __init__(self, s: str) -> None:
        self.s = s
        self.pos = 0

    def _skip_ws(self) -> None:
        while self.pos < len(self.s) and self.s[self.pos].isspace():
            self.pos += 1

    def _ident(self) -> Token:
        start = self.pos
        while self.pos < len(self.s) and (
            self.s[self.pos].isalnum() or self.s[self.pos] == "_"
        ):
            self.pos += 1
        return Token(TokenKind.IDENT, self.s[start:self.pos])

    def _number(self) -> Token:
        # Only support numbers starting with [1-9]
        start = self.pos
        c = self.s[self.pos]
        if not ("1" <= c <= "9"):
            raise RuntimeError(
                "Expected a number starting with [1-9] near pos=" + str(self.pos)
            )
        self.pos += 1
        while self.pos < len(self.s) and self.s[self.pos].isdigit():
            self.pos += 1
        return Token(TokenKind.NUMBER, self.s[start:self.pos])

    def next(self) -> Token:
        self._skip_ws()
        if self.pos >= len(self.s):
            return Token(TokenKind.END, "")
        c = self.s[self.pos]
        if c.isalpha():
            return self._ident()
        if c.isdigit():
            return self._number()
        self.pos += 1
        if c == "+":
            return Token(TokenKind.PLUS, "+")
        if c == "|":
            return Token(TokenKind.OR, "|")
        if c == "!":
            return Token(TokenKind.NOT, "!")
        if c == "(":
            return Token(TokenKind.LPAREN, "(")
        if c == ")":
            return Token(TokenKind.RPAREN, ")")
        if c == ".":
            return Token(TokenKind.DOT, ".")
        raise RuntimeError(
            "Unexpected char: " + c + " near pos=" + str(self.pos - 1)
        )


# ======================== Abstract Syntax Tree (AST) & Semantics ========================

class Field(Enum):
    PRESSED = auto()
    ON_PRESSED = auto()
    ON_RELEASED = auto()
    HOLD_TIME_GE = auto()


@dataclass
class Atom:
    name: str = ""           # Key name: "LT" "RB" "up" ...
    field: Field = Field.PRESSED
    hold_seconds: float = 0.0  # used when field == HOLD_TIME_GE


class NodeKind(Enum):
    ATOM = auto()
    NOT = auto()
    AND = auto()
    OR = auto()


class Node:
    def __init__(
        self,
        kind: NodeKind,
        atom: Atom = None,
        lhs: "Node" = None,
        rhs: "Node" = None,
    ) -> None:
        self.kind = kind
        self.atom = atom if atom is not None else Atom()
        self.lhs = lhs  # NOT: child is in lhs; AND/OR: left
        self.rhs = rhs  # AND/OR: right


# ======================== Recursive Descent Parser ========================
# Supports: ! unary NOT; + logical AND; | logical OR; () grouping
# Atom syntax: name [ '(' number ['s'|'sec'|'secs'] ')' ] [ '.' (pressed|on_pressed|on_released) ]

class Parser:
    def __init__(self, expr: str) -> None:
        self._lexer = Lexer(expr)
        self.tok = self._lexer.next()

    def parse(self) -> Node:
        n = self._parse_or()
        if self.tok.kind != TokenKind.END:
            raise RuntimeError(
                "Trailing tokens near pos=" + str(self._lexer.pos)
            )
        return n

    def _eat(self, kind: TokenKind) -> None:
        if self.tok.kind != kind:
            raise RuntimeError(
                "Unexpected token near pos=" + str(self._lexer.pos)
            )
        self.tok = self._lexer.next()

    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self.tok.kind == TokenKind.OR:
            self._eat(TokenKind.OR)
            right = self._parse_and()
            left = Node(NodeKind.OR, lhs=left, rhs=right)
        return left

    def _parse_and(self) -> Node:
        left = self._parse_unary()
        while self.tok.kind == TokenKind.PLUS:
            self._eat(TokenKind.PLUS)
            right = self._parse_unary()
            left = Node(NodeKind.AND, lhs=left, rhs=right)
        return left

    def _parse_unary(self) -> Node:
        if self.tok.kind == TokenKind.NOT:
            self._eat(TokenKind.NOT)
            child = self._parse_unary()
            return Node(NodeKind.NOT, lhs=child)
        if self.tok.kind == TokenKind.LPAREN:
            self._eat(TokenKind.LPAREN)
            inside = self._parse_or()
            self._eat(TokenKind.RPAREN)
            return inside
        return self._parse_atom()

    def _parse_atom(self) -> Node:
        if self.tok.kind != TokenKind.IDENT:
            raise RuntimeError(
                "Expected identifier near pos=" + str(self._lexer.pos)
            )
        a = Atom(name=self.tok.text)
        self._eat(TokenKind.IDENT)

        # Optional hold duration: name '(' number ['s'|'sec'|'secs'] ')'
        if self.tok.kind == TokenKind.LPAREN:
            self._eat(TokenKind.LPAREN)
            if self.tok.kind != TokenKind.NUMBER:
                raise RuntimeError(
                    "Expected hold seconds number near pos=" + str(self._lexer.pos)
                )
            a.hold_seconds = float(self.tok.text)
            self._eat(TokenKind.NUMBER)
            # Optional unit
            if self.tok.kind == TokenKind.IDENT:
                unit = self.tok.text.lower()
                if unit in ("s", "sec", "secs"):
                    self._eat(TokenKind.IDENT)
                else:
                    raise RuntimeError(
                        "Unknown time unit '" + self.tok.text + "'; use 's'/'sec'"
                    )
            self._eat(TokenKind.RPAREN)
            a.field = Field.HOLD_TIME_GE

        # Optional explicit state
        if self.tok.kind == TokenKind.DOT:
            self._eat(TokenKind.DOT)
            if self.tok.kind != TokenKind.IDENT:
                raise RuntimeError(
                    "Expected state after '.' near pos=" + str(self._lexer.pos)
                )
            st = self.tok.text
            if st == "on_pressed":
                a.field = Field.ON_PRESSED
            elif st == "on_released":
                a.field = Field.ON_RELEASED
            elif st == "pressed":
                a.field = Field.PRESSED
            else:
                raise RuntimeError(
                    "Unknown field: " + st + " (allowed: pressed|on_pressed|on_released)"
                )
            self._eat(TokenKind.IDENT)

        return Node(NodeKind.ATOM, atom=a)


# ======================== Compile to Executable Predicate ========================

def compile_expr(node: Node) -> Callable[[UnitreeJoystick], bool]:
    """Compile an AST :class:`Node` into a predicate ``f(joy) -> bool``."""
    if node.kind == NodeKind.ATOM:
        a = node.atom

        def eval_atom(joy: UnitreeJoystick, _a: Atom = a) -> bool:
            kb = get_key(joy, _a.name)
            if _a.field == Field.PRESSED:
                return kb.pressed
            if _a.field == Field.ON_PRESSED:
                return kb.on_pressed
            if _a.field == Field.ON_RELEASED:
                return kb.on_released
            if _a.field == Field.HOLD_TIME_GE:
                return kb.pressed and (kb.pressed_time >= _a.hold_seconds)
            return False

        return eval_atom

    if node.kind == NodeKind.NOT:
        child = compile_expr(node.lhs)
        return lambda joy: not child(joy)

    if node.kind == NodeKind.AND:
        lhs = compile_expr(node.lhs)
        rhs = compile_expr(node.rhs)
        return lambda joy: lhs(joy) and rhs(joy)

    if node.kind == NodeKind.OR:
        lhs = compile_expr(node.lhs)
        rhs = compile_expr(node.rhs)
        return lambda joy: lhs(joy) or rhs(joy)

    raise RuntimeError("Invalid node kind")


def compile_dsl(expr: str) -> Callable[[UnitreeJoystick], bool]:
    """Parse ``expr`` and return a predicate ``f(joy) -> bool``."""
    return compile_expr(Parser(expr).parse())


# ======================== Demo / Self-test ========================

if __name__ == "__main__":
    joy = UnitreeJoystick()

    joy.A.pressed = True
    joy.B.pressed = False
    joy.RB.pressed = True
    joy.X.pressed = False
    joy.X.on_pressed = True
    joy.Y.pressed = False
    joy.up.pressed = True
    joy.right.pressed = True
    joy.LT.pressed = True
    joy.LT.pressed_time = 3.0
    joy.RT.pressed = False

    expressions = [
        "A",
        "A+B",
        "RB+X.on_pressed",
        "up+right",
        "LT(2s) + up",
        "X|Y",
        "!A + B",
        "!LT(1s)",
        "(A + B) | (X + Y)",
        "((LT(1s) + up) | (RB + X.on_pressed)) + !Y",
    ]

    for expr in expressions:
        print(f"{expr!r:45} -> {compile_dsl(expr)(joy)}")
