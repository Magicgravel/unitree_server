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

from threading import Thread
import threading
import time
import mujoco
import mujoco.viewer


class Config:
    ROBOT = "go2" # Robot name, "go2", "b2", "b2w", "h1", "go2w", "g1" 
    ROBOT_SCENE = "unitree_mujoco/unitree_robots/" + ROBOT + "/scene.xml" # Robot scene
    DOMAIN_ID = 1 # Domain id
    INTERFACE = "lo" # Interface 

    USE_JOYSTICK = 1 # Simulate Unitree WirelessController using a gamepad
    JOYSTICK_TYPE = "xbox" # support "xbox" and "switch" gamepad layout
    JOYSTICK_DEVICE = 0 # Joystick number

    PRINT_SCENE_INFORMATION = True # Print link, joint and sensors information of robot
    ENABLE_ELASTIC_BAND = False # Virtual spring band, used for lifting h1

    SIMULATE_DT = 0.005  # Need to be larger than the runtime of viewer.sync()
    VIEWER_DT = 0.02  # 50 fps for viewer


class UnitreeMujocoLauncher:
    def __init__(self):
        self.config = Config()
        self.viewer_thread = None
        self.sim_thread = None
        self.bridge = None
        self.locker = threading.Lock()
    
    def init(self):
        self.config.ROBOT_SCENE = "unitree_mujoco/unitree_robots/" + self.config.ROBOT + "/scene.xml"
        
        # Update self.config to the config.py file
        config_path = "config.py"
        with open(config_path, "r") as f:
            config_lines = f.readlines()
        with open(config_path, "w") as f:
            for line in config_lines:
                if line.startswith("ROBOT ="):
                    f.write(f"ROBOT = '{self.config.ROBOT}'\n")
                else:
                    f.write(line)
            
        
        self.mj_model = mujoco.MjModel.from_xml_path(self.config.ROBOT_SCENE)
        self.mj_data = mujoco.MjData(self.mj_model)

        if self.config.ENABLE_ELASTIC_BAND:
            from unitree_mujoco.simulate_python.unitree_sdk2py_bridge import ElasticBand
            self.elastic_band = ElasticBand()
            if self.config.ROBOT in ["h1", "g1"]:
                self.band_attached_link = self.mj_model.body("torso_link").id
            else:
                self.band_attached_link = self.mj_model.body("base_link").id
            self.viewer = mujoco.viewer.launch_passive(
                key_callback=self.elastic_band.MujuocoKeyCallback
            )
        else:
            self.viewer = mujoco.viewer.launch_passive(self.mj_model, self.mj_data)

        self.mj_model.opt.timestep = self.config.SIMULATE_DT
        num_motor_ = self.mj_model.nu
        dim_motor_sensor_ = 3 * num_motor_

        time.sleep(0.2)
    
    def set_config(self, cfg):
        self.config = cfg

    def start_simulation(self):
        self.viewer_thread = Thread(target=self.PhysicsViewerThread)
        self.sim_thread = Thread(target=self.SimulationThread)

        self.viewer_thread.start()
        self.sim_thread.start()

    def stop_simulation(self):
        # 关闭渲染窗口, 让 viewer/sim 线程退出
        viewer = getattr(self, "viewer", None)
        if viewer is not None and viewer.is_running():
            viewer.close()
        if self.viewer_thread is not None and self.viewer_thread.is_alive():
            self.viewer_thread.join()
        if self.sim_thread is not None and self.sim_thread.is_alive():
            self.sim_thread.join()
        # 停止 UnitreeSdk2Bridge 所有 DDS 周期发布线程
        if self.bridge is not None:
            self.bridge.lowStateThread.Wait()
            self.bridge.HighStateThread.Wait()
            self.bridge.WirelessControllerThread.Wait()
    
    def SimulationThread(self):
        from unitree_mujoco.simulate_python.unitree_sdk2py_bridge import UnitreeSdk2Bridge
        unitree = UnitreeSdk2Bridge(self.mj_model, self.mj_data)
        self.bridge = unitree

        if self.config.USE_JOYSTICK:
            unitree.SetupJoystick(device_id=0, js_type=self.config.JOYSTICK_TYPE)
        if self.config.PRINT_SCENE_INFORMATION:
            unitree.PrintSceneInformation()

        while self.viewer.is_running():
            step_start = time.perf_counter()

            self.locker.acquire()

            if self.config.ENABLE_ELASTIC_BAND:
                if self.elastic_band.enable:
                    self.mj_data.xfrc_applied[self.band_attached_link, :3] = self.elastic_band.Advance(
                        self.mj_data.qpos[:3], self.mj_data.qvel[:3]
                    )
            mujoco.mj_step(self.mj_model, self.mj_data)

            self.locker.release()

            time_until_next_step = self.mj_model.opt.timestep - (
                time.perf_counter() - step_start
            )
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)


    def PhysicsViewerThread(self):
        while self.viewer.is_running():
            self.locker.acquire()
            self.viewer.sync()
            self.locker.release()
            time.sleep(self.config.VIEWER_DT)
    
    def reset(self):
        self.locker.acquire()
        mujoco.mj_resetData(self.mj_model, self.mj_data)
        self.locker.release()