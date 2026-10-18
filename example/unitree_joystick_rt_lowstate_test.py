#!/usr/bin/env python3
"""
订阅 rt/lowstate，解析其中 wireless_remote(40B) 手柄数据，
使用 UnitreeJoystick + DSL 验证按键/摇杆状态。

示例:
    python example/unitree_joystick_rt_lowstate_test.py --interface lo --domain-id 0
    python example/unitree_joystick_rt_lowstate_test.py --robot go2 --dsl "A.on_pressed" "LB+RB"
"""

from __future__ import annotations

import argparse
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber

from robot.common.unitree_joystick import REMOTE_DATA_RX, UnitreeJoystick, compile_dsl

TOPIC_LOWSTATE = "rt/lowstate"


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


class LowStateJoystickTester:
    def __init__(self, dsl_exprs: List[str], robot: str) -> None:
        self.joy = UnitreeJoystick()
        self.predicates = {expr: compile_dsl(expr) for expr in dsl_exprs}
        self.prev_dsl_state = {expr: False for expr in dsl_exprs}
        self.raw = REMOTE_DATA_RX()
        self.msg_count = 0
        self._lock = threading.Lock()

        if robot == "g1":
            from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_  # type: ignore
        else:
            from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_  # type: ignore
        self.lowstate_type = LowState_

    def handler(self, msg) -> None:
        with self._lock:
            # 直接按 REMOTE_DATA_RX 的原始布局解析，避免手工字节偏移错误
            self.raw.buff = bytes(msg.wireless_remote)
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
            hits = []
            for expr, pred in self.predicates.items():
                state = bool(pred(self.joy))
                if state and not self.prev_dsl_state[expr]:
                    hits.append(expr)
                self.prev_dsl_state[expr] = state

            # 方便核对原始 bitfield
            btn_u16 = struct.unpack("<H", bytes(self.raw.buff[2:4]))[0]

        print(
            f"\rmsg={msg_count:<7} btn=0x{btn_u16:04x} pressed={pressed!s:<40} "
            f"lx={lx:+.2f} ly={ly:+.2f} rx={rx:+.2f} ry={ry:+.2f}",
            end="",
            flush=True,
        )
        for expr in hits:
            print(f"\n[DSL HIT] {expr}")


def main() -> None:
    parser = argparse.ArgumentParser(description="rt/lowstate -> UnitreeJoystick 测试")
    parser.add_argument("--interface", default="lo", help="DDS 网卡名，默认 lo")
    parser.add_argument("--domain-id", type=int, default=0, help="DDS domain id，默认 0")
    parser.add_argument("--robot", choices=["g1", "go2"], default="g1", help="LowState 类型，默认 g1")
    parser.add_argument("--hz", type=float, default=30.0, help="打印频率，默认 30Hz")
    parser.add_argument(
        "--dsl",
        nargs="*",
        default=["A.on_pressed", "LB+RB", "LT + up", "start.on_pressed"],
        help="要验证的 DSL 表达式列表",
    )
    args = parser.parse_args()

    tester = LowStateJoystickTester(args.dsl, args.robot)

    ChannelFactoryInitialize(args.domain_id, args.interface)
    sub = ChannelSubscriber(TOPIC_LOWSTATE, tester.lowstate_type)
    sub.Init(tester.handler, 10)

    print(
        f"[INFO] subscribed topic={TOPIC_LOWSTATE}, domain={args.domain_id}, interface={args.interface}, robot={args.robot}"
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

