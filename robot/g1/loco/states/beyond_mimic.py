from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
from common.motion_loader import MotionLoader
from common.param_loader import ParamLoader
from common.observation import ObservationReal
from common.audio_player import AudioPlayer
import numpy as np
import time
import os
import onnxruntime as ort


current_dir = os.path.dirname(os.path.abspath(__file__))
policy_path = os.path.join(current_dir, "../policy")

class BeyondMimic(FSMState):
    name = 'mjlab_motion'
    
    def __init__(self, kwargs: dict):
        super().__init__()
        self.name = BeyondMimic.name
        
        self.state_cmd: StateAndCmd = kwargs.get("state_cmd")
        self.policy_output: PolicyOutput = kwargs.get("policy_output")
        self.audio_player: AudioPlayer = kwargs.get("audio_player", None)
        self.policy_path = kwargs.get("policy_path", policy_path)
        self.motion_name = kwargs.get("motion_name")
        
        motion_file = os.path.join(self.policy_path, f"params/{self.motion_name}.npz")
        param_file = os.path.join(self.policy_path, f"params/deploy.yaml")
        policy_file = os.path.join(self.policy_path, f"exported/policy_v9.onnx")
        self.audio_file = os.path.join(self.policy_path, f"params/{self.motion_name}_fixed.wav")
        
        # 1. Load Policy
        self.sess = ort.InferenceSession(policy_file)
        self.input_name = self.sess.get_inputs()[0].name
        self.output_name = self.sess.get_outputs()[0].name
        
        # 2. Load Motion
        self.motion = MotionLoader(motion_file)
        print(f"Loaded motion file: {motion_file} with {self.motion.num_frames} frames.")
        
        # 3. Setup Robot Communication
        self.param = ParamLoader(param_file)
        print(f"Loaded param file: {param_file}.")
        self.dt = self.param.dt
        
        # 4. Setup Observation
        self.obs_getter = ObservationReal(self.state_cmd, self.motion, self.param)
        
        # State vars
        self.last_action = np.zeros(29, dtype=np.float32)
        
        print("Locomotion policy initializing ...")
                
    
    def enter(self):
        if self.audio_player:
            self.audio_player.set_volume(95)
            self.audio_player.play(self.audio_file)
        self.start_time = time.time()
    
    
    def run(self):
        # 1. Get Obs
        t = time.time() - self.start_time
        # if self.motion and t > self.motion.duration:
        #     print("Motion finished. Stopping...")
        #     return
        
        obs = self.obs_getter.get_obs(t, self.last_action)
        
        # 2. Inference
        # ONNX Runtime expects [batch, dim]
        inputs = {self.input_name: obs.reshape(1, -1).astype(np.float32)}
        action = self.sess.run([self.output_name], inputs)[0][0]
        
        self.last_action = action
        
        # 3. Process Action -> Command
        # Using action scale from yaml
        target_q = action * self.param.action_scale + self.param.default_dof_pos
        
        self.policy_output.actions = target_q.copy()
        self.policy_output.kps = np.array(self.param.kp, dtype=np.float32)
        self.policy_output.kds = np.array(self.param.kd, dtype=np.float32)
    
    
    def exit(self):
        if self.audio_player:
            self.audio_player.stop()
