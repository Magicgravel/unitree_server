import struct
import threading

from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
from .gamepad_patch import GamepadPatch
from .unitree_joystick import (
    UnitreeJoystick,
    compile_dsl,
    REMOTE_DATA_RX,
)

TOPIC_LOWSTATE = "rt/lowstate"

class WirelessController:
    def __init__(self):
        self.lowstate: LowState_ = unitree_go_msg_dds__LowState_()
        self.gamepad_patch: GamepadPatch = GamepadPatch()
        self.unitree_joystick: UnitreeJoystick = UnitreeJoystick()
        self.raw = REMOTE_DATA_RX()

        self.key_mapping: dict = {}
        self._compiled: dict = {}
        self._prev_state: dict = {}
        self._lock = threading.Lock()
        self._msg_count: int = 0

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber(TOPIC_LOWSTATE, LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
    
    def LowStateMessageHandler(self, msg: LowState_):
        self.lowstate = msg
        self._msg_count += 1

        # 更新 UnitreeJoystick 的状态
        self.raw.buff = bytes(msg.wireless_remote)
        with self._lock:
            self.unitree_joystick.extract(self.raw)
            self.gamepad_patch.patch(self.unitree_joystick)
    
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
        
        # self.print_status()
    
    def print_status(self) -> None:
        def _pressed_keys(joy: UnitreeJoystick):
            names = ["A","B","X","Y","LB","RB","back","start","up","down","left","right","LT","RT"]
            out = []
            for name in names:
                key = getattr(joy, name if name in ("A", "B", "X", "Y", "LB", "RB", "LT", "RT") else name)
                if key.pressed:
                    out.append(name)
            return out
        
        with self._lock:
            pressed = _pressed_keys(self.unitree_joystick)
            lx = self.unitree_joystick.lx.data
            ly = self.unitree_joystick.ly.data
            rx = self.unitree_joystick.rx.data
            ry = self.unitree_joystick.ry.data
            msg_count = self._msg_count
            hits = []
            for expr, pred in self._compiled.items():
                state = bool(pred(self.unitree_joystick))
                if state and not self._prev_state[expr]:
                    hits.append(expr)
                self._prev_state[expr] = state

            # 方便核对原始 bitfield
            btn_u16 = struct.unpack("<H", bytes(self.raw.buff[2:4]))[0]

        print(
            f"\rmsg={msg_count:<7} btn=0x{btn_u16:04x} pressed={pressed!s:<40} "
            f"lx={lx:+.2f} ly={ly:+.2f} rx={rx:+.2f} ry={ry:+.2f}",
            end="",
            flush=True,
        )
        for expr in hits:
            print(f"\n[DSL HIT] {expr}")