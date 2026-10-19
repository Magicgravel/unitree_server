from typing import List
from fsm.fsm_state import FSMState

from .zero_torque import ZeroTorque
from .passive_mode import PassiveMode
from .stand_up import StandUp
from .stand_down import StandDown
from .loco_mode import LocoMode

mode_list: List[FSMState] = [
    ZeroTorque,
    PassiveMode,
    StandUp,
    StandDown,
    LocoMode,
]