# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/go2/go2_pub.h

from unitree_sdk2py.idl.unitree_go.msg.dds_ import (
    LowCmd_,
    LowState_,
    SportModeState_,
    WirelessController_,
    MotorCmds_,
    MotorStates_,
)
from unitree_sdk2py.idl.default import (
    unitree_go_msg_dds__LowCmd_,
    unitree_go_msg_dds__LowState_,
    unitree_go_msg_dds__SportModeState_,
    unitree_go_msg_dds__WirelessController_,
    unitree_go_msg_dds__MotorCmd_,
    unitree_go_msg_dds__MotorState_,
)
from unitree_sdk2py.utils.crc import CRC

from ...common.publisher import RealTimePublisher


class LowCmd(RealTimePublisher):
    def __init__(self, topic="rt/lowcmd"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        msg = unitree_go_msg_dds__LowCmd_()
        msg.head[:] = [0xFE, 0xEF]
        msg.level_flag = 0xFF
        for motor in msg.motor_cmd:
            motor.mode = 1
        return msg

    def pre_communication(self):
        self.msg_.crc = CRC().Crc(self.msg_)


class LowState(RealTimePublisher):
    def __init__(self, topic="rt/lowstate"):
        super().__init__(topic, LowState_)
        self.joystick = None

    def _default_msg(self):
        return unitree_go_msg_dds__LowState_()

    def pre_communication(self):
        if self.joystick is not None:
            key = self.joystick.combine()
            self.msg_.wireless_remote[:] = key.buff
        self.msg_.crc = CRC().Crc(self.msg_)


class SportModeState(RealTimePublisher):
    def __init__(self, topic="rt/sportmodestate"):
        super().__init__(topic, SportModeState_)

    def _default_msg(self):
        return unitree_go_msg_dds__SportModeState_()


class WirelessController(RealTimePublisher):
    def __init__(self, topic="rt/wirelesscontroller"):
        super().__init__(topic, WirelessController_)
        self.joystick = None

    def _default_msg(self):
        return unitree_go_msg_dds__WirelessController_()

    def pre_communication(self):
        if self.joystick is not None:
            key = self.joystick.combine()
            self.msg_.lx = self.joystick.lx()
            self.msg_.ly = self.joystick.ly()
            self.msg_.rx = self.joystick.rx()
            self.msg_.ry = self.joystick.ry()
            self.msg_.keys = key.btn.value


class MotorCmds(RealTimePublisher):
    def __init__(self, topic, num=1):
        self._num = num
        super().__init__(topic, MotorCmds_)

    def _default_msg(self):
        return MotorCmds_(cmds=[unitree_go_msg_dds__MotorCmd_() for _ in range(self._num)])


class MotorStates(RealTimePublisher):
    def __init__(self, topic, num=1):
        self._num = num
        super().__init__(topic, MotorStates_)

    def _default_msg(self):
        return MotorStates_(states=[unitree_go_msg_dds__MotorState_() for _ in range(self._num)])
