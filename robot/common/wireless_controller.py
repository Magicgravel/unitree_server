from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__WirelessController_
from .unitree_joystick import (
    UnitreeJoystick,
    compile_dsl,
    get_key,
)

TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"

class WirelessController:
    def __init__(self):
        self.wireless_controller: WirelessController_ = unitree_go_msg_dds__WirelessController_()
        self.unitree_joystick = UnitreeJoystick()

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber(TOPIC_WIRELESS_CONTROLLER, WirelessController_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
    
    def LowStateMessageHandler(self, msg: WirelessController_):
        self.wireless_controller = msg

        self.lx = self.wireless_controller.lx
        self.rx = self.wireless_controller.rx
        self.ry = self.wireless_controller.ry
        self.ly = self.wireless_controller.ly

        keys = self.wireless_controller.keys
        self.r1 = (keys >> 0) & 1
        self.l1 = (keys >> 1) & 1
        self.start = (keys >> 2) & 1
        self.select = (keys >> 3) & 1
        self.r2 = (keys >> 4) & 1
        self.l2 = (keys >> 5) & 1
        self.f1 = (keys >> 6) & 1
        self.f2 = (keys >> 7) & 1
        self.a = (keys >> 8) & 1
        self.b = (keys >> 9) & 1
        self.x = (keys >> 10) & 1
        self.y = (keys >> 11) & 1
        self.up = (keys >> 12) & 1
        self.right = (keys >> 13) & 1
        self.down = (keys >> 14) & 1
        self.left = (keys >> 15) & 1
    
    def set_key_mapping(self, mapping: dict):
        self.key_mapping = mapping
        # 编译 DSL 表达式
        self._predicates = {
            expr: compile_dsl(expr) for expr in self.key_mapping
        }
        # 上一帧各表达式的值, 用于上升沿检测
        self._prev_state = {expr: False for expr in self.key_mapping}
    
    def update(self):
        context = {
            "lx": self.lx,
            "rx": self.rx,
            "ly": self.ly,
            "ry": self.ry,
            "l1": self.l1,
            "l2": self.l2,
            "r1": self.r1,
            "r2": self.r2,
            "a": self.a,
            "b": self.b,
            "x": self.x,
            "y": self.y,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
            "select": self.select,
            "f1": self.f1,
            "f2": self.f2,
            "start": self.start,
        }

        for expr, predicate in self._predicates.items():
            self._prev_state[expr] = predicate(context)
        self.unitree_joystick.update(self._prev_state)