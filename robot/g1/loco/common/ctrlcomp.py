"""
定义控制循环中使用的核心数据结构。
StateAndCmd 类：用于存储机器人的当前状态（关节角度 q, 速度 dq, IMU 等）以及接收到的指令（速度指令, 技能指令）。
               类似于一个数据黑板，在主循环和策略之间传递信息。
PolicyOutput 类：用于标准化策略网络的输出格式（动作 actions, Kp, Kd）。
"""

import numpy as np
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

class StateAndCmd:
    def __init__(self, num_joints):
        self.lowstate: LowState_ = None
        self.imu_state = None
        self.motor_state = None
        # robot state
        self.num_joints = num_joints
        self.q = np.zeros(num_joints, dtype=np.float32)
        self.dq = np.zeros(num_joints, dtype=np.float32)
        self.ddq = np.zeros(num_joints, dtype=np.float32)
        self.tau_est = np.zeros(num_joints, dtype=np.float32)
        self.gravity_ori = np.array([0., 0., 1.])
        self.base_quat = np.array([1., 0., 0., 0.])
        self.ang_vel = np.zeros(3)
        # joy cmd
        self.vel_cmd = np.zeros(3)

class PolicyOutput:
    def __init__(self, num_joints):
        # actions
        self.actions = np.zeros(num_joints, dtype=np.float32)
        self.kps = np.zeros(num_joints, dtype=np.float32)
        self.kds = np.zeros(num_joints, dtype=np.float32)
        