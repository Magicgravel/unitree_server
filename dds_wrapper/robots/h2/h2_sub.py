# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/h2/h2_sub.h

import time

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_, HandState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorStates_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__LowCmd_,
    unitree_hg_msg_dds__LowState_,
    unitree_hg_msg_dds__HandState_,
)

from ...common.subscription import SubscriptionBase
from ...common.unitree_joystick import UnitreeJoystick, RemoteDataRx


class LowCmd(SubscriptionBase):
    def __init__(self, topic="rt/lowcmd"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_hg_msg_dds__LowCmd_()


class ArmSdk(SubscriptionBase):
    def __init__(self, topic="rt/arm_sdk"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_hg_msg_dds__LowCmd_()


class LowState(SubscriptionBase):
    def __init__(self, topic="rt/lowstate"):
        super().__init__(topic, LowState_)
        self.joystick = UnitreeJoystick()
        self.joystick_timeout_ms_ = 3000
        self._is_joystick_timeout = False
        self._last_joystick_time = None

    def _default_msg(self):
        return unitree_hg_msg_dds__LowState_()

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


class InspireHandState(SubscriptionBase):
    def __init__(self, topic="rt/inspire/state"):
        super().__init__(topic, MotorStates_)

    def _default_msg(self):
        return MotorStates_(states=[])


class Dex3LeftHandState(SubscriptionBase):
    def __init__(self, topic="rt/dex3/left/state"):
        super().__init__(topic, HandState_)

    def _default_msg(self):
        return unitree_hg_msg_dds__HandState_()


class Dex3RightHandState(SubscriptionBase):
    def __init__(self, topic="rt/dex3/right/state"):
        super().__init__(topic, HandState_)

    def _default_msg(self):
        return unitree_hg_msg_dds__HandState_()
