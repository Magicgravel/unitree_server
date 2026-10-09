# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/r1/r1_pub.h

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_

from ...common.publisher import RealTimePublisher
from .defines import JointIndex


class ArmSdk(RealTimePublisher):
    JOINTS = [
        JointIndex.LeftShoulderPitch,
        JointIndex.LeftShoulderRoll,
        JointIndex.LeftShoulderYaw,
        JointIndex.LeftElbow,
        JointIndex.LeftWristRoll,
        JointIndex.RightShoulderPitch,
        JointIndex.RightShoulderRoll,
        JointIndex.RightShoulderYaw,
        JointIndex.RightElbow,
        JointIndex.RightWristRoll,
        JointIndex.WaistYaw,
        JointIndex.HeadPitch,
        JointIndex.HeadYaw,
    ]

    def __init__(self, topic="rt/arm_sdk"):
        super().__init__(topic, LowCmd_)

    def _default_msg(self):
        return unitree_hg_msg_dds__LowCmd_()

    def weight(self, coe=None):
        """Get/set the arm sdk weight (0.0..1.0)."""
        if coe is None:
            return float(self.msg_.mode_pr) / 100.0
        self.msg_.mode_pr = max(0, min(100, int(coe * 100.0)))
        return None
