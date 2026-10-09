#!/usr/bin/env python3
"""
Unitree 机器人键盘控制脚本 (Keyboard Control for Unitree Robots).

用法 / Usage:
    python ctrl_keyboard.py <networkInterface>

    示例 / Example:
        python ctrl_keyboard.py eth0

按键说明 / Key Bindings:
    w / W / ↑ : 前进 (Move Forward)
    s / S / ↓ : 后退 (Move Backward)
    a / A / ← : 左移 (Move Left)
    d / D / → : 右移 (Move Right)
    q / Q     : 左转 (Turn Left)
    e / E     : 右转 (Turn Right)
    空格 (Space) : 停止 (Stop)
    Esc / Ctrl+C : 退出 (Quit)

注意 / Notes:
    - 需要在 TTY 终端中运行，不支持重定向输入。
    - 发布频率: 50 Hz。
    - 支持机器人型号: 通过 import 切换 SportClient (当前为 G1)。
"""

import select
import sys
import termios
import threading
import time
import tty

# from pathlib import Path
# SDK_ROOT = Path('~/unitree_sdk2_python').expanduser().resolve()
# if str(SDK_ROOT) not in sys.path:
#     sys.path.insert(0, str(SDK_ROOT))

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
# from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient as SportClient
# from unitree_sdk2py.h2.loco.h2_loco_client import LocoClient as SportClient
from unitree_sdk2py.go2.sport.sport_client import SportClient
# from unitree_sdk2py.b2.sport.sport_client import SportClient 
# from unitree_sdk2py.a2.sport.sport_client import SportClient

VX_MAX = 0.5
VY_MAX = 0.8
VYAW_MAX = 2.0

VX_STEP = 0.1
VY_STEP = 0.1
VYAW_STEP = 0.1

PUBLISH_DT = 0.02

KEY_FORWARD = {b"w", b"W", b"\x1b[A"}
KEY_BACKWARD = {b"s", b"S", b"\x1b[B"}
KEY_LEFT = {b"a", b"A", b"\x1b[D"}
KEY_RIGHT = {b"d", b"D", b"\x1b[C"}
KEY_TURN_LEFT = {b"q", b"Q"}
KEY_TURN_RIGHT = {b"e", b"E"}
KEY_STOP = {b" "}
KEY_QUIT = {b"\x03", b"\x1b"}


class KeyboardReader:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        self.key = b""
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join(timeout=0.5)
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        with self.lock:
            key = self.key
            self.key = b""
        return key

    def _run(self):
        tty.setraw(self.fd)
        try:
            while self.running:
                if not select.select([sys.stdin], [], [], 0.02)[0]:
                    continue
                key = sys.stdin.buffer.read(1)
                if key == b"\x1b" and select.select([sys.stdin], [], [], 0.01)[0]:
                    key += sys.stdin.buffer.read(1)
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        key += sys.stdin.buffer.read(1)
                with self.lock:
                    self.key = key
        finally:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


def print_help():
    print("Unitree robot keyboard control")
    print("w/up: forward")
    print("s/down: backward")
    print("a/left: move left")
    print("d/right: move right")
    print("q: turn left")
    print("e: turn right")
    print("space: stop")
    print("esc or ctrl-c: quit")
    print("publish rate: 50 Hz")


def print_status(vx, vy, vyaw, ret):
    sys.stdout.write(f"\r vx={vx:+.2f}  vy={vy:+.2f}  vyaw={vyaw:+.2f} ret={ret} ")
    sys.stdout.flush()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} networkInterface")
        sys.exit(1)

    if not sys.stdin.isatty():
        print("This script requires a TTY terminal.")
        sys.exit(1)

    ChannelFactoryInitialize(0, sys.argv[1])

    sport_client = SportClient()
    sport_client.SetTimeout(5.0)
    sport_client.Init()

    print_help()

    reader = KeyboardReader()
    reader.start()

    vx = 0.0
    vy = 0.0
    vyaw = 0.0
    next_tick = time.monotonic()

    try:
        while True:
            key = reader.get_key()
            if key in KEY_QUIT:
                break
            if key in KEY_FORWARD:
                vx = min(vx + VX_STEP, VX_MAX)
            elif key in KEY_BACKWARD:
                vx = max(vx - VX_STEP, -VX_MAX)
            elif key in KEY_LEFT:
                vy = min(vy + VY_STEP, VY_MAX)
            elif key in KEY_RIGHT:
                vy = max(vy - VY_STEP, -VY_MAX)
            elif key in KEY_TURN_LEFT:
                vyaw = min(vyaw + VYAW_STEP, VYAW_MAX)
            elif key in KEY_TURN_RIGHT:
                vyaw = max(vyaw - VYAW_STEP, -VYAW_MAX)
            elif key in KEY_STOP:
                vx, vy, vyaw = 0.0, 0.0, 0.0

            ret = sport_client.Move(vx, vy, vyaw)
            print_status(vx, vy, vyaw, ret)

            next_tick += PUBLISH_DT
            sleep_time = next_tick - time.monotonic()
            if sleep_time > 0.0:
                time.sleep(sleep_time)
            else:
                next_tick = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        sport_client.StopMove()
        print("\nStopped.")


if __name__ == "__main__":
    main()
