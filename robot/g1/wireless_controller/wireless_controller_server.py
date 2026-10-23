"""G1 无线手柄控制服务.

订阅 ``rt/wirelesscontroller`` 话题, 使用 ``unitree_joystick_dsl`` 解析按键组合,
并将命中的组合映射到 loco / audio / arm 服务对应的动作上。

``key_mapping`` 的键为 DSL 表达式字符串, 值为命中后执行的回调函数。
表达式示例:
    "LT(2s) + B"            LT 长按 2 秒且 B 被按住
    "start.on_pressed"      start 本帧刚按下 (单帧触发)
    "up.on_pressed"         up 方向本帧刚按下

所有动作均按“上升沿”触发: 只有表达式从 False 变为 True 的那一帧才执行,
避免长按组合在按住期间每帧重复触发。
"""

import json
import threading
import time

from robot.g1.loco.g1_loco_server import FSM_ID, G1LocoServer
from robot.g1.audio.g1_audio_server import G1AudioServer
from robot.g1.arm.g1_arm_action_server import G1ArmActionServer
from robot.common.wireless_controller import WirelessController


class G1WirelessControllerServer:
    def __init__(
        self,
        context: dict,
        rate_hz: float=200.0,
    ):
        self.loco_server: G1LocoServer = context.get('loco_server', None)
        self.audio_server: G1AudioServer = context.get('audio_server', None)
        self.arm_action_server: G1ArmActionServer = context.get('arm_server', None)

        self.rate_hz = rate_hz
        self.period = 1.0 / rate_hz

        self._thread = None
        self._stop_event = threading.Event()

        self.wireless_controller = WirelessController()
        self.wireless_controller.Init()
        
        self.key_mapping_loco = {
            "LT + Y": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kInvalid})),
            "LT(2s) + B": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kPassive})),
            "RB + RT + X": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kWjcgetup})),
            "start.on_pressed": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kCpyWalkRun29dofs})),
            
            "LT + RT": lambda: print("调试模式"),
            "LS + RS": lambda: (mj_launcher.reset() if (mj_launcher := context.get("unitree_mujoco_launcher")) else None),
        }
        self.key_mapping_audio = {
            "up.on_pressed": lambda: self.audio_server._OnSetVolume(10),
            "down.on_pressed": lambda: self.audio_server._OnSetVolume(-10),
        }
        self.key_mapping_arm = {
            "X.on_pressed": lambda: self.arm_action_server._OnExecuteAction(json.dumps({"data": "shake hand"})),
        }

        self.key_mapping = {}
        if self.loco_server is not None:
            self.key_mapping.update(self.key_mapping_loco)
        if self.audio_server is not None:
            self.key_mapping.update(self.key_mapping_audio)
        if self.arm_action_server is not None:
            self.key_mapping.update(self.key_mapping_arm)
        
        self.wireless_controller.set_key_mapping(self.key_mapping)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def update(self):
        self.wireless_controller.update()
        self.loco_server._motion_controller.state_cmd.vel_cmd[0] = self.wireless_controller.raw.RF_RX.ly * 0.5
        self.loco_server._motion_controller.state_cmd.vel_cmd[1] = self.wireless_controller.raw.RF_RX.lx * 0.5
        self.loco_server._motion_controller.state_cmd.vel_cmd[2] = self.wireless_controller.raw.RF_RX.rx * -1.0

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.update()
            self._stop_event.wait(timeout=self.period)

    def Start(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run_loop,
                name="wireless_controller_loop",
                daemon=True,
            )
            self._thread.start()

    def Stop(self):
        self._stop_event.set()
