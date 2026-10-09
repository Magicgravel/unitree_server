# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/common/unitree_joystick.hpp

import math
import struct
import time


# ***************************** Unitree Joystick Data Type ***************************** #


class BtnUnion:
    """Equivalent of the C++ ``BtnUnion`` (16-bit button bitfield)."""

    def __init__(self):
        self.value = 0

    # Bit indexes (little-endian bitfield, matching the C++ declaration order).
    R1 = 0
    L1 = 1
    Start = 2
    Select = 3
    R2 = 4
    L2 = 5
    f1 = 6
    f2 = 7
    A = 8
    B = 9
    X = 10
    Y = 11
    up = 12
    right = 13
    down = 14
    left = 15


class RemoteDataRx:
    """Equivalent of the C++ ``REMOTE_DATA_RX`` union (40-byte buffer)."""

    # Byte offsets of the float axes inside the buffer.
    LX_OFFSET = 4
    RX_OFFSET = 8
    RY_OFFSET = 12
    L2_OFFSET = 16
    LY_OFFSET = 20

    def __init__(self):
        self.buff = bytearray(40)
        self.btn = BtnUnion()

    @classmethod
    def unpack(cls, data):
        """Build a RemoteDataRx from a 40-byte wireless_remote sequence."""
        key = cls()
        key.buff = bytearray(data[:40])
        key.btn.value = key.buff[2] | (key.buff[3] << 8)
        return key

    def pack(self):
        """Write the button bits back into the buffer."""
        self.buff[2] = self.btn.value & 0xFF
        self.buff[3] = (self.btn.value >> 8) & 0xFF
        return self.buff

    def get_float(self, offset):
        return struct.unpack("<f", bytes(self.buff[offset:offset + 4]))[0]

    def set_float(self, offset, value):
        self.buff[offset:offset + 4] = struct.pack("<f", float(value))


# ***************************** Button & Axis ***************************** #


class KeyBase:
    """Base class for keys, tracking pressed/on_pressed/on_released state.

    Example::

        >>> btn = Button()
        >>> btn(1)  # update
        >>> btn.pressed
        >>> if btn.on_pressed:
        >>>     print(btn.click_cnt)
        >>> if btn.pressed:
        >>>     print(btn.pressed_time)
    """

    DOUBLE_CLICK_THRESHOLD = 0.5  # Unit: second

    def __init__(self):
        self.pressed = False
        self.on_pressed = False
        self.on_released = False
        self.click_cnt = 0  # used at `on_pressed`
        self.pressed_time = 0.0
        self._last_pressed = False
        self._last_click_time = None

    def update(self, is_pressed):
        is_pressed = bool(is_pressed)
        self.pressed = is_pressed
        self.on_pressed = self.pressed and not self._last_pressed
        self.on_released = (not self.pressed) and self._last_pressed
        self._last_pressed = self.pressed

        now = time.monotonic()
        if self.on_pressed:
            if (
                self._last_click_time is not None
                and (now - self._last_click_time) < self.DOUBLE_CLICK_THRESHOLD
            ):
                self.click_cnt += 1
            else:
                self.click_cnt = 1
            self._last_click_time = now

        if self.pressed and self._last_click_time is not None:
            self.pressed_time = now - self._last_click_time

        if not (self.pressed or self.on_released):  # save once time on released
            self.pressed_time = 0.0


class Button(KeyBase):
    """A button fed with integer data (0 == released, otherwise pressed)."""

    def __init__(self):
        super().__init__()
        self._data = 0
        self._data_null = 0

    def __call__(self, data=None):
        if data is None:
            return self._data
        is_pressed = data != self._data_null
        self.update(is_pressed)
        self._data = data
        return self._data


class Axis(KeyBase):
    """An analog axis with deadzone and smoothing."""

    def __init__(self):
        super().__init__()
        self._data = 0.0
        self.smooth = 0.03
        self.deadzone = 0.01
        self.threshold = 0.5  # Change an axis value to a button

    def __call__(self, data=None):
        if data is None:
            return self._data
        data_deadzone = 0.0 if math.fabs(data) < self.deadzone else data
        new_data = self._data * (1.0 - self.smooth) + data_deadzone * self.smooth
        is_pressed = new_data > self.threshold
        self.update(is_pressed)
        self._data = new_data
        return self._data


# ***************************** Unitree Joystick Interface ***************************** #


class UnitreeJoystick:
    """Adopts standard joystick key names."""

    def __init__(self):
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

    def update(self):
        """Override in subclasses to refresh state from raw hardware data."""
        pass

    def extract(self, key):
        """Update all keys from a RemoteDataRx (or 40-byte wireless_remote)."""
        if not isinstance(key, RemoteDataRx):
            key = RemoteDataRx.unpack(key)

        btn = key.btn.value
        self.back(int((btn >> BtnUnion.Select) & 1))
        self.start(int((btn >> BtnUnion.Start) & 1))
        self.LB(int((btn >> BtnUnion.L1) & 1))
        self.RB(int((btn >> BtnUnion.R1) & 1))
        self.F1(int((btn >> BtnUnion.f1) & 1))
        self.F2(int((btn >> BtnUnion.f2) & 1))
        self.A(int((btn >> BtnUnion.A) & 1))
        self.B(int((btn >> BtnUnion.B) & 1))
        self.X(int((btn >> BtnUnion.X) & 1))
        self.Y(int((btn >> BtnUnion.Y) & 1))
        self.up(int((btn >> BtnUnion.up) & 1))
        self.down(int((btn >> BtnUnion.down) & 1))
        self.left(int((btn >> BtnUnion.left) & 1))
        self.right(int((btn >> BtnUnion.right) & 1))
        self.LT(float((btn >> BtnUnion.L2) & 1))
        self.RT(float((btn >> BtnUnion.R2) & 1))
        self.lx(key.get_float(RemoteDataRx.LX_OFFSET))
        self.ly(key.get_float(RemoteDataRx.LY_OFFSET))
        self.rx(key.get_float(RemoteDataRx.RX_OFFSET))
        self.ry(key.get_float(RemoteDataRx.RY_OFFSET))

    def combine(self):
        """Merge the current joystick state into a RemoteDataRx."""
        key = RemoteDataRx()
        btn = key.btn

        btn.value |= int(bool(self.RB())) << BtnUnion.R1
        btn.value |= int(bool(self.LB())) << BtnUnion.L1
        btn.value |= int(bool(self.start())) << BtnUnion.Start
        btn.value |= int(bool(self.back())) << BtnUnion.Select
        btn.value |= int(self.RT() > 0.5) << BtnUnion.R2
        btn.value |= int(self.LT() > 0.5) << BtnUnion.L2
        btn.value |= int(bool(self.F1())) << BtnUnion.f1
        btn.value |= int(bool(self.F2())) << BtnUnion.f2
        btn.value |= int(bool(self.A())) << BtnUnion.A
        btn.value |= int(bool(self.B())) << BtnUnion.B
        btn.value |= int(bool(self.X())) << BtnUnion.X
        btn.value |= int(bool(self.Y())) << BtnUnion.Y
        btn.value |= int(bool(self.up())) << BtnUnion.up
        btn.value |= int(bool(self.right())) << BtnUnion.right
        btn.value |= int(bool(self.down())) << BtnUnion.down
        btn.value |= int(bool(self.left())) << BtnUnion.left

        key.set_float(RemoteDataRx.LX_OFFSET, self.lx())
        key.set_float(RemoteDataRx.RX_OFFSET, self.rx())
        key.set_float(RemoteDataRx.RY_OFFSET, self.ry())
        key.set_float(RemoteDataRx.LY_OFFSET, self.ly())

        key.pack()
        return key
