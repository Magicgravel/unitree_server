import time
import sys
import struct

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize

# Uncomment the following two lines when using Go2、Go2-W、B2、B2-W、H1 robot
# from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
# from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

# Uncomment the following two lines when using G1、H1-2 robot
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

class DataParser:
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
        self.F3 = 0
        self.Start = 0
       
    def parse_botton(self,data1,data2):
        self.R1 = (data1 >> 0) & 1
        self.L1 = (data1 >> 1) & 1
        self.Start = (data1 >> 2) & 1
        self.Select = (data1 >> 3) & 1
        self.R2 = (data1 >> 4) & 1
        self.L2 = (data1 >> 5) & 1
        self.F1 = (data1 >> 6) & 1
        self.F3 = (data1 >> 7) & 1
        self.A = (data2 >> 0) & 1
        self.B = (data2 >> 1) & 1
        self.X = (data2 >> 2) & 1
        self.Y = (data2 >> 3) & 1
        self.Up = (data2 >> 4) & 1
        self.Right = (data2 >> 5) & 1
        self.Down = (data2 >> 6) & 1
        self.Left = (data2 >> 7) & 1

    def parse_key(self,data):
        lx_offset = 4
        self.Lx = struct.unpack('<f', data[lx_offset:lx_offset + 4])[0]
        rx_offset = 8
        self.Rx = struct.unpack('<f', data[rx_offset:rx_offset + 4])[0]
        ry_offset = 12
        self.Ry = struct.unpack('<f', data[ry_offset:ry_offset + 4])[0]
        L2_offset = 16
        L2 = struct.unpack('<f', data[L2_offset:L2_offset + 4])[0] # Placeholder，unused
        ly_offset = 20
        self.Ly = struct.unpack('<f', data[ly_offset:ly_offset + 4])[0]

    def parse(self,remoteData):
        self.parse_key(remoteData)
        self.parse_botton(remoteData[2],remoteData[3])

        
class Gamepad:
    def __init__(self, networkInterface: str = ''):
        if networkInterface != '':
            ChannelFactoryInitialize(0, networkInterface)
        self.low_state = None
        self.data_parser = DataParser()
        self.botton = self.data_parser
        self.key = self.data_parser

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber("rt/lf/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)
        
        # Wait for first message to arrive
        while self.low_state is None:
            time.sleep(0.1)
        print("First LowState received. Gamepad is ready.")
    
    def LowStateMessageHandler(self, msg: LowState_):
        self.low_state = msg
        wireless_remote_data = self.low_state.wireless_remote
        self.data_parser.parse(wireless_remote_data)


if __name__ == '__main__':

    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")

    if len(sys.argv)>1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    gamepad = Gamepad('eth0')
    gamepad.Init()

    while True:
        print("Current Gamepad State:")
        print(f"Lx: {gamepad.key.Lx:.2f}, Ly: {gamepad.key.Ly:.2f}, Rx: {gamepad.key.Rx:.2f}, Ry: {gamepad.key.Ry:.2f}")
        print(f"Buttons: L1={gamepad.botton.L1}, L2={gamepad.botton.L2}, R1={gamepad.botton.R1}, R2={gamepad.botton.R2}, A={gamepad.botton.A}, B={gamepad.botton.B}, X={gamepad.botton.X}, Y={gamepad.botton.Y}, Up={gamepad.botton.Up}, Down={gamepad.botton.Down}, Left={gamepad.botton.Left}, Right={gamepad.botton.Right}, Start={gamepad.botton.Start}, Select={gamepad.botton.Select}, F1={gamepad.botton.F1}, F3={gamepad.botton.F3}")
        time.sleep(2)