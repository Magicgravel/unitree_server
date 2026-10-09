# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/h2/h2_pub.h

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__LowCmd_,
    unitree_hg_msg_dds__LowState_,
)
from unitree_sdk2py.utils.crc import CRC

from ...common.publisher import RealTimePublisher
from . import h2_sub


class LowState(RealTimePublisher):
    def __init__(self, topic="rt/lowstate"):
        super().__init__(topic, LowState_)
        self.joystick = None

    def _default_msg(self):
        return unitree_hg_msg_dds__LowState_()

    def pre_communication(self):
        if self.joystick is not None:
            key = self.joystick.combine()
            self.msg_.wireless_remote[:] = key.buff
        self.msg_.crc = CRC().Crc(self.msg_)


class LowCmd(RealTimePublisher):
    def __init__(self, topic="rt/lowcmd"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_hg_msg_dds__LowCmd_()

    def check_mode_machine(self, lowstate=None):
        sub = h2_sub.LowState() if lowstate is None else lowstate
        sub.wait_for_connection()
        m_sub = sub.msg_.mode_machine
        m_pub = self.msg_.mode_machine

        # 0: simulation environment
        return not (m_sub != 0 and m_sub != m_pub)

    def pre_communication(self):
        self.msg_.crc = CRC().Crc(self.msg_)


class ArmSdk(RealTimePublisher):
    def __init__(self, topic="rt/arm_sdk"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_hg_msg_dds__LowCmd_()

    def weight(self, coe=None):
        """Enable arm sdk. Get the weight if coe is omitted."""
        if coe is None:
            return self.msg_.motor_cmd[31].q
        self.msg_.motor_cmd[31].q = max(0.0, min(1.0, coe))
        return None
