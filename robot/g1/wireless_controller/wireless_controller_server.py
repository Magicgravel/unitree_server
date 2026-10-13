from robot.g1.loco.g1_loco_server import G1LocoServer
from robot.g1.audio.g1_audio_server import G1AudioServer
from robot.g1.arm.g1_arm_action_server import G1ArmActionServer
from ...common.wireless_controller import WirelessController

class G1WirelessControllerServer:
    def __init__(
        self,
        loco_server: G1LocoServer=None,
        audio_server: G1AudioServer=None,
        arm_action_server: G1ArmActionServer=None
    ):
        self.loco_server = loco_server
        self.audio_server = audio_server
        self.arm_action_server = arm_action_server

        self.controller = WirelessController()
        self.controller.Init()
        
        self.key_mapping = {
            ''
        }
    
    def update(self):
        pass