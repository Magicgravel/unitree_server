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
import signal
import threading

from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from robot.g1.loco.g1_loco_server import G1LocoServer
from robot.g1.audio.g1_audio_server import G1AudioServer
from robot.g1.arm.g1_arm_action_server import G1ArmActionServer
from robot.g1.wireless_controller.wireless_controller_server import G1WirelessControllerServer

from robot.go2.sport.go2_sport_server import Go2SportServer
from robot.go2.wireless_controller.wireless_controller_server import Go2WirelessControllerServer

# 目前仅实现了 G1/Go2 的服务端, 后续可扩展 H2/R1 等机型
SUPPORTED_ROBOTS = ("g1", "go2")

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
        "--print_scene_info", action="store_true", default=False, help="打印场景信息"
    )
    parser.add_argument(
        "--band", action="store_true", default=False, help="启动虚拟吊绳"
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
    context: dict = vars(args).copy()
    
    # 初始化 DDS 通道 (domain id + 网卡)
    ChannelFactoryInitialize(args.domain_id, args.interface)

    unitree_mujoco_launcher = None
    if args.sim:
        from unitree_mujoco_launcher import UnitreeMujocoLauncher
        unitree_mujoco_launcher = UnitreeMujocoLauncher()
        unitree_mujoco_launcher.config.ROBOT = args.robot
        unitree_mujoco_launcher.config.DOMAIN_ID = args.domain_id
        unitree_mujoco_launcher.config.INTERFACE = args.interface
        unitree_mujoco_launcher.config.USE_JOYSTICK = args.joystick
        unitree_mujoco_launcher.config.PRINT_SCENE_INFORMATION = args.print_scene_info
        unitree_mujoco_launcher.config.ENABLE_ELASTIC_BAND = args.band
        unitree_mujoco_launcher.init()
        unitree_mujoco_launcher.start_simulation()
        
        context['unitree_mujoco_launcher'] = unitree_mujoco_launcher

    servers = []
    stop_event = threading.Event()

    if args.robot == "g1":
        if args.loco:
            loco_server = G1LocoServer(context)
            loco_server.Init()
            loco_server.Start()
            servers.append(loco_server)
            context['loco_server'] = loco_server
            print("[G1LocoServer] started, waiting for loco commands...")
        if args.audio:
            audio_server = G1AudioServer()
            audio_server.Init()
            audio_server.Start()
            servers.append(audio_server)
            context['audio_server'] = audio_server
            print("[G1AudioServer] started, waiting for audio commands...")
        if args.arm:
            arm_server = G1ArmActionServer()
            arm_server.Init()
            arm_server.Start()
            servers.append(arm_server)
            context['arm_server'] = arm_server
            print("[G1ArmActionServer] started, waiting for arm commands...")
        if args.joystick:
            wireless_controller_server = G1WirelessControllerServer(context)
            wireless_controller_server.Start()
            servers.append(wireless_controller_server)
            print("[G1WirelessControllerServer] started, waiting for wireless controller commands...")
    if args.robot == "go2":
        if args.loco:
            sport_server = Go2SportServer(context)
            sport_server.Init()
            sport_server.Start()
            servers.append(sport_server)
            context['sport_server'] = sport_server
            print("[Go2SportServer] started, waiting for sport commands...")
        if args.joystick:
            wireless_controller_server = Go2WirelessControllerServer(context)
            wireless_controller_server.Start()
            servers.append(wireless_controller_server)
            print("[Go2WirelessControllerServer] started, waiting for wireless controller commands...")

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
        if unitree_mujoco_launcher is not None:
            unitree_mujoco_launcher.stop_simulation()
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
