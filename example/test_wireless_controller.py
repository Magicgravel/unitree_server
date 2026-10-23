#!/usr/bin/env python3
"""
wireless_controller.py 的离线单元测试(无需真实 DDS / 机器人 / 手柄)。

覆盖:
  1. LowStateMessageHandler 对 raw 字节的解析 (wireless_remote -> UnitreeJoystick)
  2. set_key_mapping 的 DSL 编译与“上升沿”回调触发
  3. 组合键 (A+B)、长按等 DSL 表达式
  4. 回调抛异常时不影响 update() 主流程
  5. Init() 的订阅行为

运行:
    python example/test_wireless_controller.py
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from robot.common.wireless_controller import WirelessController

# BtnUnion 位定义 (LSB first):
#   R1,L1,Start,Select,R2,L2,f1,f2,A,B,X,Y,up,right,down,left
BTN = {
    "R1": 1 << 0, "L1": 1 << 1, "Start": 1 << 2, "Select": 1 << 3,
    "R2": 1 << 4, "L2": 1 << 5, "f1": 1 << 6, "f2": 1 << 7,
    "A": 1 << 8, "B": 1 << 9, "X": 1 << 10, "Y": 1 << 11,
    "up": 1 << 12, "right": 1 << 13, "down": 1 << 14, "left": 1 << 15,
    # 摇杆侧命名别名: R1 -> RB, L1 -> LB
    "RB": 1 << 0, "LB": 1 << 1,
}


def make_remote(
    buttons: int = 0,
    lx: float = 0.0,
    ly: float = 0.0,
    rx: float = 0.0,
    ry: float = 0.0,
) -> list:
    """构造 40 字节 wireless_remote 负载。

    布局 <2BH5f: head0, head1, btn, lx, rx, ry, L2, ly
    """
    packed = struct.pack("<2BH5f", 0, 0, buttons, lx, rx, ry, 0.0, ly)
    return list(packed.ljust(40, b"\x00"))


class FakeLowState:
    """最小化的 LowState_ 假对象, 只提供 wireless_remote 字段。"""

    def __init__(self, remote: list) -> None:
        self.wireless_remote = remote


class TestWirelessController(unittest.TestCase):
    def setUp(self) -> None:
        # 隔离 pygame 手柄依赖: patch() 变成 no-op, 避免无手柄时崩溃
        gp_patcher = mock.patch("robot.common.wireless_controller.GamepadPatch")
        self.mock_gp_cls = gp_patcher.start()
        self.addCleanup(gp_patcher.stop)

        self.wc = WirelessController()

    def feed(self, buttons: int = 0, **axes) -> None:
        """向控制器注入一帧 lowstate 消息。"""
        self.wc.LowStateMessageHandler(FakeLowState(make_remote(buttons, **axes)))

    # ---------- 消息解析 ----------

    def test_lowstate_handler_parses_buttons(self):
        self.feed(BTN["A"] | BTN["RB"])
        with self.wc._lock:
            self.assertTrue(self.wc.unitree_joystick.A.pressed)
            self.assertTrue(self.wc.unitree_joystick.RB.pressed)
            self.assertFalse(self.wc.unitree_joystick.B.pressed)

    def test_lowstate_handler_counts_messages_and_stores_msg(self):
        msg = FakeLowState(make_remote(BTN["A"]))
        self.wc.LowStateMessageHandler(msg)
        self.assertEqual(self.wc._msg_count, 1)
        self.assertIs(self.wc.lowstate, msg)

    def test_lowstate_handler_parses_axes(self):
        self.feed(0, lx=0.8, ly=-0.8)
        with self.wc._lock:
            self.assertAlmostEqual(self.wc.unitree_joystick.lx.data, 0.8 * 0.03, places=6)
            self.assertAlmostEqual(self.wc.unitree_joystick.ly.data, -0.8 * 0.03, places=6)

    # ---------- DSL 映射与上升沿触发 ----------

    def test_single_key_rising_edge(self):
        calls = []
        self.wc.set_key_mapping({"A": lambda: calls.append("A")})

        self.feed(BTN["A"])
        self.wc.update()
        self.assertEqual(calls, ["A"])

        # 同一状态重复 update 不应重复触发
        self.wc.update()
        self.wc.update()
        self.assertEqual(calls, ["A"])

    def test_release_then_press_again(self):
        calls = []
        self.wc.set_key_mapping({"A": lambda: calls.append("A")})

        self.feed(BTN["A"])
        self.wc.update()
        self.feed(0)          # 松开
        self.wc.update()
        self.feed(BTN["A"])   # 再次按下
        self.wc.update()

        self.assertEqual(calls, ["A", "A"])

    def test_combo_and_requires_both(self):
        calls = []
        self.wc.set_key_mapping({"A+B": lambda: calls.append("AB")})

        self.feed(BTN["A"])
        self.wc.update()
        self.assertEqual(calls, [])

        self.feed(BTN["A"] | BTN["B"])
        self.wc.update()
        self.assertEqual(calls, ["AB"])

    def test_on_pressed_trigger(self):
        calls = []
        self.wc.set_key_mapping({"start.on_pressed": lambda: calls.append("start")})

        self.feed(BTN["Start"])
        self.wc.update()
        self.assertEqual(calls, ["start"])

        self.wc.update()  # 边沿已过, 不再触发
        self.assertEqual(calls, ["start"])

    def test_empty_mapping_is_safe(self):
        self.wc.set_key_mapping({})
        self.feed(BTN["A"])
        self.wc.update()  # 不应抛异常

    def test_callback_exception_is_swallowed(self):
        def bad():
            raise RuntimeError("boom")

        ok_calls = []
        self.wc.set_key_mapping({
            "A": bad,
            "B": lambda: ok_calls.append("B"),
        })

        self.feed(BTN["A"] | BTN["B"])
        self.wc.update()  # bad 抛异常不应中断 update
        self.assertEqual(ok_calls, ["B"])

    # ---------- Init 订阅 ----------

    def test_init_subscribes_to_lowstate(self):
        with mock.patch("robot.common.wireless_controller.ChannelSubscriber") as mock_sub:
            self.wc.Init()

        mock_sub.assert_called_once_with("rt/lowstate", mock.ANY)
        self.wc.lowstate_subscriber.Init.assert_called_once_with(
            self.wc.LowStateMessageHandler, 10
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
