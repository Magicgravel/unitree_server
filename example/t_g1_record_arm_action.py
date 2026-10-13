"""
录制 G1 机器人上肢动作数据并保存为 CSV。

脚本订阅 G1 的 `rt/lowstate` 话题, 按照指定频率记录 14 个上肢关节
(左/右肩、肘、腕) 的关节角度, 并将数据保存为 CSV 文件。

用法 / Usage:
    # 执行自定义动作 "shake hand" 并录制 5 秒
    python3 t_g1_record_arm_action.py --interface lo --name "shake hand" --hz 50 --duration 5

    # 不执行动作, 被动录制 (拖拽示教 / 手动摆臂), 按 Ctrl+C 停止
    python3 t_g1_record_arm_action.py --interface eth0 --hz 100

说明 / Notes:
    - `--name` 为可选参数, 指定要执行的 G1 自定义上肢动作名称。
    - `--duration` 为 0.0 时持续录制, 直到按下 Ctrl+C 手动停止。
    - CSV 第一列为相对时间戳 (秒), 其余 14 列为上肢关节角度 (弧度)。
    - 仿真模式下 unitree_server 的 G1ArmActionServer 只记录动作名, 不会真实驱动
      仿真机器人, 因此 `--name` 在仿真中通常不会产生运动。
"""

import argparse
import csv
import os
import sys
import threading
import time
from enum import IntEnum

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

LOWSTATE_TOPIC = "rt/lowstate"


class G1_29_JointArmIndex(IntEnum):
    """G1 29DOF 上肢关节在 LowState_.motor_state 中的索引."""

    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristYaw = 21
    kLeftWristyaw = 21  # 兼容旧拼写 (typo)

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28


# 与 G1_29_JointArmIndex 一一对应 (顺序一致) 的 CSV 列名
ARM_JOINT_NAMES = [
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_shoulder_yaw",
    "left_elbow",
    "left_wrist_roll",
    "left_wrist_pitch",
    "left_wrist_yaw",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_shoulder_yaw",
    "right_elbow",
    "right_wrist_roll",
    "right_wrist_pitch",
    "right_wrist_yaw",
]

# 14 个上肢关节的电机索引 (15 ~ 28)
ARM_JOINT_INDICES = [
    G1_29_JointArmIndex.kLeftShoulderPitch,
    G1_29_JointArmIndex.kLeftShoulderRoll,
    G1_29_JointArmIndex.kLeftShoulderYaw,
    G1_29_JointArmIndex.kLeftElbow,
    G1_29_JointArmIndex.kLeftWristRoll,
    G1_29_JointArmIndex.kLeftWristPitch,
    G1_29_JointArmIndex.kLeftWristYaw,
    G1_29_JointArmIndex.kRightShoulderPitch,
    G1_29_JointArmIndex.kRightShoulderRoll,
    G1_29_JointArmIndex.kRightShoulderYaw,
    G1_29_JointArmIndex.kRightElbow,
    G1_29_JointArmIndex.kRightWristRoll,
    G1_29_JointArmIndex.kRightWristPitch,
    G1_29_JointArmIndex.kRightWristYaw,
]


def default_output_path(name):
    """根据动作名生成默认的 CSV 保存路径."""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "robot", "g1", "arm", "arm_action_data",
    )
    if name:
        safe_name = name.strip().replace("/", "_").replace(" ", "_")
        return os.path.join(data_dir, f"{safe_name}.csv")
    return os.path.join(data_dir, time.strftime("arm_action_%Y%m%d_%H%M%S.csv"))


class ArmActionRecorder:
    def __init__(self, hz, name, duration, output):
        self.hz = hz
        self.name = name
        self.duration = duration
        self.output = output

        self._lock = threading.Lock()
        self._latest_state = None
        self._samples = []
        self._subscriber = None
        self._arm_client = None

    def _on_low_state(self, msg: LowState_):
        """DDS 回调: 缓存最新一帧低电平状态 (线程安全)."""
        with self._lock:
            self._latest_state = msg

    def start(self):
        """订阅 lowstate 并等待首帧数据到达."""
        self._subscriber = ChannelSubscriber(LOWSTATE_TOPIC, LowState_)
        self._subscriber.Init(self._on_low_state, 10)

        print("Waiting for lowstate ...")
        while self._latest_state is None:
            time.sleep(0.1)
        print("Lowstate received, ready to record.")

    def execute_action(self):
        """可选: 触发 G1 自定义上肢动作."""
        if not self.name:
            print("No action specified, recording passively.")
            return

        from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient

        try:
            self._arm_client = G1ArmActionClient()
            self._arm_client.SetTimeout(10.0)
            self._arm_client.Init()
            code = self._arm_client.ExecuteCustomAction(self.name)
            print(f"Execute custom action '{self.name}', ret: {code}")
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] failed to execute action '{self.name}': {exc}")

    def stop_action(self):
        """可选: 停止自定义上肢动作."""
        if self._arm_client is None:
            return
        try:
            self._arm_client.StopCustomAction()
            print("Custom action stopped.")
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] failed to stop action: {exc}")

    def record(self):
        """按指定频率采样上肢关节角度, 直到到达时长或收到 Ctrl+C."""
        period = 1.0 / self.hz
        start = time.monotonic()
        next_tick = start
        print(f"Recording at {self.hz} Hz. Press Ctrl+C to stop.")

        while True:
            now = time.monotonic()
            if self.duration > 0.0 and now - start >= self.duration:
                break

            with self._lock:
                state = self._latest_state

            if state is not None:
                row = [now - start]
                for idx in ARM_JOINT_INDICES:
                    row.append(float(state.motor_state[idx].q))
                self._samples.append(row)

            next_tick += period
            sleep_time = next_tick - time.monotonic()
            if sleep_time > 0.0:
                time.sleep(sleep_time)
            else:
                next_tick = time.monotonic()

    def save(self):
        """将采样数据写入 CSV 文件."""
        if not self._samples:
            print("No samples recorded, nothing to save.")
            return

        output_dir = os.path.dirname(self.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(self.output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp"] + ARM_JOINT_NAMES)
            writer.writerows(self._samples)

        print(f"Saved {len(self._samples)} samples to {self.output}")


def main():
    parser = argparse.ArgumentParser(
        description="Record G1 arm joint angles and save to CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--interface", type=str, default="lo",
        help="Network interface connected to the robot",
    )
    parser.add_argument(
        "--domain-id", type=int, default=0,
        help="DDS domain id",
    )
    parser.add_argument(
        "--hz", type=int, default=50,
        help="Frequency in Hz at which to record the arm action",
    )
    parser.add_argument(
        "--name", type=str, default=None,
        help="Name of the custom arm action to execute (optional)",
    )
    parser.add_argument(
        "--duration", type=float, default=0.0,
        help="Duration in seconds for which to record. 0.0 means manual stop (Ctrl+C).",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output CSV path (defaults to robot/g1/arm/arm_action_data/<name>.csv)",
    )
    args = parser.parse_args()

    if args.hz <= 0:
        print("Invalid --hz, must be a positive integer.")
        sys.exit(1)

    output = args.output or default_output_path(args.name)

    # 初始化 DDS 通道 (domain id + 网卡)
    ChannelFactoryInitialize(args.domain_id, args.interface)

    recorder = ArmActionRecorder(
        hz=args.hz,
        name=args.name,
        duration=args.duration,
        output=output,
    )

    try:
        recorder.start()
        recorder.execute_action()
        recorder.record()
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
    finally:
        recorder.stop_action()
        recorder.save()


if __name__ == "__main__":
    main()