import json
import os
import threading
import numpy as np
import yaml
import time

from .motion import MotionController

from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
)
from unitree_sdk2py.go2.sport.sport_api import (
    SPORT_SERVICE_NAME,
    SPORT_API_VERSION,
    
    SPORT_API_ID_DAMP,
    SPORT_API_ID_BALANCESTAND,
    SPORT_API_ID_STOPMOVE,
    SPORT_API_ID_STANDUP,
    SPORT_API_ID_STANDDOWN,
    SPORT_API_ID_RECOVERYSTAND,
    SPORT_API_ID_EULER,
    SPORT_API_ID_MOVE,
    # SPORT_API_ID_SIT,
    # SPORT_API_ID_RISESIT,
    # SPORT_API_ID_SPEEDLEVEL,
    # SPORT_API_ID_HELLO,
    # SPORT_API_ID_STRETCH,
    # SPORT_API_ID_CONTENT,
    # SPORT_API_ID_DANCE1,
    # SPORT_API_ID_DANCE2,
    # SPORT_API_ID_SWITCHJOYSTICK,
    # SPORT_API_ID_POSE,
    # SPORT_API_ID_SCRAPE,
    # SPORT_API_ID_FRONTFLIP,
    # SPORT_API_ID_FRONTJUMP,
    # SPORT_API_ID_FRONTPOUNCE,
    # SPORT_API_ID_HEART,
    # SPORT_API_ID_STATICWALK,
    # SPORT_API_ID_TROTRUN,
    # SPORT_API_ID_ECONOMICGAIT,
    # SPORT_API_ID_LEFTFLIP,
    # SPORT_API_ID_BACKFLIP,
    # SPORT_API_ID_HANDSTAND,
    # SPORT_API_ID_FREEWALK,
    # SPORT_API_ID_FREEBOUND,
    # SPORT_API_ID_FREEJUMP,
    # SPORT_API_ID_FREEAVOID,
    # SPORT_API_ID_CLASSICWALK,
    # SPORT_API_ID_WALKUPRIGHT,
    # SPORT_API_ID_CROSSSTEP,
    # SPORT_API_ID_AUTORECOVERY_SET,
    # SPORT_API_ID_AUTORECOVERY_GET,
    # SPORT_API_ID_SWITCHAVOIDMODE,
)


class FSM_ID:
    kInvalid = 0
    kPassive = 1
    kSquat = 2
    kSit = 3
    kStandUp = 4
    kStandDown = 5
    kWalkMotion = 500

# Unitree FSM id -> 本地 FSM 状态名 (见 states/__init__.py 中的 mode_list)
FSM_ID_TO_STATE = {
    FSM_ID.kInvalid: "zero_torque",
    FSM_ID.kPassive: "passive",
    FSM_ID.kSquat: "stand_up",
    FSM_ID.kStandUp: "stand_up",
    FSM_ID.kStandDown: "stand_down",
    FSM_ID.kWalkMotion: "loco_mode",
}

class Go2SportServer(Server):
    def __init__(self, context: dict):
        super().__init__(SPORT_SERVICE_NAME)
        
        self._fsm_id = FSM_ID.kInvalid
        self._lock = threading.Lock()
        self._control_thread = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(current_dir, "config.yaml")
        with open(config_file, "r") as f:
            print(f"Loading config from {config_file}")
            config: dict = yaml.safe_load(f)

        config.update(context)
        context = config

        self._motion_controller = MotionController(context)
    
    def Init(self):
        self._SetApiVersion(SPORT_API_VERSION)
        self._RegistHandler(SPORT_API_ID_DAMP, self._OnDamp, False)
        self._RegistHandler(SPORT_API_ID_BALANCESTAND, self._OnBalanceStand, False)
        self._RegistHandler(SPORT_API_ID_STOPMOVE, self._OnStopMove, False)
        self._RegistHandler(SPORT_API_ID_STANDUP, self._OnStandUp, False)
        self._RegistHandler(SPORT_API_ID_STANDDOWN, self._OnStandDown, False)
        self._RegistHandler(SPORT_API_ID_RECOVERYSTAND, self._OnRecoveryStand, False)
        self._RegistHandler(SPORT_API_ID_EULER, self._OnEuler, False)
        self._RegistHandler(SPORT_API_ID_MOVE, self._OnMove, False)
        # self._RegistHandler(SPORT_API_ID_SIT, self._OnSit, False)
        # self._RegistHandler(SPORT_API_ID_RISESIT, self._OnRiseSit, False)
        # self._RegistHandler(SPORT_API_ID_SPEEDLEVEL, self._OnSpeedLevel, False)
        # self._RegistHandler(SPORT_API_ID_HELLO, self._OnHello, False)
        # self._RegistHandler(SPORT_API_ID_STRETCH, self._OnStretch, False)
        # self._RegistHandler(SPORT_API_ID_CONTENT, self._OnContent, False)
        # self._RegistHandler(SPORT_API_ID_DANCE1, self._OnDance1, False)
        # self._RegistHandler(SPORT_API_ID_DANCE2, self._OnDance2, False)
        # self._RegistHandler(SPORT_API_ID_SWITCHJOYSTICK, self._OnSwitchJoystick, False)
        # self._RegistHandler(SPORT_API_ID_POSE, self._OnPose, False)
        # self._RegistHandler(SPORT_API_ID_SCRAPE, self._OnScrape, False)
        # self._RegistHandler(SPORT_API_ID_FRONTFLIP, self._OnFrontFlip, False)
        # self._RegistHandler(SPORT_API_ID_FRONTJUMP, self._OnFrontJump, False)
        # self._RegistHandler(SPORT_API_ID_FRONTPOUNCE, self._OnFrontPounce, False)
        # self._RegistHandler(SPORT_API_ID_HEART, self._OnHeart, False)
        # self._RegistHandler(SPORT_API_ID_STATICWALK, self._OnStaticWalk, False)
        # self._RegistHandler(SPORT_API_ID_TROTRUN, self._OnTrotRun, False)
        # self._RegistHandler(SPORT_API_ID_ECONOMICGAIT, self._OnEconomicGait, False)
        # self._RegistHandler(SPORT_API_ID_LEFTFLIP, self._OnLeftFlip, False)
        # self._RegistHandler(SPORT_API_ID_BACKFLIP, self._OnBackFlip, False)
        # self._RegistHandler(SPORT_API_ID_HANDSTAND, self._OnHandStand, False)
        # self._RegistHandler(SPORT_API_ID_FREEWALK, self._OnFreeWalk, False)
        # self._RegistHandler(SPORT_API_ID_FREEBOUND, self._OnFreeBound, False)
        # self._RegistHandler(SPORT_API_ID_FREEJUMP, self._OnFreeJump, False)
        # self._RegistHandler(SPORT_API_ID_FREEAVOID, self._OnFreeAvoid, False)
        # self._RegistHandler(SPORT_API_ID_CLASSICWALK, self._OnClassicWalk, False)
        # self._RegistHandler(SPORT_API_ID_WALKUPRIGHT, self._OnWalkUpright, False)
        # self._RegistHandler(SPORT_API_ID_CROSSSTEP, self._OnCrossStep, False)
        # self._RegistHandler(SPORT_API_ID_AUTORECOVERY_SET, self._OnAutoRecoverySet, False)
        # self._RegistHandler(SPORT_API_ID_AUTORECOVERY_GET, self._OnAutoRecoveryGet, False)
        # self._RegistHandler(SPORT_API_ID_SWITCHAVOIDMODE, self._OnSwitchAvoidMode, False)
        self._StartControlLoop()

    def _StartControlLoop(self):
        """在后台线程运行 50Hz 的 FSM 控制循环."""
        if self._control_thread is None or not self._control_thread.is_alive():
            self._control_thread = threading.Thread(
                target=self._motion_controller.run,
                name="sport_control",
                daemon=True,
            )
            self._control_thread.start()

    def Stop(self):
        self._motion_controller.stop()
    
    def set_fsm(self, fsm_id):
        with self._lock:
            self._fsm_id = fsm_id
        
        state_name = FSM_ID_TO_STATE.get(fsm_id)
        if state_name and state_name in self._motion_controller.fsm_controller.state:
            self._motion_controller.fsm_controller.change(state_name)
        else:
            print(f"[Go2LocoServer] unknown fsm_id {fsm_id}, keeping current state")
        return RPC_OK, ""
    
    def _OnDamp(self, parameter):
        return self.set_fsm(FSM_ID.kPassive)
    
    def _OnBalanceStand(self, parameter):
        return self.set_fsm(FSM_ID.kWalkMotion)
    
    def _OnStopMove(self, parameter):
        return self._OnMove(
            json.dumps({"x": 0.0, "y": 0.0, "z": 0.0})
        )
    
    def _OnStandUp(self, parameter):
        ret = self.set_fsm(FSM_ID.kStandUp)
        time.sleep(2.0)
        ret = self.set_fsm(FSM_ID.kWalkMotion)
        return ret

    def _OnStandDown(self, parameter):
        return self.set_fsm(FSM_ID.kStandDown)
    
    def _OnRecoveryStand(self, parameter):
        return self.set_fsm(FSM_ID.kWalkMotion)
    
    def _OnEuler(self, parameter):
        try:
            p = json.loads(parameter)
            roll = p.get("x", 0.0)
            pitch = p.get("y", 0.0)
            yaw = p.get("z", 0.0)
            euler = np.array([roll, pitch, yaw], dtype=np.float32)
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""
        
        self._motion_controller.state_cmd.euler_cmd = euler
        return RPC_OK, ""
    
    def _OnMove(self, parameter):
        try:
            p = json.loads(parameter)
            x = p.get("x", 0.0)
            y = p.get("y", 0.0)
            z = p.get("z", 0.0)
            vel = np.array([x, y, z], dtype=np.float32)
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        self._motion_controller.state_cmd.vel_cmd = vel
        return RPC_OK, ""