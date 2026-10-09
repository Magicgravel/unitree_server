# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/go2/go2_sub.h

import time

from unitree_sdk2py.idl.unitree_go.msg.dds_ import (
    LowCmd_,
    LowState_,
    SportModeState_,
    MotorCmds_,
    MotorStates_,
)
from unitree_sdk2py.idl.default import (
    unitree_go_msg_dds__LowCmd_,
    unitree_go_msg_dds__LowState_,
    unitree_go_msg_dds__SportModeState_,
    unitree_go_msg_dds__MotorCmd_,
    unitree_go_msg_dds__MotorState_,
)

from ...common.subscription import SubscriptionBase
from ...common.unitree_joystick import UnitreeJoystick, RemoteDataRx


class LowState(SubscriptionBase):
    def __init__(self, topic="rt/lowstate"):
        super().__init__(topic, LowState_)
        self.joystick = UnitreeJoystick()
        self.joystick_timeout_ms_ = 3000
        self._is_joystick_timeout = False
        self._last_joystick_time = None

    def _default_msg(self):
        return unitree_go_msg_dds__LowState_()

    def update(self):
        with self._mutex:
            wireless_remote = self.msg_.wireless_remote
            if all(byte == 0 for byte in wireless_remote):
                now = time.monotonic()
                if (
                    self._last_joystick_time is None
                    or (now - self._last_joystick_time) > (self.joystick_timeout_ms_ / 1000.0)
                ):
                    self._is_joystick_timeout = True
            else:
                self._last_joystick_time = time.monotonic()
                self._is_joystick_timeout = False

            key = RemoteDataRx.unpack(wireless_remote)
            self.joystick.extract(key)

    def isJoystickTimeout(self):
        return self._is_joystick_timeout


class LowCmd(SubscriptionBase):
    def __init__(self, topic="rt/lowcmd"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_go_msg_dds__LowCmd_()


class SportModeState(SubscriptionBase):
    def __init__(self, topic="rt/sportmodestate"):
        super().__init__(topic, SportModeState_)

    def _default_msg(self):
        return unitree_go_msg_dds__SportModeState_()

    def gaitType(self):
        return self.msg_.gait_type

    def position(self):
        return self.msg_.position

    def velocity(self):
        return self.msg_.velocity


class MotorStates(SubscriptionBase):
    def __init__(self, topic, num=0):
        self._num = num
        super().__init__(topic, MotorStates_)

    def _default_msg(self):
        if self._num != 0:
            return MotorStates_(states=[unitree_go_msg_dds__MotorState_() for _ in range(self._num)])
        return MotorStates_(states=[])


class MotorCmds(SubscriptionBase):
    def __init__(self, topic, num=0):
        self._num = num
        super().__init__(topic, MotorCmds_)

    def _default_msg(self):
        if self._num != 0:
            return MotorCmds_(cmds=[unitree_go_msg_dds__MotorCmd_() for _ in range(self._num)])
        return MotorCmds_(cmds=[])
