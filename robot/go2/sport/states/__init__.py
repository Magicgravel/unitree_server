from typing import List
from fsm.fsm_state import FSMState

from .zero_torque import ZeroTorque
from .passive_mode import PassiveMode
from .fixed_pose import FixedPose
# from .loco_mode import LocoMode

mode_list: List[FSMState] = [
    ZeroTorque,
    PassiveMode,
    FixedPose,
    # LocoMode,
]