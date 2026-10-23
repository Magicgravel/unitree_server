"""Go2 无线手柄控制服务.

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

import threading

from robot.go2.sport.go2_sport_server import Go2SportServer
from robot.common.wireless_controller import WirelessController


class Go2WirelessControllerServer:
    def __init__(
        self,
        context: dict,
        rate_hz: float=200.0,
    ):
        self.sport_server: Go2SportServer = context.get('sport_server', None)

        self.rate_hz = rate_hz
        self.period = 1.0 / rate_hz

        self._thread = None
        self._stop_event = threading.Event()

        self.wireless_controller = WirelessController()
        self.wireless_controller.Init()
        
        self.key_mapping_sport = {
            "LT(2s) + B": lambda: self.sport_server._OnDamp(),
            "start.on_pressed": lambda: self.sport_server._OnRecoveryStand(),
            
            "LT + RT": lambda: print("调试模式"),
            "LS + RS": lambda: (mj_launcher.reset() if (mj_launcher := context.get("unitree_mujoco_launcher")) else None),
        }

        self.key_mapping = {}
        if self.sport_server is not None:
            self.key_mapping.update(self.key_mapping_sport)

        self.wireless_controller.set_key_mapping(self.key_mapping)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def update(self):
        self.wireless_controller.update()
        self.sport_server._motion_controller.state_cmd.vel_cmd[0] = self.wireless_controller.raw.RF_RX.ly * 0.5
        self.sport_server._motion_controller.state_cmd.vel_cmd[1] = self.wireless_controller.raw.RF_RX.lx * 0.5
        self.sport_server._motion_controller.state_cmd.vel_cmd[2] = self.wireless_controller.raw.RF_RX.rx * -1.0

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
