from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
import numpy as np

kps = [100, 100, 100, 150, 40, 40,
      100, 100, 100, 150, 40, 40,
      300, 300, 300,
      100, 100, 50, 50, 20, 20, 20,
      100, 100, 50, 50, 20, 20, 20,]

kds = [2, 2, 2, 4, 2, 2,
      2, 2, 2, 4, 2, 2,
      3,3,3,
      2,2,2,2,1,1,1,
      2,2,2,2,1,1,1]

joint2motor_idx = [0, 1, 2, 3, 4,  5,
                  6, 7, 8, 9, 10, 11,
                  12, 13, 14, 
                  15, 16, 17, 18, 19, 20, 21, 
                  22, 23, 24, 25, 26, 27, 28]

default_angles = [-0.2,  0.0,  0.0,  0.42, -0.23, 0.0, 
                 -0.2,  0.0,  0.0,  0.42, -0.23, 0.0,
                  0, 0, 0,
                  0.35, 0.18, 0, 0.87, 0, 0, 0,
                  0.35, -0.18, 0, 0.87, 0, 0, 0,
                  ]

control_dt = 0.02

class FixedPose(FSMState):
    name = 'fixed_pose'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = FixedPose.name
        
        self.state_cmd: StateAndCmd = kwargs.get("state_cmd")
        self.policy_output: PolicyOutput = kwargs.get("policy_output")
        
        self.alpha = 0.
        self.cur_step = 0
        
        self.kds = np.array(kds, dtype=np.float32)
        self.kps = np.array(kps, dtype=np.float32)
        self.default_angles = np.array(default_angles, dtype=np.float32)
        self.joint2motor_idx = np.array(joint2motor_idx, dtype=np.int32)
        self.control_dt = control_dt
    
    def enter(self):
        print("Moving to default pos.")
        self.total_time = 3.0
        self.num_step = int(self.total_time / self.control_dt)
        self.dof_size = len(self.joint2motor_idx)
        self.init_dof_pos = np.zeros(self.dof_size, dtype=np.float32)
        self.alpha = 0.
        self.cur_step = 0
        for i in range(self.dof_size):
            self.init_dof_pos[i] = self.state_cmd.lowstate.motor_state[self.joint2motor_idx[i]].q
        
        
    def run(self):
        self.cur_step += 1
        self.alpha = min(self.cur_step / self.num_step, 1.0)
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            target_pos = self.default_angles[j]
            self.policy_output.actions[motor_idx] = self.init_dof_pos[j] * (1 - self.alpha) + target_pos * self.alpha
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]
    
    def exit(self):
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            self.policy_output.actions[motor_idx] = self.default_angles[j]
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]
