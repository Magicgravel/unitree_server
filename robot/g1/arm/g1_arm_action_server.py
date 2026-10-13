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
    # ROBOT_API_ID_ARM_ACTION_EXECUTE_CUSTOM_ACTION,
    # ROBOT_API_ID_ARM_ACTION_STOP_CUSTOM_ACTION,
)
# 这两个 API ID 在 unitree_sdk2_python 中暂未定义, 因此在这里手动定义
ROBOT_API_ID_ARM_ACTION_EXECUTE_CUSTOM_ACTION = 7108
ROBOT_API_ID_ARM_ACTION_STOP_CUSTOM_ACTION = 7109

from unitree_sdk2py.g1.arm.g1_arm_action_client import action_map
# action_map = {
#     "release arm": 99,
#     "two-hand kiss": 11,
#     "left kiss": 12,
#     "right kiss": 13,
#     "hands up": 15,
#     "clap": 17,
#     "high five": 18,
#     "hug": 19,
#     "heart": 20,
#     "right heart": 21,
#     "reject": 22,
#     "right hand up": 23,
#     "x-ray": 24,
#     "face wave": 25,
#     "high wave": 26,
#     "shake hand": 27,
# }


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
        return RPC_OK, json.dumps(action_map)

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
