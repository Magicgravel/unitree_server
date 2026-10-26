from ....common.fsm.fsm_state import FSMState
from ....common.ctrlcomp import StateAndCmd, PolicyOutput
import numpy as np

kds = [60,80,80,
       60,80,80,
       60,80,80,
       60,80,80]

kps = [5,4,4,
       5,4,4,
       5,4,4,
       5,4,4]

joint2motor_idx = [0, 1, 2,
                   3, 4, 5,
                   6, 7, 8,
                   9, 10, 11]

default_angles = [
    [0.0, 1.36, -2.65, 0.0, 1.36, -2.65, 0.0, 1.36, -2.65, 0.0, 1.36, -2.65],
    [0., 0.8, -1.5, 0., 0.8, -1.5, 0., 0.8, -1.5, 0., 0.8, -1.5],
]

control_dt = 0.02

class StandDown(FSMState):
    name = 'stand_down'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = StandDown.name
        
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
        for i in range(self.dof_size):
            self.init_dof_pos[i] = self.state_cmd.lowstate.motor_state[self.joint2motor_idx[i]].q

        # Split the fixed pose into multiple steps, moving through each
        # row of default_angles sequentially.
        self.num_poses = len(self.default_angles)
        self.pose_idx = 0
        self.start_pos = self.init_dof_pos.copy()
        self.target_pos = self.default_angles[self.pose_idx].copy()
        self.alpha = 0.
        self.cur_step = 0


    def run(self):
        self.cur_step += 1
        self.alpha = min(self.cur_step / self.num_step, 1.0)

        # Interpolate from the start pose to the current target pose.
        action = self.start_pos * (1 - self.alpha) + self.target_pos * self.alpha
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            self.policy_output.actions[motor_idx] = action[j]
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]

        # Advance to the next pose once the current step is finished.
        if self.alpha >= 1.0 and self.pose_idx < self.num_poses - 1:
            self.pose_idx += 1
            self.start_pos = self.target_pos.copy()
            self.target_pos = self.default_angles[self.pose_idx].copy()
            self.cur_step = 0
            self.alpha = 0.

    def exit(self):
        final_pose = self.default_angles[-1]
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            self.policy_output.actions[motor_idx] = final_pose[j]
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]
