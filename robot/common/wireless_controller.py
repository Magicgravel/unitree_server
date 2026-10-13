from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__WirelessController_

TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"

class WirelessController:
    def __init__(self):
        # key
        self.Lx = 0           
        self.Rx = 0            
        self.Ry = 0            
        self.Ly = 0

        # button
        self.L1 = 0
        self.L2 = 0
        self.R1 = 0
        self.R2 = 0
        self.A = 0
        self.B = 0
        self.X = 0
        self.Y = 0
        self.Up = 0
        self.Down = 0
        self.Left = 0
        self.Right = 0
        self.Select = 0
        self.F1 = 0
        self.F2 = 0
        self.Start = 0
        
        self.wireless_controller: WirelessController_ = unitree_go_msg_dds__WirelessController_()

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber(TOPIC_WIRELESS_CONTROLLER, WirelessController_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
    
    def LowStateMessageHandler(self, msg: WirelessController_):
        self.wireless_controller = msg
        self.update()
    
    def update(self):
        self.Lx = self.wireless_controller.lx
        self.Rx = self.wireless_controller.rx
        self.Ry = self.wireless_controller.ry
        self.Ly = self.wireless_controller.ly

        keys = self.wireless_controller.keys
        self.R1 = (keys >> 0) & 1
        self.L1 = (keys >> 1) & 1
        self.Start = (keys >> 2) & 1
        self.Select = (keys >> 3) & 1
        self.R2 = (keys >> 4) & 1
        self.L2 = (keys >> 5) & 1
        self.F1 = (keys >> 6) & 1
        self.F2 = (keys >> 7) & 1
        self.A = (keys >> 8) & 1
        self.B = (keys >> 9) & 1
        self.X = (keys >> 10) & 1
        self.Y = (keys >> 11) & 1
        self.Up = (keys >> 12) & 1
        self.Right = (keys >> 13) & 1
        self.Down = (keys >> 14) & 1
        self.Left = (keys >> 15) & 1