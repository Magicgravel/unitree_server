import threading
import time

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelPublisher
from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowCmd_, unitree_go_msg_dds__LowState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_, unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_ as HgLowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_ as HgLowState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowCmd_ as GoLowCmd_ 
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_ as GoLowState_
from unitree_sdk2py.utils.crc import CRC


class Mode:
    PR = 0  # Series Control for Pitch/Roll Joints
    AB = 1  # Parallel Control for A/B Joints

class RobotReal:
    def __init__(self, cfg: dict):
        self.state_lock = cfg.get("state_lock", threading.Lock())
        self.cmd_lock = cfg.get("cmd_lock", threading.Lock())
        self.num_joints = cfg.get("num_joints", None)
        
        # print(f"Initializing Unitree SDK on {self.network_interface}...")
        # self.domain_id = cfg.get("domain_id", 0)
        # self.network_interface = cfg.get("interface", "eth0")
        # ChannelFactoryInitialize(0, self.network_interface)
        
        self.crc = CRC()
        
        self.robot = cfg.get("robot", "g1")
        if self.robot in ["g1"]:
            self._low_cmd_type = HgLowCmd_
            self._low_state_type = HgLowState_
            self.low_cmd: HgLowCmd_ = unitree_hg_msg_dds__LowCmd_()
            self.low_state: HgLowState_ = None # Received async
        elif self.robot in ["go2"]:
            self._low_cmd_type = GoLowCmd_
            self._low_state_type = GoLowState_
            self.low_cmd: GoLowCmd_ = unitree_go_msg_dds__LowCmd_()
            self.low_state: GoLowState_ = None # Received async
        else:
            raise ValueError(f"Unsupported robot type: {self.robot}")
        
        # Publisher/Subscriber
        self.pub = ChannelPublisher(cfg.get("lowcmd_topic", "rt/lowcmd"), self._low_cmd_type)
        self.pub.Init()
        self.sub = ChannelSubscriber(cfg.get("lowstate_topic", "rt/lowstate"), self._low_state_type)
        self.sub.Init(self.low_state_handler, 10)
        
        self.running = True
        
        # Wait for connection
        print("Waiting for LowState...")
        while self.low_state is None:
            time.sleep(0.1)

        print("Connected!")
        
        for i in range(self.num_joints):
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