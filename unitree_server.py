#!/usr/bin/env python3
"""
Unitree 机器人服务入口 (Unitree Robot Server Entry Point).

架构 / Architecture:
    unitree_sdk (高层接口)  <--->  unitree_server (处理 RPC 接口调用)
                                      |
                                      +---> unitree_mujoco (仿真)  或  unitree_robot (实机)

该脚本根据命令行参数启动一个或多个 RPC 服务:
    --loco   : 运动控制服务 (G1LocoServer, 基于 FSM + 运动策略)
    --audio  : 语音播放服务 (G1AudioServer, 接收 PCM 流并播放)
    --arm    : 上肢动作服务 (G1ArmActionServer, 执行内置/自定义动作)

示例 / Examples:
    # 实机运动控制
    python3 unitree_server.py --loco --interface eth0

    # 仿真运动控制
    python3 unitree_server.py --loco --sim

    # 同时启动全部服务
    python3 unitree_server.py --loco --audio --arm --sim
"""

import argparse
import os
import signal
import threading

from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from robot.g1.loco.g1_loco_server import G1LocoServer
from robot.g1.audio.g1_audio_server import G1AudioServer
from robot.g1.arm.g1_arm_action_server import G1ArmActionServer

# 目前仅实现了 G1 的服务端, 后续可扩展 h2/go2/r1 等机型。
SUPPORTED_ROBOTS = ("g1",)
UNITREE_MUJOCO_DIR = os.path.dirname(os.path.abspath(__file__)) + "/unitree_mujoco/simulate_python"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unitree robot RPC server entry point.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--domain_id", type=int, default=1, help="DDS 域 ID (domain id)"
    )
    parser.add_argument(
        "--interface", type=str, default="lo", help="连接机器人的网卡名称"
    )
    parser.add_argument(
        "--sim", action="store_true", help="打开 unitree_mujoco 仿真"
    )
    parser.add_argument(
        "--robot", type=str, default="g1", choices=SUPPORTED_ROBOTS,
        help="机器人型号",
    )
    parser.add_argument(
        "--joystick", action="store_true", default=False, help="启动使用游戏手柄模拟R3"
    )
    parser.add_argument(
        "--loco", action="store_true", help="启动运动控制服务"
    )
    parser.add_argument(
        "--audio", action="store_true", help="启动语音播放服务"
    )
    parser.add_argument(
        "--arm", action="store_true", help="启动上肢动作服务"
    )
    return parser


def main():
    args = build_parser().parse_args()

    if args.sim:
        if not os.path.exists(UNITREE_MUJOCO_DIR):
            print(f"[unitree_server] simulation directory not found: {UNITREE_MUJOCO_DIR}")
            print(f"[unitree_server] clone the repository using:")
            print(f"    git clone https://github.com/UnitreeRobotics/unitree_mujoco.git")
            print(f"    or")
            print(f"    git submodule update --init --recursive")
            return
        print("[unitree_server] running in simulation mode.")
        
        # 修改 unitree_mujoco/simulate_python/config.py 中的 ROBOT，USE_JOYSTICK 字段
        config_path = os.path.join(UNITREE_MUJOCO_DIR, "config.py")
        with open(config_path, "r") as f:
            config_lines = f.readlines()
        with open(config_path, "w") as f:
            for line in config_lines:
                if line.startswith("ROBOT ="):
                    f.write(f"ROBOT = '{args.robot}'\n")
                elif line.startswith("DOMAIN_ID ="):
                    f.write(f"DOMAIN_ID = {args.domain_id}\n")
                elif line.startswith("INTERFACE ="):
                    f.write(f"INTERFACE = '{args.interface}'\n")
                elif line.startswith("USE_JOYSTICK ="):
                    f.write(f"USE_JOYSTICK = {args.joystick}\n")
                else:
                    f.write(line)
        
        # 运行 unitree_mujoco/simulation_python/unitree_mujoco.py
        import subprocess
        subprocess.Popen(["python3", "unitree_mujoco.py"], cwd=UNITREE_MUJOCO_DIR)

    # 初始化 DDS 通道 (domain id + 网卡)
    ChannelFactoryInitialize(args.domain_id, args.interface)

    servers = []
    stop_event = threading.Event()

    if args.robot == "g1":
        if args.loco:
            loco_server = G1LocoServer()
            loco_server.Init()
            loco_server.Start()
            servers.append(loco_server)
            print("[G1LocoServer] started, waiting for loco commands...")
        if args.audio:
            audio_server = G1AudioServer()
            audio_server.Init()
            audio_server.Start()
            servers.append(audio_server)
            print("[G1AudioServer] started, waiting for PlayStream requests...")
        if args.arm:
            arm_server = G1ArmActionServer()
            arm_server.Init()
            arm_server.Start()
            servers.append(arm_server)
            print("[G1ArmActionServer] started, waiting for arm commands...")

    def handle_signal(signum, _frame):
        print(f"\n[unitree_server] received signal {signum}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # 服务在后台线程中运行, 主线程需要保持存活。
    try:
        while not stop_event.is_set():
            stop_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        for server in servers:
            stop = getattr(server, "Stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception as exc:  # noqa: BLE001
                    print(f"[unitree_server] failed to stop {server.GetName()}: {exc}")
        print("[unitree_server] exited.")


if __name__ == "__main__":
    main()
