import os

from .beyond_mimic import BeyondMimic

current_dir = os.path.dirname(os.path.abspath(__file__))
policy_path = os.path.join(current_dir, "../policy/mimic/jntm")

class JntmMotion(BeyondMimic):
    name = 'jntm_motion'
    
    def __init__(self, kwargs: dict):
        kwargs["policy_path"] = policy_path
        kwargs["motion_name"] = "jntm"  # specify the motion name to load
        super().__init__(kwargs)
        self.name = JntmMotion.name