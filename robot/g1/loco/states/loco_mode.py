from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
import numpy as np
import yaml
import time
import os
import onnxruntime as ort

current_dir = os.path.dirname(os.path.abspath(__file__))
policy_path = os.path.join(current_dir, "../policy")

class LocoMode(FSMState):
    name = 'loco'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = LocoMode.name
        
        self.state_cmd: StateAndCmd = kwargs.get("state_cmd")
        self.policy_output: PolicyOutput = kwargs.get("policy_output")
        
        # Load the correct parameter and policy files for velocity control
        param_file = os.path.join(policy_path, "velocity/v0/params/deploy.yaml")
        policy_file = os.path.join(policy_path, "velocity/v0/exported/policy_v9.onnx")
        
        # 1. Setup ONNX Inference Session
        self.sess = ort.InferenceSession(policy_file)
        self.input_name = self.sess.get_inputs()[0].name
        self.output_name = self.sess.get_outputs()[0].name
        
        # 2. Parse config from deploy.yaml
        with open(param_file, 'r') as f:
            config = yaml.safe_load(f)
            
        self.dt = config.get("step_dt", 0.02)
        self.joint2motor_idx = config["joint_ids_map"]
        self.num_actions = len(self.joint2motor_idx)
        self.default_angles = np.array(config["default_joint_pos"], dtype=np.float32)
        
        # Actions configuration
        self.action_scale = np.array(config["actions"]["JointPositionAction"]["scale"], dtype=np.float32)
        
        # Controller configuration
        stiffness = np.array(config["stiffness"], dtype=np.float32)
        damping = np.array(config["damping"], dtype=np.float32)
        self.kps_reorder = np.zeros(len(self.state_cmd.q) if self.state_cmd else 29, dtype=np.float32)
        self.kds_reorder = np.zeros(len(self.state_cmd.q) if self.state_cmd else 29, dtype=np.float32)
        for i, motor_idx in enumerate(self.joint2motor_idx):
            self.kps_reorder[motor_idx] = stiffness[i]
            self.kds_reorder[motor_idx] = damping[i]
        
        # Commands configuration (velocity_commands)
        ranges = config["commands"]["base_velocity"]["ranges"]
        self.range_velx = ranges["lin_vel_x"]
        self.range_vely = ranges["lin_vel_y"]
        self.range_velz = ranges["ang_vel_z"]
        
        # Observations configuration
        obs_cfg = config["observations"]
        self.ang_vel_scale = np.array(obs_cfg["base_ang_vel"]["scale"], dtype=np.float32)
        self.dof_pos_scale = np.array(obs_cfg["joint_pos_rel"]["scale"], dtype=np.float32)
        self.dof_vel_scale = np.array(obs_cfg["joint_vel_rel"]["scale"], dtype=np.float32)
        self.cmd_scale = np.array(obs_cfg["velocity_commands"]["scale"], dtype=np.float32)
        
        # State variables
        self.last_action = np.zeros(self.num_actions, dtype=np.float32)
        self.action = np.zeros(self.num_actions, dtype=np.float32)
        self.obs = np.zeros(96, dtype=np.float32)
        self.cmd = np.zeros(3, dtype=np.float32)
        self.qj_obs = np.zeros(self.num_actions, dtype=np.float32)
        self.dqj_obs = np.zeros(self.num_actions, dtype=np.float32)
        self.gravity_orientation = np.zeros(3, dtype=np.float32)
        self.ang_vel = np.zeros(3, dtype=np.float32)
                    
        print("Locomotion policy initializing ...")
                
    
    def enter(self):
        self.start_time = time.time()
            
    
    def run(self):
        # 1. Retrieve current state
        self.qj = np.array([m.q for m in self.state_cmd.lowstate.motor_state[:29]], dtype=np.float32)
        self.dqj = np.array([m.dq for m in self.state_cmd.lowstate.motor_state[:29]], dtype=np.float32)
        
        imu = self.state_cmd.lowstate.imu_state
        self.ang_vel = np.array([imu.gyroscope[0], imu.gyroscope[1], imu.gyroscope[2]], dtype=np.float32)
        
        w, x, y, z = imu.quaternion[0], imu.quaternion[1], imu.quaternion[2], imu.quaternion[3]
        self.gravity_orientation = np.array([
            -2.0 * (x * z - w * y),
            -2.0 * (y * z + w * x),
            2.0 * (x * x + y * y) - 1.0
        ], dtype=np.float32)
        
        joycmd = self.state_cmd.vel_cmd
            
        # 2. Process Commands
        self.cmd[0] = np.clip(joycmd[0], self.range_velx[0], self.range_velx[1])
        self.cmd[1] = np.clip(joycmd[1], self.range_vely[0], self.range_vely[1])
        self.cmd[2] = np.clip(joycmd[2], self.range_velz[0], self.range_velz[1])
        
        # 3. Process Joint States
        for i, motor_idx in enumerate(self.joint2motor_idx):
            self.qj_obs[i] = self.qj[motor_idx]
            self.dqj_obs[i] = self.dqj[motor_idx]
            
        self.qj_obs = (self.qj_obs - self.default_angles) * self.dof_pos_scale
        self.dqj_obs = self.dqj_obs * self.dof_vel_scale
        self.ang_vel = self.ang_vel * self.ang_vel_scale
        self.cmd = self.cmd * self.cmd_scale
        
        # 4. Construct Observation Tensor
        self.obs[:3] = self.ang_vel
        self.obs[3:6] = self.gravity_orientation
        self.obs[6:9] = self.cmd
        self.obs[9: 9 + self.num_actions] = self.qj_obs
        self.obs[9 + self.num_actions: 9 + self.num_actions * 2] = self.dqj_obs
        self.obs[9 + self.num_actions * 2: 9 + self.num_actions * 3] = self.last_action
        
        obs_tensor = self.obs.reshape(1, -1).astype(np.float32)
        
        # 5. Run ONNX Inference
        inputs = {self.input_name: np.clip(obs_tensor, -100.0, 100.0)}
        action_raw = self.sess.run([self.output_name], inputs)[0]
        self.action = np.clip(action_raw.flatten(), -100.0, 100.0)
        self.last_action = self.action.copy()
        
        # 6. Apply Actions
        loco_action = self.action * self.action_scale + self.default_angles
        action_reorder = np.zeros_like(self.qj)
        for i, motor_idx in enumerate(self.joint2motor_idx):
            action_reorder[motor_idx] = loco_action[i]
            
        # 7. Update Policy Output
        self.policy_output.actions = action_reorder
        self.policy_output.kps = self.kps_reorder
        self.policy_output.kds = self.kds_reorder
    
    def exit(self):
        pass
