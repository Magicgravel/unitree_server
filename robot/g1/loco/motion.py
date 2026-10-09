import argparse
import threading
import time
import os
import sys
import yaml
import json
import numpy as np
from pathlib import Path

MOTION_ROOT = Path(__file__).parent.expanduser().resolve()
if str(MOTION_ROOT) not in sys.path:
    sys.path.insert(0, str(MOTION_ROOT))

from fsm.fsm import FSM
from states import *

from common.ctrlcomp import StateAndCmd, PolicyOutput
# from common.audio_player import AudioPlayer

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_api.msg.dds_._Request_ import Request_

default_state_name = ZeroTorque.name


class MotionController:
    def __init__(self, cfg: dict):
        self.running = True
        self.num_joints = 29
        self.cfg = cfg
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
        
        # self.teleop = TeleopGamepad(self.fsm_controller, self.cfg, self.cfg.get("network_interface", ""))
        
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


ROBOT_API_ID_LOCO_SET_VELOCITY = 7105
SPORT_API_ID_MOVE = 1008

class MoveController:
    def __init__(self, controller: MotionController):
        self.motion_controller = controller
        self.subscriber = ChannelSubscriber('rt/api/sport/request', Request_)
        self.subscriber.Init(self.move_callback, 10)

    def move_callback(self, msg: Request_):
        api_id = msg.header.identity.api_id
        p = json.loads(msg.parameter)
        if api_id == ROBOT_API_ID_LOCO_SET_VELOCITY:
            velocity = p.get("velocity", [0.0, 0.0, 0.0])
            duration = p.get("duration", 1.0)
        elif api_id == SPORT_API_ID_MOVE:
            velocity = [p.get("x", 0.0), p.get("y", 0.0), p.get("z", 0.0)]
            duration = p.get("duration", 1.0)
        else:
            return
        self.motion_controller.state_cmd.vel_cmd = np.array(velocity, dtype=np.float32)
        # print(f"[motion.py] velocity: {velocity}")


def teleop_key_callback(remote_data):
    lx, ly, rx, ry, keys = remote_data
    if keys == 1:
        motion_controller.fsm_controller.change(PassiveMode.name)
    elif keys == 2:
        motion_controller.fsm_controller.change(FixedPose.name)
    elif keys == 3:
        motion_controller.fsm_controller.change(LocoMode.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action='store_true', help="Run in simulation mode (no robot communication)")
    parser.add_argument("--net", type=str, default="lo", help="Network interface for robot communication.")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_dir, "config.yaml")
    with open(config_file, 'r') as f:
        print(f"Loading config from {config_file}")
        config = yaml.safe_load(f)
    
    if args.sim:
        config["mode"] = "sim"
    if args.net:
        config["network_interface"] = args.net
    
    try:
        motion_controller = MotionController(config)
        move_controller = MoveController(motion_controller)
        
        # keyboard_teleop = TeleopKeyboard(teleop_key_callback)
        # keyboard_teleop.raw_mode = False
        # keyboard_teleop.run_in_thread()
        
        motion_controller.run()
    except KeyboardInterrupt:
        print("Stopping...")
        motion_controller.stop()
        sys.exit(0)
