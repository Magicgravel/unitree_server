import struct
import threading

from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
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

TOPIC_LOWSTATE = "rt/lowstate"

class WirelessController:
    def __init__(self):
        self.lowstate: LowState_ = unitree_go_msg_dds__LowState_()
        self.unitree_joystick: UnitreeJoystick = UnitreeJoystick()
        self.raw = REMOTE_DATA_RX()

        self._received: bool = False
        self.key_mapping: dict = {}
        self._compiled: dict = {}
        self._prev_state: dict = {}
        self._lock = threading.Lock()

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber(TOPIC_LOWSTATE, LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
    
    def LowStateMessageHandler(self, msg: LowState_):
        self.lowstate = msg
        self._received = True

        # 更新 UnitreeJoystick 的状态
        self.raw = REMOTE_DATA_RX()
        # 把 self.lowstate 的无线遥控器数据提取到 raw 中
        self.raw.RF_RX.btn.value = self.lowstate.wireless_remote[2]
        self.raw.RF_RX.lx = struct.unpack("f", self.lowstate.wireless_remote[4:8])[0]
        self.raw.RF_RX.ly = struct.unpack("f", self.lowstate.wireless_remote[20:24])[0]
        self.raw.RF_RX.rx = struct.unpack("f", self.lowstate.wireless_remote[8:12])[0]
        self.raw.RF_RX.ry = struct.unpack("f", self.lowstate.wireless_remote[12:16])[0]
        with self._lock:
            self.unitree_joystick.extract(self.raw)
    
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
                    print(f"[WirelessController] triggering callback for {expr!r}")
                    callback()
                except Exception as e:
                    print(f"[WirelessController] callback for {expr!r} failed: {e}")
        
        # 把当前按下的按键状态打印出来, 便于调试
        # if self._received:
        #     with self._lock:
        #         btn_value = self.raw.RF_RX.btn.value
        #         lx = self.raw.RF_RX.lx
        #         ly = self.raw.RF_RX.ly
        #         rx = self.raw.RF_RX.rx
        #         ry = self.raw.RF_RX.ry
        #         print(f"[WirelessController] current button value: {btn_value}, lx: {lx}, ly: {ly}, rx: {rx}, ry: {ry}")