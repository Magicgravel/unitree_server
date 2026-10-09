from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
import numpy as np

kds = [8,8,8,8,8,8,
      8,8,8,8,8,8,
      8,8,8,
      8,8,8,8,8,8,8,
      8,8,8,8,8,8,8]

kps = [0,0,0,0,0,0,
      0,0,0,0,0,0,
      0,0,0,
      0,0,0,0,0,0,0,
      0,0,0,0,0,0,0]

class PassiveMode(FSMState):
    name = 'passive'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = PassiveMode.name
        
        self.state_cmd = kwargs.get("state_cmd")
        self.policy_output = kwargs.get("policy_output")
        
        self.kds = np.array(kds, dtype=np.float32)
        self.kps = np.array(kps, dtype=np.float32)
    
    def enter(self):
        self.policy_output.kps = self.kps.copy()
        self.policy_output.kds = self.kds.copy()
    
    def run(self):
        actions = np.zeros(self.state_cmd.num_joints)
        
        self.policy_output.actions = actions.copy()
        self.policy_output.kps = self.kps.copy()
        self.policy_output.kds = self.kds.copy()
    
    def exit(self):
        self.policy_output.kps = self.kps.copy()
        self.policy_output.kds = self.kds.copy()
        