## @file teleop_keyboard.py
# @brief Teleoperation keyboard control for Unitree robot

import sys
import tty
import termios
import threading

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__WirelessController_
from unitree_sdk2py.utils.thread import RecurrentThread

DOMAIN_ID = 0
INTERFACE = "lo"
TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"

class WirelessControllerPublisher:
    def __init__(self):
        self.publisher = ChannelPublisher(TOPIC_WIRELESS_CONTROLLER, WirelessController_)
        self.publisher.Init()
        
        self.wireless_controller = unitree_go_msg_dds__WirelessController_()
        self.lx = 0.0
        self.ly = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.keys = 0

        self.publish_thread = RecurrentThread( 
            interval=0.1, target=self.publish, name="WirelessControllerPublisher"
        )
        self.publish_thread.Start()

    def publish(self):
        self.wireless_controller.lx = self.lx
        self.wireless_controller.ly = self.ly
        self.wireless_controller.rx = self.rx
        self.wireless_controller.ry = self.ry
        self.wireless_controller.keys = self.keys

        self.publisher.Write(self.wireless_controller)
    
    def update(self, remote_data):
        self.lx, self.ly, self.rx, self.ry, self.keys = remote_data

class TeleopKeyboard:
    def __init__(self, callback=None):
        self.d_speed = 0.1
        self.d_turn = 0.5
        self.is_running = False
        
        self.lx = 0.0
        self.ly = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.kyes = 0
        
        self.callback = callback
        
        self.raw_mode = True
        self.prefix = "> "

    def get_key(self):
        if self.raw_mode:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    # Handle arrow keys
                    ch += sys.stdin.read(2)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch
        else:
            return input(self.prefix)

    def run(self):
        # print("Teleop Keyboard Control (Terminal)")
        # print("w/s: linear x (forward/back) (ly)")
        # print("a/d: linear y (strafe left/right) (lx)")
        # print("left/right arrow: angular z (turn) (rx)")
        # print("up/down arrow: linear x (forward/back) (ly)")
        # print("space: zero all")
        # print("Press Ctrl+C to quit.")
        
        self.is_running = True
        while self.is_running:
            key = self.get_key()
            if key == '\x03':
                self.exit()
            elif key == '\x1b[A':  # Up
                self.ly += self.d_speed
            elif key == '\x1b[B':  # Down
                self.ly -= self.d_speed
            elif key == '\x1b[D':  # Left
                self.rx += self.d_turn
            elif key == '\x1b[C':  # Right
                self.rx -= self.d_turn
            elif key == 'w':
                self.ly += self.d_speed
            elif key == 's':
                self.ly -= self.d_speed
            elif key == 'a':
                self.lx += self.d_speed
            elif key == 'd':
                self.lx -= self.d_speed
            elif key == 'q':
                self.ry += self.d_turn
            elif key == 'e':
                self.ry -= self.d_turn
            elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                self.kyes = int(key)
            elif key == ' ':
                self.lx = 0.0
                self.ly = 0.0
                self.rx = 0.0
                self.ry = 0.0
            
            # Print current status
            # print(f"\rly: {self.ly:.2f}, lx: {self.lx:.2f}, rx: {self.rx:.2f} ", end="", flush=True)

            if self.callback:
                remote_data = (self.lx, self.ly, self.rx, self.ry, self.kyes)
                self.callback(remote_data)
    
    def stop(self):
        self.is_running = False
    
    def exit(self):
        self.is_running = False
        if self.raw_mode:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("Teleop Keyboard Control Stopped.")
        exit(0)
    
    def run_in_thread(self):
        threading.Thread(target=self.run, daemon=True).start()


if __name__ == "__main__":
    ChannelFactoryInitialize(DOMAIN_ID, INTERFACE)
    
    wireless_controller_publisher = WirelessControllerPublisher()
    
    teleop = TeleopKeyboard(
        wireless_controller_publisher.update
    )
    teleop.run()