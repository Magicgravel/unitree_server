from typing import List
from fsm.fsm_state import FSMState

from .zero_torque import ZeroTorque
from .passive_mode import PassiveMode
from .fixed_pose import FixedPose
from .loco_mode import LocoMode
# from .loco_mode_pt import LocoModePt
# from .loco_mode_wbc_fsm import LocoMode_wbc_fsm
# from .jntm_motion import JntmMotion
# from .unistore_motion import UsMotion

mode_list: List[FSMState] = [
    ZeroTorque,
    PassiveMode,
    FixedPose,
    LocoMode,
    # LocoModePt,
    # LocoMode_wbc_fsm,
    # JntmMotion,
    # UsMotion,
]