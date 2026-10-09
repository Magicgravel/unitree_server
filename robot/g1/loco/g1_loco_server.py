import json
import threading
import os
import yaml

from .g1_loco_server import MotionController

from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
    RPC_ERR_SERVER_INTERNAL,
)
from unitree_sdk2py.g1.loco.g1_loco_api import (
    LOCO_SERVICE_NAME,
    LOCO_API_VERSION,
    
    ROBOT_API_ID_LOCO_GET_FSM_ID,
    ROBOT_API_ID_LOCO_GET_FSM_MODE,
    ROBOT_API_ID_LOCO_GET_BALANCE_MODE,
    ROBOT_API_ID_LOCO_GET_SWING_HEIGHT,
    ROBOT_API_ID_LOCO_GET_STAND_HEIGHT,
    ROBOT_API_ID_LOCO_GET_PHASE, # deprecated
    
    ROBOT_API_ID_LOCO_SET_FSM_ID,
    ROBOT_API_ID_LOCO_SET_BALANCE_MODE,
    ROBOT_API_ID_LOCO_SET_SWING_HEIGHT,
    ROBOT_API_ID_LOCO_SET_STAND_HEIGHT,
    ROBOT_API_ID_LOCO_SET_VELOCITY,
    ROBOT_API_ID_LOCO_SET_ARM_TASK,
)

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

class LocoServer(Server):
    def __init__(self):
        super().__init__(LOCO_SERVICE_NAME)

        self._fsm_id = FSM_ID.kInvalid
        self._fsm_mode = 0
        self._lock = threading.Lock()
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(current_dir, "config.yaml")
        with open(config_file, 'r') as f:
            print(f"Loading config from {config_file}")
            config = yaml.safe_load(f)
        self._motion_controller = MotionController(config)

    def Init(self):
        self._SetApiVersion(LOCO_API_VERSION)
        self._RegistBinaryHandler(ROBOT_API_ID_LOCO_GET_FSM_ID, self._OnGetFsmId, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_GET_FSM_MODE, self._OnGetFsmMode, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_GET_BALANCE_MODE, self._OnGetBalanceMode, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_GET_SWING_HEIGHT, self._OnGetSwingHeight, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_GET_STAND_HEIGHT, self._OnGetStandHeight, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_GET_PHASE, self._OnGetPhase, False) # deprecated
        self._RegistHandler(ROBOT_API_ID_LOCO_SET_FSM_ID, self._OnSetFsmId, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_SET_BALANCE_MODE, self._OnSetBalanceMode, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_SET_SWING_HEIGHT, self._OnSetSwingHeight, False)
        # self._RegistHandler(ROBOT_API_ID_LOCO_SET_STAND_HEIGHT, self._OnSetStandHeight, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SET_VELOCITY, self._OnSetVelocity, False)
        self._RegistHandler(ROBOT_API_ID_LOCO_SET_ARM_TASK, self._OnSetArmTask, False)
    
    def _OnGetFsmId(self, parameter):
        return RPC_OK, json.dumps({"fsm_id": self._fsm_id})

    # def _OnGetFsmMode(self, parameter):
    #     return RPC_OK, json.dumps({"fsm_mode": self._fsm_mode})

    # def _OnGetBalanceMode(self, parameter):
    #     return RPC_OK, json.dumps({"balance_mode": 0})

    # def _OnGetSwingHeight(self, parameter):
    #     return RPC_OK, json.dumps({"swing_height": 0})

    # def _OnGetStandHeight(self, parameter):
    #     return RPC_OK, json.dumps({"stand_height": 0})

    # def _OnGetPhase(self, parameter):
    #     return RPC_OK, json.dumps({"phase": 0})

    def _OnSetFsmId(self, parameter):
        self._fsm_id = json.loads(parameter).get("fsm_id", FSM_ID.kInvalid)
        return RPC_OK, ""

    # def _OnSetBalanceMode(self, parameter):
    #     return RPC_OK, ""

    # def _OnSetSwingHeight(self, parameter):
    #     return RPC_OK, ""

    # def _OnSetStandHeight(self, parameter):
    #     return RPC_OK, ""

    def _OnSetVelocity(self, parameter):
        return RPC_OK, ""

    def _OnSetArmTask(self, parameter):
        return RPC_OK, ""