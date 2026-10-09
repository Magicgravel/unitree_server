# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.

from enum import IntEnum


class JointIndex(IntEnum):
    # Left leg
    LeftHipPitch = 0
    LeftHipRoll = 1
    LeftHipYaw = 2
    LeftKnee = 3
    LeftAnklePitch = 5
    LeftAnkleRoll = 4

    # Right leg
    RightHipPitch = 6
    RightHipRoll = 7
    RightHipYaw = 8
    RightKnee = 9
    RightAnklePitch = 11
    RightAnkleRoll = 10

    WaistYaw = 14
    WaistRoll = 12
    WaistPitch = 13

    # Left arm
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 21
    LeftWristPitch = 20
    LeftWristYaw = 19

    # Right arm
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 28
    RightWristPitch = 27
    RightWristYaw = 26


ArmJoints = [
    JointIndex.LeftShoulderPitch, JointIndex.LeftShoulderRoll,
    JointIndex.LeftShoulderYaw, JointIndex.LeftElbow,
    JointIndex.LeftWristRoll, JointIndex.LeftWristPitch,
    JointIndex.LeftWristYaw,
    JointIndex.RightShoulderPitch, JointIndex.RightShoulderRoll,
    JointIndex.RightShoulderYaw, JointIndex.RightElbow,
    JointIndex.RightWristRoll, JointIndex.RightWristPitch,
    JointIndex.RightWristYaw,
]
