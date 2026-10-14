"""
Joystick DSL (Domain Specific Language) for Unitree Robotics Joystick
(Python port of unitree_joystick_dsl.hpp, plus the joystick state-management
features from unitree_joystick.hpp: KeyBase/Button/Axis, extract/combine)

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

import struct
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict


# ======================== Key State ========================

class KeyBase:
    """State of a single joystick key (mirrors the C++ ``KeyBase``).

    Call :meth:`update` with the raw pressed flag to maintain ``pressed``,
    ``on_pressed``, ``on_released``, ``click_cnt`` and ``pressed_time``.
    """

    __slots__ = (
        "pressed",
        "on_pressed",
        "on_released",
        "click_cnt",
        "pressed_time",
        "_last_pressed",
        "_last_click_time",
        "_double_click_threshold",
    )

    def __init__(self) -> None:
        self.pressed: bool = False
        self.on_pressed: bool = False
        self.on_released: bool = False
        self.click_cnt: int = 0
        self.pressed_time: float = 0.0
        self._last_pressed: bool = False
        self._last_click_time: float = 0.0
        self._double_click_threshold: float = 0.5  # seconds

    def update(self, is_pressed: bool) -> None:
        """Update the key state from the raw pressed flag.

        Mirrors the C++ ``KeyBase::update``: computes edge triggers, the
        click count (double-click threshold) and the hold duration.
        """
        self.pressed = bool(is_pressed)
        self.on_pressed = self.pressed and not self._last_pressed
        self.on_released = (not self.pressed) and self._last_pressed
        self._last_pressed = self.pressed

        now = time.monotonic()
        if self.on_pressed:
            if now - self._last_click_time < self._double_click_threshold:
                self.click_cnt += 1
            else:
                self.click_cnt = 1
            self._last_click_time = now

        if self.pressed:
            self.pressed_time = now - self._last_click_time
        if not (self.pressed or self.on_released):
            self.pressed_time = 0.0


class Button(KeyBase):
    """Digital button holding a raw value (mirrors the C++ ``Button<T>``).

    ``update(data)`` marks the button pressed whenever ``data`` differs from
    ``null_value``; the latest raw value is kept in :attr:`data`.
    """

    def __init__(self, null_value: int = 0) -> None:
        super().__init__()
        self.data = null_value
        self._null_value = null_value

    def update(self, data) -> None:
        super().update(data != self._null_value)
        self.data = data


class Axis(KeyBase):
    """Analog axis with deadzone and smoothing (mirrors the C++ ``Axis``).

    ``update(data)`` applies deadzone + exponential smoothing and marks the
    axis pressed when the smoothed value exceeds ``threshold``.
    """

    def __init__(
        self, threshold: float = 0.5, smooth: float = 0.03, deadzone: float = 0.01
    ) -> None:
        super().__init__()
        self.threshold = threshold
        self.smooth = smooth
        self.deadzone = deadzone
        self.data = 0.0

    def update(self, data) -> None:
        data = float(data)
        data_deadzone = 0.0 if abs(data) < self.deadzone else data
        new_data = self.data * (1.0 - self.smooth) + data_deadzone * self.smooth
        super().update(new_data > self.threshold)
        self.data = new_data


# ======================== Raw Data Types (mirrors unitree_joystick.hpp) ========================

class BtnUnion:
    """16-bit button bitfield, LSB-first (mirrors the C++ ``BtnUnion``).

    Individual components are accessed by name (``btn.A``, ``btn.Start`` ...);
    ``value`` holds the packed 16-bit word.
    """

    _FIELDS = (
        "R1", "L1", "Start", "Select", "R2", "L2", "f1", "f2",
        "A", "B", "X", "Y", "up", "right", "down", "left",
    )
    __slots__ = ("value",)

    def __init__(self, value: int = 0) -> None:
        self.value = int(value) & 0xFFFF

    def __getattr__(self, name: str) -> int:
        if name in BtnUnion._FIELDS:
            return (self.value >> BtnUnion._FIELDS.index(name)) & 1
        raise AttributeError("'BtnUnion' object has no attribute %r" % name)

    def __setattr__(self, name: str, val) -> None:
        if name == "value":
            object.__setattr__(self, "value", int(val) & 0xFFFF)
            return
        if name in BtnUnion._FIELDS:
            bit = BtnUnion._FIELDS.index(name)
            if val:
                self.value |= 1 << bit
            else:
                self.value &= ~(1 << bit)
            return
        object.__setattr__(self, name, val)


class BtnDataStruct:
    """Raw joystick payload (mirrors the C++ ``BtnDataStruct``)."""

    __slots__ = ("head", "btn", "lx", "rx", "ry", "L2", "ly")

    def __init__(self) -> None:
        self.head = [0, 0]
        self.btn = BtnUnion()
        self.lx = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.L2 = 0.0
        self.ly = 0.0


class REMOTE_DATA_RX:
    """Union view of raw joystick data (mirrors the C++ ``REMOTE_DATA_RX``).

    ``RF_RX`` exposes the parsed fields; ``buff`` round-trips the raw buffer
    (little-endian native layout: 2B head + 2B buttons + 5 floats, padded to
    ``BUFF_SIZE`` bytes).
    """

    _PACKED_SIZE = 24  # head[2] + btn[2] + lx/rx/ry/L2/ly[5*4]
    BUFF_SIZE = 40

    def __init__(self) -> None:
        self.RF_RX = BtnDataStruct()

    @property
    def buff(self) -> bytes:
        d = self.RF_RX
        packed = struct.pack(
            "<2BH5f",
            d.head[0], d.head[1], d.btn.value,
            d.lx, d.rx, d.ry, d.L2, d.ly,
        )
        return packed + b"\x00" * (self.BUFF_SIZE - self._PACKED_SIZE)

    @buff.setter
    def buff(self, raw) -> None:
        raw = bytes(raw)
        if len(raw) < self._PACKED_SIZE:
            raise ValueError(
                "Buffer too short: expected >= %d bytes, got %d"
                % (self._PACKED_SIZE, len(raw))
            )
        head0, head1, btnval, lx, rx, ry, L2, ly = struct.unpack(
            "<2BH5f", raw[: self._PACKED_SIZE]
        )
        d = self.RF_RX
        d.head = [head0, head1]
        d.btn.value = btnval
        d.lx, d.rx, d.ry, d.L2, d.ly = lx, rx, ry, L2, ly


class UnitreeJoystick:
    """Joystick state container holding every key supported by the DSL.

    Digital buttons are :class:`Button` instances, analog axes are
    :class:`Axis` instances. Feed raw data with :meth:`extract`, then read the
    maintained state (``pressed``/``on_pressed``/``pressed_time`` ...) or use
    :func:`compile_dsl`.
    """

    def __init__(self) -> None:
        self.back = Button()
        self.start = Button()
        self.LS = Button()
        self.RS = Button()
        self.LB = Button()
        self.RB = Button()
        self.A = Button()
        self.B = Button()
        self.X = Button()
        self.Y = Button()
        self.up = Button()
        self.down = Button()
        self.left = Button()
        self.right = Button()
        self.F1 = Button()
        self.F2 = Button()
        self.lx = Axis()
        self.ly = Axis()
        self.rx = Axis()
        self.ry = Axis()
        self.LT = Axis()
        self.RT = Axis()

    def update(self) -> None:
        """Hook for subclasses to refresh state (no-op, mirrors C++ ``update``)."""

    def extract(self, key: "REMOTE_DATA_RX") -> None:
        """Update every key from a raw :class:`REMOTE_DATA_RX` payload."""
        btn = key.RF_RX.btn
        self.back.update(btn.Select)
        self.start.update(btn.Start)
        self.LB.update(btn.L1)
        self.RB.update(btn.R1)
        self.F1.update(btn.f1)
        self.F2.update(btn.f2)
        self.A.update(btn.A)
        self.B.update(btn.B)
        self.X.update(btn.X)
        self.Y.update(btn.Y)
        self.up.update(btn.up)
        self.down.update(btn.down)
        self.left.update(btn.left)
        self.right.update(btn.right)
        self.LT.update(btn.L2)
        self.RT.update(btn.R2)
        self.lx.update(key.RF_RX.lx)
        self.ly.update(key.RF_RX.ly)
        self.rx.update(key.RF_RX.rx)
        self.ry.update(key.RF_RX.ry)

    def combine(self) -> "REMOTE_DATA_RX":
        """Serialize the current key state back into a :class:`REMOTE_DATA_RX`."""
        key = REMOTE_DATA_RX()
        btn = key.RF_RX.btn
        btn.Select = self.back.data
        btn.Start = self.start.data
        btn.L1 = self.LB.data
        btn.R1 = self.RB.data
        btn.f1 = self.F1.data
        btn.f2 = self.F2.data
        btn.A = self.A.data
        btn.B = self.B.data
        btn.X = self.X.data
        btn.Y = self.Y.data
        btn.up = self.up.data
        btn.down = self.down.data
        btn.left = self.left.data
        btn.right = self.right.data
        btn.L2 = 1 if self.LT.data > 0.5 else 0
        btn.R2 = 1 if self.RT.data > 0.5 else 0
        key.RF_RX.lx = self.lx.data
        key.RF_RX.ly = self.ly.data
        key.RF_RX.rx = self.rx.data
        key.RF_RX.ry = self.ry.data
        return key


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

    # --- Driver demo: extract() from a raw payload, then combine() back ---
    raw = REMOTE_DATA_RX()
    raw.RF_RX.btn.A = 1
    raw.RF_RX.btn.Start = 1
    raw.RF_RX.lx = 0.9
    raw.RF_RX.ly = -0.9
    joy2 = UnitreeJoystick()
    joy2.extract(raw)
    print()
    print("A pressed:", joy2.A.pressed, "| A on_pressed:", joy2.A.on_pressed)
    print("Start pressed:", joy2.start.pressed)
    print("lx.data:", round(joy2.lx.data, 4))

    out = joy2.combine()
    print("combine A:", out.RF_RX.btn.A, "| buff size:", len(out.buff))
