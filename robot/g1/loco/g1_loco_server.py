import json
import os
import threading
import numpy as np
import yaml

from .motion import MotionController

from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
)
from unitree_sdk2py.g1.loco.g1_loco_api import (
    LOCO_SERVICE_NAME,
    LOCO_API_VERSION,
    ROBOT_API_ID_LOCO_GET_FSM_ID,
    ROBOT_API_ID_LOCO_SET_FSM_ID,
    ROBOT_API_ID_LOCO_SET_VELOCITY,
    # ROBOT_API_ID_LOCO_SET_ARM_TASK,
)
ROBOT_API_ID_LOCO_SWITCH_TO_USER_CTRL = 7110
ROBOT_API_ID_LOCO_SWITCH_TO_INTERNAL_CTRL = 7111


class FSM_ID:
    kInvalid = 0
    kPassive = 1
    kSquat = 2
    kSit = 3
    kFixStand = 4
    kOnekeybreak = 706
    kLieDownStandUp = 702
    kWalkMotion = 500
    kWalkMotion3dofWaist = 501
    kHumanMimic2 = 503
    kCpyRun29dofs = 801
    kCpyWalkRun29dofs = 802
    kUserLowcmd = 1000
    kWjcgetup = 1001


# Unitree FSM id -> 本地 FSM 状态名 (见 states/__init__.py 中的 mode_list)
FSM_ID_TO_STATE = {
    FSM_ID.kInvalid: "zero_torque",
    FSM_ID.kPassive: "passive",
    FSM_ID.kSquat: "fixed_pose",
    FSM_ID.kSit: "fixed_pose",
    FSM_ID.kFixStand: "fixed_pose",
    FSM_ID.kOnekeybreak: "fixed_pose",
    FSM_ID.kLieDownStandUp: "fixed_pose",
    FSM_ID.kWalkMotion: "loco",
    FSM_ID.kWalkMotion3dofWaist: "loco",
    FSM_ID.kHumanMimic2: "loco",
    FSM_ID.kCpyRun29dofs: "loco",
    FSM_ID.kCpyWalkRun29dofs: "loco",
    FSM_ID.kUserLowcmd: "user_ctrl_mode",
    FSM_ID.kWjcgetup: "getup_mode",
}


class G1LocoServer(Server):
    def __init__(self, sim: bool = False, interface: str = "lo"):
        super().__init__(LOCO_SERVICE_NAME)

        self._fsm_id = FSM_ID.kInvalid
        self._last_fsm_id = FSM_ID.kInvalid
        self._lock = threading.Lock()
        self._control_thread = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(current_dir, "config.yaml")
        with open(config_file, "r") as f:
            print(f"Loading config from {config_file}")
            config = yaml.safe_load(f)

        # 允许通过命令行覆盖配置: --sim / --interface
        if sim:
            config["mode"] = "sim"
        if interface:
            config["network_interface"] = interface

        self._motion_controller = MotionController(config)

    def Init(self):
        self._SetApiVersion(LOCO_API_VERSION)
        self._RegistHandler(ROBOT_API_ID_LOCO_GET_FSM_ID, self._OnGetFsmId, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SET_FSM_ID, self._OnSetFsmId, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SET_VELOCITY, self._OnSetVelocity, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_SET_ARM_TASK, self._OnSetArmTask, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SWITCH_TO_USER_CTRL, self._OnSwitchToUserCtrl, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SWITCH_TO_INTERNAL_CTRL, self._OnSwitchToInternalCtrl, False)
        self._StartControlLoop()

    def _StartControlLoop(self):
        """在后台线程运行 50Hz 的 FSM 控制循环."""
        if self._control_thread is None or not self._control_thread.is_alive():
            self._control_thread = threading.Thread(
                target=self._motion_controller.run,
                name="loco_control",
                daemon=True,
            )
            self._control_thread.start()

    def Stop(self):
        self._motion_controller.stop()

    def _OnGetFsmId(self, parameter):
        return RPC_OK, json.dumps({"fsm_id": self._fsm_id})

    def _OnSetFsmId(self, parameter):
        try:
            p = json.loads(parameter)
            fsm_id = int(p.get("data", FSM_ID.kInvalid))
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        with self._lock:
            self._last_fsm_id = self._fsm_id
            self._fsm_id = fsm_id

        state_name = FSM_ID_TO_STATE.get(fsm_id)
        if state_name and state_name in self._motion_controller.fsm_controller.state:
            self._motion_controller.fsm_controller.change(state_name)
        else:
            print(f"[G1LocoServer] unknown fsm_id {fsm_id}, keeping current state")
        return RPC_OK, ""

    def _OnSetVelocity(self, parameter):
        try:
            p = json.loads(parameter)
            velocity = p.get("velocity", [0.0, 0.0, 0.0])
            if not isinstance(velocity, (list, tuple)) or len(velocity) < 3:
                return RPC_ERR_SERVER_API_PARAMETER, ""
            vel = np.array(velocity[:3], dtype=np.float32)
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        self._motion_controller.state_cmd.vel_cmd = vel
        return RPC_OK, ""

    # def _OnSetArmTask(self, parameter):
    #     try:
    #         p = json.loads(parameter)
    #         task_id = p.get("data")
    #     except (ValueError, TypeError, AttributeError):
    #         return RPC_ERR_SERVER_API_PARAMETER, ""
    #     print(f"[G1LocoServer] arm task set to {task_id}")
    #     return RPC_OK, ""

    def _OnSwitchToUserCtrl(self, parameter):
        if self._fsm_id not in [
            FSM_ID.kPassive,
            FSM_ID.kCpyRun29dofs,
            FSM_ID.kCpyWalkRun29dofs,
        ]:
            print(f"[G1LocoServer] cannot switch to user control from fsm_id {self._fsm_id}")
            return RPC_ERR_SERVER_API_PARAMETER, ""
        
        print("[G1LocoServer] switching to user control")
        state_name = FSM_ID_TO_STATE.get(FSM_ID.kUserLowcmd)
        if state_name and state_name in self._motion_controller.fsm_controller.state:
            self._motion_controller.fsm_controller.change(state_name)
        return RPC_OK, ""

    def _OnSwitchToInternalCtrl(self, parameter):
        class G1InternalFsmMode:
            LAST = 0    # 切换至用户开发模式前的运控模式
            PASSIVE = 1 # 阻尼模式
            WALKRUN = 2 # 走跑模式
        
        try:
            p = json.loads(parameter)
            mode = int(p.get("data", G1InternalFsmMode.LAST))
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        if mode == G1InternalFsmMode.LAST:
            fsm_id = self._last_fsm_id
        elif mode == G1InternalFsmMode.PASSIVE:
            fsm_id = FSM_ID.kPassive
        elif mode == G1InternalFsmMode.WALKRUN:
            fsm_id = FSM_ID.kCpyWalkRun29dofs
        else:
            print("[G1LocoServer] invalid internal FSM mode")
            return RPC_ERR_SERVER_API_PARAMETER, ""
        
        print(f"[G1LocoServer] switching to internal control, fsm_id={fsm_id}")
        return self._OnSetFsmId(
            json.dumps({"data": fsm_id})
        )