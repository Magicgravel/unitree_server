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
from robot.common.unitree_joystick import (
    UnitreeJoystick,
    compile_dsl,
    get_key,
)
from robot.common.wireless_controller import WirelessController

# DSL 键名 -> WirelessController 按键属性名
_BUTTON_MAP = {
    "back": "Select",
    "start": "Start",
    "LB": "L1",
    "RB": "R1",
    "LT": "L2",
    "RT": "R2",
    "A": "A",
    "B": "B",
    "X": "X",
    "Y": "Y",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "F1": "F1",
    "F2": "F2",
    # 注意: WirelessController 未暴露 LS/RS (摇杆按下), 对应键恒为未按下。
}

# DSL 摇杆键名 -> WirelessController 摇杆轴属性名
_AXIS_MAP = {
    "lx": "Lx",
    "ly": "Ly",
    "rx": "Rx",
    "ry": "Ry",
}

# 摇杆轴判定为“按下”的阈值
AXIS_THRESHOLD = 0.5


class G1WirelessControllerServer:
    def __init__(
        self,
        loco_server: G1LocoServer=None,
        audio_server: G1AudioServer=None,
        arm_action_server: G1ArmActionServer=None,
        rate_hz: float=50.0,
    ):
        self.loco_server = loco_server
        self.audio_server = audio_server
        self.arm_action_server = arm_action_server

        self.rate_hz = rate_hz
        self.period = 1.0 / rate_hz

        self.wireless_controller = WirelessController()
        self.wireless_controller.Init()

        self.joy = UnitreeJoystick()
        
        self.key_mapping_loco = {
            "LT(2s) + B": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kPassive})),
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

        # 编译 DSL 表达式
        self._predicates = {
            expr: compile_dsl(expr) for expr in self.key_mapping
        }
        # 上一帧各表达式的值, 用于上升沿检测
        self._prev_state = {expr: False for expr in self.key_mapping}

        self._last_update = None
        self._stop_event = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------
    # 状态同步
    # ------------------------------------------------------------------
    @staticmethod
    def _update_key(key, pressed, dt):
        key.on_pressed = pressed and not key.pressed
        key.on_released = (not pressed) and key.pressed
        key.pressed = pressed
        if pressed:
            key.pressed_time += dt
        else:
            key.pressed_time = 0.0

    def _sync_joy(self):
        now = time.monotonic()
        dt = self.period if self._last_update is None else (now - self._last_update)
        self._last_update = now

        for dsl_name, attr in _BUTTON_MAP.items():
            key = get_key(self.joy, dsl_name)
            pressed = bool(getattr(self.wireless_controller, attr))
            self._update_key(key, pressed, dt)

        for dsl_name, attr in _AXIS_MAP.items():
            key = get_key(self.joy, dsl_name)
            pressed = abs(getattr(self.wireless_controller, attr)) >= AXIS_THRESHOLD
            self._update_key(key, pressed, dt)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def update(self):
        self._sync_joy()
        for expr, pred in self._predicates.items():
            now = pred(self.joy)
            if now and not self._prev_state.get(expr, False):
                action = self.key_mapping[expr]
                try:
                    action()
                    print(f"[G1WirelessControllerServer] triggered: {expr!r}")
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"[G1WirelessControllerServer] action {expr!r} failed: {exc}"
                    )
            self._prev_state[expr] = now

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
