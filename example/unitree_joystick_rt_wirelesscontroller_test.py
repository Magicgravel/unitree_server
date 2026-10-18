#!/usr/bin/env python3
"""
订阅 rt/wirelesscontroller，解析 keys/lx/ly/rx/ry，
使用 UnitreeJoystick + DSL 验证按键/摇杆状态。

示例:
    python example/unitree_joystick_rt_wirelesscontroller_test.py --interface lo --domain-id 0
    python example/unitree_joystick_rt_wirelesscontroller_test.py --dsl "A.on_pressed" "LB+RB"
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_

from robot.common.unitree_joystick import REMOTE_DATA_RX, UnitreeJoystick, compile_dsl

TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"


def _pressed_keys(joy: UnitreeJoystick) -> List[str]:
    names = [
        "A",
        "B",
        "X",
        "Y",
        "LB",
        "RB",
        "back",
        "start",
        "up",
        "down",
        "left",
        "right",
        "LT",
        "RT",
    ]
    out = []
    for name in names:
        key = getattr(joy, name if name in ("A", "B", "X", "Y", "LB", "RB", "LT", "RT") else name)
        if key.pressed:
            out.append(name)
    return out


class WirelessControllerJoystickTester:
    def __init__(self, dsl_exprs: List[str]) -> None:
        self.joy = UnitreeJoystick()
        self.predicates = {expr: compile_dsl(expr) for expr in dsl_exprs}
        self.prev_dsl_state = {expr: False for expr in dsl_exprs}
        self.raw = REMOTE_DATA_RX()
        self.msg_count = 0
        self._lock = threading.Lock()

    def handler(self, msg: WirelessController_) -> None:
        with self._lock:
            # bridge 发布的 keys bit 顺序与 BtnUnion 一致(16 bits)
            self.raw.RF_RX.btn.value = int(msg.keys) & 0xFFFF
            self.raw.RF_RX.lx = float(msg.lx)
            self.raw.RF_RX.ly = float(msg.ly)
            self.raw.RF_RX.rx = float(msg.rx)
            self.raw.RF_RX.ry = float(msg.ry)
            self.joy.extract(self.raw)
            self.msg_count += 1

    def print_status(self) -> None:
        with self._lock:
            pressed = _pressed_keys(self.joy)
            lx = self.joy.lx.data
            ly = self.joy.ly.data
            rx = self.joy.rx.data
            ry = self.joy.ry.data
            msg_count = self.msg_count
            btn_u16 = self.raw.RF_RX.btn.value
            hits = []
            for expr, pred in self.predicates.items():
                state = bool(pred(self.joy))
                if state and not self.prev_dsl_state[expr]:
                    hits.append(expr)
                self.prev_dsl_state[expr] = state

        print(
            f"\rmsg={msg_count:<7} keys=0x{btn_u16:04x} pressed={pressed!s:<40} "
            f"lx={lx:+.2f} ly={ly:+.2f} rx={rx:+.2f} ry={ry:+.2f}",
            end="",
            flush=True,
        )
        for expr in hits:
            print(f"\n[DSL HIT] {expr}")


def main() -> None:
    parser = argparse.ArgumentParser(description="rt/wirelesscontroller -> UnitreeJoystick 测试")
    parser.add_argument("--interface", default="lo", help="DDS 网卡名，默认 lo")
    parser.add_argument("--domain-id", type=int, default=0, help="DDS domain id，默认 0")
    parser.add_argument("--hz", type=float, default=30.0, help="打印频率，默认 30Hz")
    parser.add_argument(
        "--dsl",
        nargs="*",
        default=["A.on_pressed", "LB+RB", "LT + up", "start.on_pressed"],
        help="要验证的 DSL 表达式列表",
    )
    args = parser.parse_args()

    tester = WirelessControllerJoystickTester(args.dsl)

    ChannelFactoryInitialize(args.domain_id, args.interface)
    sub = ChannelSubscriber(TOPIC_WIRELESS_CONTROLLER, WirelessController_)
    sub.Init(tester.handler, 10)

    print(
        f"[INFO] subscribed topic={TOPIC_WIRELESS_CONTROLLER}, domain={args.domain_id}, interface={args.interface}"
    )
    print("[INFO] 按 Ctrl+C 退出")
    print("[INFO] 监控 DSL:", ", ".join(args.dsl))

    period = 1.0 / max(1e-6, args.hz)
    try:
        while True:
            tester.print_status()
            time.sleep(period)
    except KeyboardInterrupt:
        print("\n[INFO] 退出测试")


if __name__ == "__main__":
    main()

