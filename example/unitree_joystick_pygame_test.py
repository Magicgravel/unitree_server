#!/usr/bin/env python3
"""
使用 pygame 读取真实手柄数据，驱动 UnitreeJoystick，验证按键/摇杆与 DSL 触发表现。

运行示例:
    python example/unitree_joystick_pygame_test.py
    python example/unitree_joystick_pygame_test.py --index 1 --fps 30 --dsl "A.on_pressed" "LB+RB"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import pygame

# 允许直接 `python example/xxx.py` 运行时导入项目内模块
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from robot.common.unitree_joystick import REMOTE_DATA_RX, UnitreeJoystick, compile_dsl


# 常见 Xbox/通用手柄映射（不同手柄可能不同，可按你的设备修改）
DEFAULT_BUTTON_MAP: Dict[str, int] = {
    "A": 0,
    "B": 1,
    "X": 2,
    "Y": 3,
    "LB": 4,
    "RB": 5,
    "back": 6,
    "start": 7,
    "LS": 8,
    "RS": 9,
}

DEFAULT_AXIS_MAP: Dict[str, int] = {
    "lx": 0,
    "ly": 1,
    "rx": 2,
    "ry": 3,
    "lt": 4,
    "rt": 5,
}


def _get_button(js: pygame.joystick.Joystick, idx: int) -> int:
    if idx < 0 or idx >= js.get_numbuttons():
        return 0
    return int(js.get_button(idx))


def _get_axis(js: pygame.joystick.Joystick, idx: int) -> float:
    if idx < 0 or idx >= js.get_numaxes():
        return 0.0
    return float(js.get_axis(idx))


def _normalize_trigger(v: float) -> float:
    # 一些驱动返回 [-1,1]，转换到 [0,1]
    if v < 0.0:
        return max(0.0, min(1.0, (v + 1.0) * 0.5))
    return max(0.0, min(1.0, v))


def _build_remote_data(
    js: pygame.joystick.Joystick,
    axis_deadzone: float,
    trigger_threshold: float,
) -> REMOTE_DATA_RX:
    raw = REMOTE_DATA_RX()
    btn = raw.RF_RX.btn

    btn.A = _get_button(js, DEFAULT_BUTTON_MAP["A"])
    btn.B = _get_button(js, DEFAULT_BUTTON_MAP["B"])
    btn.X = _get_button(js, DEFAULT_BUTTON_MAP["X"])
    btn.Y = _get_button(js, DEFAULT_BUTTON_MAP["Y"])
    btn.L1 = _get_button(js, DEFAULT_BUTTON_MAP["LB"])
    btn.R1 = _get_button(js, DEFAULT_BUTTON_MAP["RB"])
    btn.Select = _get_button(js, DEFAULT_BUTTON_MAP["back"])
    btn.Start = _get_button(js, DEFAULT_BUTTON_MAP["start"])

    lx = _get_axis(js, DEFAULT_AXIS_MAP["lx"])
    ly = _get_axis(js, DEFAULT_AXIS_MAP["ly"])
    rx = _get_axis(js, DEFAULT_AXIS_MAP["rx"])
    ry = _get_axis(js, DEFAULT_AXIS_MAP["ry"])
    lt = _normalize_trigger(_get_axis(js, DEFAULT_AXIS_MAP["lt"]))
    rt = _normalize_trigger(_get_axis(js, DEFAULT_AXIS_MAP["rt"]))

    raw.RF_RX.lx = 0.0 if abs(lx) < axis_deadzone else lx
    raw.RF_RX.ly = 0.0 if abs(ly) < axis_deadzone else ly
    raw.RF_RX.rx = 0.0 if abs(rx) < axis_deadzone else rx
    raw.RF_RX.ry = 0.0 if abs(ry) < axis_deadzone else ry

    # unitree_joystick.py 中 LT/RT 由 btn.L2/btn.R2 驱动
    btn.L2 = 1 if lt >= trigger_threshold else 0
    btn.R2 = 1 if rt >= trigger_threshold else 0

    # 同时保留模拟量（当前 extract() 不消费该值，但对调试有帮助）
    raw.RF_RX.L2 = lt

    if js.get_numhats() > 0:
        hx, hy = js.get_hat(0)
        btn.left = 1 if hx < 0 else 0
        btn.right = 1 if hx > 0 else 0
        btn.up = 1 if hy > 0 else 0
        btn.down = 1 if hy < 0 else 0

    return raw


def _pressed_keys(joy: UnitreeJoystick) -> List[str]:
    keys = [
        "A", "B", "X", "Y", "LB", "RB", "back", "start",
        "up", "down", "left", "right", "LT", "RT",
    ]
    result = []
    for name in keys:
        kb = getattr(joy, name if name in ("A", "B", "X", "Y", "LB", "RB", "LT", "RT") else name)
        if kb.pressed:
            result.append(name)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="pygame -> UnitreeJoystick 功能测试")
    parser.add_argument("--index", type=int, default=0, help="手柄索引，默认 0")
    parser.add_argument("--fps", type=int, default=50, help="采样频率，默认 50")
    parser.add_argument("--axis-deadzone", type=float, default=0.08, help="输入死区，默认 0.08")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="LT/RT 按下阈值，默认 0.5")
    parser.add_argument(
        "--dsl",
        nargs="*",
        default=[
            "A.on_pressed",
            "LB+RB",
            "LT + up",
            "start.on_pressed",
            "LS + RS",
            "F1",
        ],
        help="要验证的 DSL 表达式列表",
    )
    args = parser.parse_args()

    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    if count <= args.index:
        raise RuntimeError(f"未找到索引 {args.index} 的手柄，当前仅检测到 {count} 个手柄")

    js = pygame.joystick.Joystick(args.index)
    js.init()

    joy = UnitreeJoystick()
    predicates = {expr: compile_dsl(expr) for expr in args.dsl}
    prev_dsl_state = {expr: False for expr in args.dsl}

    print(f"[INFO] 手柄: {js.get_name()} (index={args.index})")
    print(
        f"[INFO] axes={js.get_numaxes()} buttons={js.get_numbuttons()} hats={js.get_numhats()} balls={js.get_numballs()}"
    )
    print("[INFO] 按 Ctrl+C 退出")
    print("[INFO] 监控 DSL:", ", ".join(args.dsl))

    clock = pygame.time.Clock()
    try:
        while True:
            pygame.event.pump()
            raw = _build_remote_data(js, args.axis_deadzone, args.trigger_threshold)
            joy.extract(raw)

            pressed = _pressed_keys(joy)
            print(
                f"\rpressed={pressed!s:<40} "
                f"lx={joy.lx.data:+.2f} ly={joy.ly.data:+.2f} "
                f"rx={joy.rx.data:+.2f} ry={joy.ry.data:+.2f}",
                end="",
                flush=True,
            )

            for expr, pred in predicates.items():
                state = bool(pred(joy))
                if state and not prev_dsl_state[expr]:
                    print(f"\n[DSL HIT] {expr}")
                prev_dsl_state[expr] = state

            clock.tick(args.fps)
    except KeyboardInterrupt:
        print("\n[INFO] 退出测试")
    finally:
        js.quit()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
