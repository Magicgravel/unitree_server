from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
import os
import json
import numpy as np
import onnxruntime as ort

current_dir = os.path.dirname(os.path.abspath(__file__))
policy_path = os.path.join(current_dir, "../policy")

NUM_DOF = 29

# 关节映射 (dof_mapping[i] 表示策略第 i 个动作对应电机索引)
dof_mapping = list(range(NUM_DOF))

# 策略超参数 (与原 C++ 中一致)
scale_lin_vel = 1.0
scale_ang_vel = 1.0
scale_dof_pos = 1.0
scale_dof_vel = 1.0
clip_observations = 100.0
clip_actions = 100.0
action_scale = 0.25

# 死区
dead_zone = 0.1

# 默认关节角
_default_dof_pos = np.zeros(NUM_DOF)

# 增益
dof_Kps = np.full(NUM_DOF, 20.0)
dof_Kds = np.full(NUM_DOF, 0.5)

# 重力向量
_gravity_vec = np.array([0.0, 0.0, -1.0])


def QuatRotateInverse(quat, vec):
    """
    用四元数的逆旋转向量。quat 顺序为 [w, x, y, z]。
    """
    w, x, y, z = quat
    # 四元数共轭 (单位四元数的逆)
    qw, qx, qy, qz = w, -x, -y, -z
    # q * v
    vx, vy, vz = vec
    # q * (0, v) * q_conj
    # 用标准公式：
    ix = qw * vx + qy * vz - qz * vy
    iy = qw * vy + qz * vx - qx * vz
    iz = qw * vz + qx * vy - qy * vx
    iw = -qx * vx - qy * vy - qz * vz

    rx = ix * qw + iw * -qx + iy * -qz - iz * -qy
    ry = iy * qw + iw * -qy + iz * -qx - ix * -qz
    rz = iz * qw + iw * -qz + ix * -qy - iy * -qx

    return np.array([rx, ry, rz])


def invNormalize(value, min_v, max_v):
    """将 [-1, 1] 映射到 [min_v, max_v]"""
    value = max(-1.0, min(1.0, value))
    return (value + 1.0) * 0.5 * (max_v - min_v) + min_v


# ============ State_Loco ============
class LocoMode_wbc_fsm(FSMState):
    name = 'loco_wbc_fsm'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = LocoMode_wbc_fsm.name

        self.state_cmd: StateAndCmd = kwargs.get("state_cmd")
        self.policy_output: PolicyOutput = kwargs.get("policy_output")

        # 读取配置
        config_path = os.path.join(policy_path, "velocity/wbc_fsm_loco/config", "loco.json")
        if not os.path.isfile(config_path):
            print(f"[ERROR] Failed to open config file: {config_path}")
            raise RuntimeError("Cannot open config file")

        with open(config_path, "r") as f:
            config = json.load(f)

        self._model_path = os.path.join(policy_path, config["model_path"])
        self._anchor_terminate_thresh = float(config["safe_projgravity_threshold"])

        self._vxLim = np.array(
            [float(config["vx_limit_min"]), float(config["vx_limit_max"])]
        )
        self._vyLim = np.array(
            [float(config["vy_limit_min"]), float(config["vy_limit_max"])]
        )
        self._wyawLim = np.array(
            [float(config["wyaw_limit_min"]), float(config["wyaw_limit_max"])]
        )
        self._cmdSmoothes = float(config["cmd_smoothes"])

        print(f"[Config Loco] Model path: {self._model_path}")

        # ONNX 会话
        self._env = None
        self._session = None
        self._input_names = ["obs", "h_in", "c_in"]
        self._output_names = ["actions", "h_out", "c_out"]

        self._loadPolicy()

        # 状态
        self._terminate_flag = False
        self._num_obs_history = 1  # 与原代码 enter() 中循环次数一致
        self._observation = []
        self._joint_q = np.zeros(NUM_DOF)
        self._targetPos_rl = np.zeros(NUM_DOF)
        self._last_targetPos_rl = np.zeros(NUM_DOF)

    def _loadPolicy(self):
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        self._session = ort.InferenceSession(
            self._model_path, sess_options, providers=["CPUExecutionProvider"]
        )

        input0 = self._session.get_inputs()[0]
        input1 = self._session.get_inputs()[1]
        output0 = self._session.get_outputs()[0]

        self._obs_size_ = input0.shape[1]
        self._hidden_size_ = input1.shape[2]
        self._action_size_ = output0.shape[1]

        self._h_state_ = np.zeros((1, 1, self._hidden_size_), dtype=np.float32)
        self._c_state_ = np.zeros((1, 1, self._hidden_size_), dtype=np.float32)
        self._action = np.zeros(self._action_size_, dtype=np.float32)

    def _observations_compute(self):
        quat = list(self.state_cmd.lowstate.imu_state.quaternion[:4])
        projected_gravity = QuatRotateInverse(quat, _gravity_vec)

        projected_gravity_error = abs(projected_gravity[2] - (-1.0))
        if projected_gravity_error > self._anchor_terminate_thresh:
            self._terminate_flag = True
            print(f"[Warning] Large projected gravity error: {projected_gravity_error}")

        obs_commands = np.array(
            [self.state_cmd.vel_cmd[0], self.state_cmd.vel_cmd[1], self.state_cmd.vel_cmd[2]], dtype=np.float32
        )

        dof_pos_vec = np.zeros(NUM_DOF, dtype=np.float32)
        dof_vel_vec = np.zeros(NUM_DOF, dtype=np.float32)
        for i in range(NUM_DOF):
            dof_pos_vec[i] = (
                self.state_cmd.lowstate.motor_state[dof_mapping[i]].q
                - _default_dof_pos[dof_mapping[i]]
            )
            dof_vel_vec[i] = self.state_cmd.lowstate.motor_state[dof_mapping[i]].dq

        body_ang_vel = np.array(self.state_cmd.lowstate.imu_state.gyroscope[:3], dtype=np.float32)

        # 缩放
        body_ang_vel[0] *= scale_lin_vel
        body_ang_vel[1] *= scale_lin_vel
        body_ang_vel[2] *= scale_ang_vel

        obs_commands[0] *= scale_lin_vel
        obs_commands[1] *= scale_lin_vel
        obs_commands[2] *= scale_ang_vel

        dof_pos_vec *= scale_dof_pos
        dof_vel_vec *= scale_dof_vel

        # 拼接观测
        obs = np.concatenate(
            [
                body_ang_vel,
                projected_gravity,
                obs_commands,
                dof_pos_vec,
                dof_vel_vec,
                self._action,
            ]
        )
        obs = np.clip(obs, -clip_observations, clip_observations)
        self._observation = obs

    def _action_compute(self):
        obs = self._observation.astype(np.float32).reshape(1, -1)
        h_in = self._h_state_.astype(np.float32)
        c_in = self._c_state_.astype(np.float32)

        outputs = self._session.run(
            self._output_names,
            {
                self._input_names[0]: obs,
                self._input_names[1]: h_in,
                self._input_names[2]: c_in,
            },
        )

        actions, h_out, c_out = outputs

        self._action = actions[0].copy()
        self._h_state_ = h_out.copy()
        self._c_state_ = c_out.copy()

        for i in range(NUM_DOF):
            self._action[i] = np.clip(self._action[i], -clip_actions, clip_actions)
            actions_scaled = self._action[i] * action_scale
            self._joint_q[dof_mapping[i]] = actions_scaled + _default_dof_pos[dof_mapping[i]]

    def enter(self):
        self._terminate_flag = False
        # for i in range(NUM_DOF):
        #     self._lowCmd.motorCmd[i].mode = 10
        #     self._lowCmd.motorCmd[i].q = self.state_cmd.lowstate.motor_state[i].q
        #     self._lowCmd.motorCmd[i].dq = 0.0
        #     self._lowCmd.motorCmd[i].tau = 0.0
        #     self._lowCmd.motorCmd[i].Kp = dof_Kps[i]
        #     self._lowCmd.motorCmd[i].Kd = dof_Kds[i]
        #     self._targetPos_rl[i] = _default_dof_pos[i]
        #     self._last_targetPos_rl[i] = self.state_cmd.lowstate.motor_state[i].q
        #     self._joint_q[i] = _default_dof_pos[i]

        for _ in range(self._num_obs_history):
            self._observations_compute()

    def run(self):
        self._observations_compute()
        self._action_compute()
        self._targetPos_rl = self._joint_q.copy()
        self._last_targetPos_rl = self._targetPos_rl.copy()
        
        self.policy_output.actions = self._targetPos_rl.copy()
        self.policy_output.kps = dof_Kps.copy()
        self.policy_output.kds = dof_Kds.copy()

    def exit(self):
        self._h_state_ = np.zeros((1, 1, self._hidden_size_), dtype=np.float32)
        self._c_state_ = np.zeros((1, 1, self._hidden_size_), dtype=np.float32)
