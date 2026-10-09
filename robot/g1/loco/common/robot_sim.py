import threading
import time
import mujoco
import mujoco.viewer
import numpy as np

from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_

class RobotSim:
    def __init__(self, model_path: str, simulation_dt: float = 0.003):
        self.simulation_dt = simulation_dt
        self.mj_model = mujoco.MjModel.from_xml_path(model_path)
        self.mj_data = mujoco.MjData(self.mj_model)
        self.target_q = np.zeros(29, dtype=np.float32)
        self.kp = np.zeros(29, dtype=np.float32)
        self.kd = np.zeros(29, dtype=np.float32)
        self.tau = np.zeros(29, dtype=np.float32)
        self.ctrl = np.zeros(29, dtype=np.float32)
        
        self.low_state = unitree_hg_msg_dds__LowState_()  # Simulated low state
        
        self.running = False
    
    def run(self):
        # Main loop for stepping the simulation
        print("Starting simulation...")
        self.running = True
        threading.Thread(target=self.simulation_loop).start()
    
    def simulation_loop(self):
        with mujoco.viewer.launch_passive(self.mj_model, self.mj_data) as viewer:
            while self.running and viewer.is_running():
                start_time = time.time()
                
                # Apply control
                self.step()
                self.mj_data.ctrl[:] = self.ctrl.copy()
                
                # Step simulation
                mujoco.mj_step(self.mj_model, self.mj_data)
                
                # Update simulated low state sensors
                self.update_state()
                
                # Sync viewer
                viewer.sync()
                
                # Sleep to maintain rate
                elapsed = time.time() - start_time
                if elapsed < self.simulation_dt:
                    time.sleep(self.simulation_dt - elapsed)
                # else:
                #     print('Simulation loop is running slower than real-time')
        
        print("MuJoCo viewer closed. Stopping...")
        self.stop()
        
    
    def step(self):
        # PD control (assuming positions start at qpos index 7 and qvel index 6)
        q = self.mj_data.qpos[7:36]
        dq = self.mj_data.qvel[6:35]
        self.ctrl = self.kp * (self.target_q - q) - self.kd * dq + self.tau
    
    def update_state(self):
        # Update IMU (assuming qpos[3:7] are quaternions and qvel[3:6] are angular velocities)
        for i in range(4):
            self.low_state.imu_state.quaternion[i] = self.mj_data.qpos[3 + i]
        for i in range(3):
            self.low_state.imu_state.gyroscope[i] = self.mj_data.qvel[3 + i]
        
        # Update motor states
        q = self.mj_data.qpos[7:36]
        dq = self.mj_data.qvel[6:35]
        
        for i in range(29):
            self.low_state.motor_state[i].q = q[i]
            self.low_state.motor_state[i].dq = dq[i]

    def stop(self):
        self.running = False