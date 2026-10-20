import threading
import time
import sys
import numpy as np
from pathlib import Path

MOTION_ROOT = Path(__file__).parent.expanduser().resolve()
if str(MOTION_ROOT) not in sys.path:
    sys.path.insert(0, str(MOTION_ROOT))

from fsm.fsm import FSM
from states import *

from common.ctrlcomp import StateAndCmd, PolicyOutput
# from common.audio_player import AudioPlayer

default_state_name = PassiveMode.name
# default_state_name = LocoMode.name

class MotionController:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.running = True
        self.num_joints = self.cfg.get("num_joints", 12)
        self.prev_buttons = {}
        self.dt = 0.02 # 50Hz
        self.state_lock = threading.Lock()
        self.cmd_lock = threading.Lock()
        self.cfg["state_lock"] = self.state_lock
        self.cfg["cmd_lock"] = self.cmd_lock
        
        if self.cfg.get("mode", "sim") == "sim":
            self.sim_mode = True
            self.cfg["network_interface"] = "lo"
        else:
            self.sim_mode = False
        
        if self.cfg.get("play_audio", False) and not self.sim_mode:
            print("Initializing Audio Player...")
            self.audio_player = AudioPlayer(self.cfg.get("network_interface", ""))
        else:
            self.audio_player = None
        
        self.state_cmd = StateAndCmd(self.num_joints)
        self.policy_output = PolicyOutput(self.num_joints)
        
        # Setup Robot Communication
        if not self.sim_mode:
            from common.robot_real import RobotReal
            self.robot = RobotReal(self.cfg)
        else:
            from common.robot_sim import RobotSim
            self.robot = RobotSim(self.cfg.get("robot_model"))
        
        self.state_cmd.lowstate = self.robot.low_state
        
        self.kwargs = {
            'state_cmd': self.state_cmd,
            'policy_output': self.policy_output,
            'audio_player': self.audio_player,
        }
        
        self.fsm_controller = FSM()
        for mode in mode_list:
            self.fsm_controller.register(mode(self.kwargs))
        self.fsm_controller.change(default_state_name)
        
        if self.cfg.get("control", True):
            self.robot.run()

    def step(self): 
        with self.state_lock:
            self.state_cmd.lowstate = self.robot.low_state
            
            if self.cfg.get("input_mode", None) in ["joy", "keyboard"]:
                try:
                    import struct
                    remote_bytes = bytes(self.state_cmd.lowstate.wireless_remote)
                    Lx = struct.unpack('<f', remote_bytes[4:8])[0]
                    Rx = struct.unpack('<f', remote_bytes[8:12])[0]
                    Ly = struct.unpack('<f', remote_bytes[20:24])[0]
                    self.state_cmd.vel_cmd = np.array([Ly, -Lx, -Rx], dtype=np.float32)
                except Exception:
                    self.state_cmd.vel_cmd = np.zeros(3, dtype=np.float32)
        
        # self.teleop.update()
        
        self.fsm_controller.run()
        
        # Send Command
        policy_output_action = self.policy_output.actions.copy()
        kps = self.policy_output.kps.copy()
        kds = self.policy_output.kds.copy()
        
        if not self.sim_mode:
            with self.cmd_lock:
                for i in range(self.num_joints):
                    self.robot.low_cmd.motor_cmd[i].q = policy_output_action[i]
                    self.robot.low_cmd.motor_cmd[i].dq = 0.0
                    self.robot.low_cmd.motor_cmd[i].kp = kps[i]
                    self.robot.low_cmd.motor_cmd[i].kd = kds[i]
                    self.robot.low_cmd.motor_cmd[i].tau = 0.0
        else:
            self.robot.target_q = policy_output_action
            self.robot.kp = kps
            self.robot.kd = kds

    def run(self): 
        while self.running:
            loop_start_time = time.time()
            
            self.step()
            
            elapsed = time.time() - loop_start_time
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                print(f"Warning: Loop is running behind by {-sleep_time:.3f} seconds.")
    
    def stop(self):
        self.running = False
        self.robot.stop()
