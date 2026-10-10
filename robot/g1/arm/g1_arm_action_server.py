import json
import threading

from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
)
from unitree_sdk2py.g1.arm.g1_arm_action_api import (
    ARM_ACTION_SERVICE_NAME,
    ARM_ACTION_API_VERSION,

    ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION,
    ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST,
    ROBOT_API_ID_ARM_ACTION_EXECUTE_CUSTOM_ACTION,
    ROBOT_API_ID_ARM_ACTION_STOP_CUSTOM_ACTION,
)

# G1 上肢 SDK 内置动作名称列表 (与客户端 action_map 保持一致)
ACTION_LIST = [
    "release arm",
    "two-hand kiss",
    "left kiss",
    "right kiss",
    "hands up",
    "clap",
    "high five",
    "hug",
    "heart",
    "right heart",
    "reject",
    "right hand up",
    "x-ray",
    "face wave",
    "high wave",
    "shake hand",
]


class G1ArmActionServer(Server):
    def __init__(self):
        super().__init__(ARM_ACTION_SERVICE_NAME)
        
        self._current_action_id = None
        self._current_action_name = None
        self._lock = threading.Lock()

    def Init(self):
        self._SetApiVersion(ARM_ACTION_API_VERSION)
        # 客户端通过 _Call (非二进制) 调用, 因此这里使用 _RegistHandler
        self._RegistHandler(ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION, self._OnExecuteAction, False)
        self._RegistHandler(ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST, self._OnGetActionList, False)
        self._RegistHandler(ROBOT_API_ID_ARM_ACTION_EXECUTE_CUSTOM_ACTION, self._OnExecuteCustomAction, False)
        self._RegistHandler(ROBOT_API_ID_ARM_ACTION_STOP_CUSTOM_ACTION, self._OnStopCustomAction, False)

    def _OnExecuteAction(self, parameter):
        try:
            p = json.loads(parameter)
            action_id = int(p.get("data", -1))
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        with self._lock:
            self._current_action_id = action_id
        print(f"[G1ArmActionServer] execute action id: {action_id}")
        return RPC_OK, ""

    def _OnGetActionList(self, parameter):
        return RPC_OK, json.dumps(ACTION_LIST)

    def _OnExecuteCustomAction(self, parameter):
        try:
            p = json.loads(parameter)
            action_name = p.get("action_name", "")
        except (ValueError, TypeError, AttributeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""

        with self._lock:
            self._current_action_name = action_name
        print(f"[G1ArmActionServer] execute custom action: {action_name}")
        return RPC_OK, ""

    def _OnStopCustomAction(self, parameter):
        with self._lock:
            self._current_action_name = None
        print("[G1ArmActionServer] custom action stopped.")
        return RPC_OK, ""
