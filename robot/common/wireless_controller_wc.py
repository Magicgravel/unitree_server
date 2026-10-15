import threading

from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__WirelessController_
from .unitree_joystick import (
    UnitreeJoystick,
    compile_dsl,
    REMOTE_DATA_RX,
)

# key_mapping example
# key_mapping = {
#     "LT(2s) + B": lambda: self.loco_server._OnSetFsmId(json.dumps({"data": FSM_ID.kPassive})),
#     "up.on_pressed": lambda: self.audio_server._OnSetVolume(10),
#     "down.on_pressed": lambda: self.audio_server._OnSetVolume(-10),
# }

TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"

class WirelessController:
    def __init__(self):
        self.wireless_controller: WirelessController_ = unitree_go_msg_dds__WirelessController_()
        self.unitree_joystick = UnitreeJoystick()

        self.key_mapping: dict = {}
        self._compiled: dict = {}
        self._prev_state: dict = {}
        self._lock = threading.Lock()

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber(TOPIC_WIRELESS_CONTROLLER, WirelessController_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
    
    def LowStateMessageHandler(self, msg: WirelessController_):
        self.wireless_controller = msg

        # 更新 UnitreeJoystick 的状态
        raw = REMOTE_DATA_RX()
        raw.RF_RX.btn.value = msg.keys
        raw.RF_RX.lx = msg.lx
        raw.RF_RX.ly = msg.ly
        raw.RF_RX.rx = msg.rx
        raw.RF_RX.ry = msg.ry
        with self._lock:
            self.unitree_joystick.extract(raw)
    
    def set_key_mapping(self, mapping: dict):
        self.key_mapping = mapping or {}
        # 编译 DSL 表达式
        self._compiled = {}
        self._prev_state = {}
        for expr, callback in self.key_mapping.items():
            self._compiled[expr] = compile_dsl(expr)
            self._prev_state[expr] = False
    
    def update(self):
        # 评估所有 DSL 表达式, 命中时按“上升沿”触发回调
        triggered = []
        with self._lock:
            for expr, predicate in self._compiled.items():
                state = bool(predicate(self.unitree_joystick))
                if state and not self._prev_state.get(expr, False):
                    triggered.append(expr)
                self._prev_state[expr] = state

        for expr in triggered:
            callback = self.key_mapping.get(expr)
            if callback is not None:
                try:
                    callback()
                except Exception as e:
                    print(f"[WirelessController] callback for {expr!r} failed: {e}")