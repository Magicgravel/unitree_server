import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelPublisher
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.utils.crc import CRC


class Mode:
    PR = 0  # Series Control for Pitch/Roll Joints
    AB = 1  # Parallel Control for A/B Joints

class RobotReal:
    def __init__(self, cfg: dict):
        self.network_interface = cfg.get("network_interface", "eth0")
        self.state_lock = cfg.get("state_lock", threading.Lock())
        self.cmd_lock = cfg.get("cmd_lock", threading.Lock())
        
        print(f"Initializing Unitree SDK on {self.network_interface}...")
        ChannelFactoryInitialize(0, self.network_interface)
        
        self.crc = CRC()
        
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state: LowState_ = None # Received async
        
        # Publisher/Subscriber
        self.pub = ChannelPublisher(cfg.get("lowcmd_topic", "rt/user_lowcmd"), LowCmd_)
        self.pub.Init()
        self.sub = ChannelSubscriber(cfg.get("lowstate_topic", "rt/lowstate"), LowState_)
        self.sub.Init(self.low_state_handler, 10)
        
        self.running = True
        
        # Wait for connection
        print("Waiting for LowState...")
        while self.low_state is None:
            time.sleep(0.1)
        
        self.mode_machine = self.low_state.mode_machine
        print("Connected! Current mode_machine:", self.mode_machine)
        
        self.low_cmd.mode_pr = Mode.PR
        self.low_cmd.mode_machine = self.mode_machine
        for i in range(29):
            self.low_cmd.motor_cmd[i].mode = 1  # 1:Enable, 0:Disable
    
    def low_state_handler(self, msg):
        with self.state_lock:
            self.low_state = msg
    
    def run(self):
        # Main loop for stepping the robot
        def send_cmd_loop():
            while self.running:
                self.step()
                time.sleep(0.002)  # Run at 500Hz
        
        print("Starting robot control loop...")
        self.running = True
        threading.Thread(target=send_cmd_loop).start()
    
    def step(self):
        with self.cmd_lock:
            # Compute CRC
            self.low_cmd.crc = self.crc.Crc(self.low_cmd)
            
            # Publish command
            self.pub.Write(self.low_cmd)
    
    def stop(self):
        self.running = False