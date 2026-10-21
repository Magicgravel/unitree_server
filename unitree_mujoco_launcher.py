import os
import sys
UNITREE_MUJOCO_DIR = os.path.dirname(os.path.abspath(__file__)) + "/unitree_mujoco/simulate_python"
if not os.path.exists(UNITREE_MUJOCO_DIR):
    print(f"[unitree_mujoco_launcher] simulation directory not found: {UNITREE_MUJOCO_DIR}")
    print(f"[unitree_mujoco_launcher] clone the repository using:")
    print(f"    git clone https://github.com/UnitreeRobotics/unitree_mujoco.git")
    print(f"    or")
    print(f"    git submodule update --init --recursive")
    sys.exit(1)
if str(UNITREE_MUJOCO_DIR) not in sys.path:
    sys.path.insert(0, str(UNITREE_MUJOCO_DIR))

from threading import Thread
os.chdir(UNITREE_MUJOCO_DIR)
from unitree_mujoco import *

class Config:
    ROBOT = "go2" # Robot name, "go2", "b2", "b2w", "h1", "go2w", "g1" 
    ROBOT_SCENE = "../unitree_robots/" + ROBOT + "/scene.xml" # Robot scene
    DOMAIN_ID = 1 # Domain id
    INTERFACE = "lo" # Interface 

    USE_JOYSTICK = 1 # Simulate Unitree WirelessController using a gamepad
    JOYSTICK_TYPE = "xbox" # support "xbox" and "switch" gamepad layout
    JOYSTICK_DEVICE = 0 # Joystick number

    PRINT_SCENE_INFORMATION = True # Print link, joint and sensors information of robot
    ENABLE_ELASTIC_BAND = False # Virtual spring band, used for lifting h1

    SIMULATE_DT = 0.005  # Need to be larger than the runtime of viewer.sync()
    VIEWER_DT = 0.02  # 50 fps for viewer

config = Config()

class UnitreeMujocoLauncher:
    def __init__(self):
        self.config = config

        self.viewer_thread = None
        self.sim_thread = None

    def set_config(self, cfg):
        self.config = cfg

    def start_simulation(self):
        self.viewer_thread = Thread(target=PhysicsViewerThread)
        self.sim_thread = Thread(target=SimulationThread)

        self.viewer_thread.start()
        self.sim_thread.start()

    def stop_simulation(self):
        if self.viewer_thread.is_alive():
            self.viewer_thread.join()
        if self.sim_thread.is_alive():
            self.sim_thread.join()