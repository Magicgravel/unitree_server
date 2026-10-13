from fsm.fsm_state import FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput

from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_

TOPIC_USER_LOWCMD = "rt/user_lowcmd"

class UserCtrlMode(FSMState):
    name = 'user_ctrl_mode'
    
    def __init__(self, kwargs):
        super().__init__()
        self.name = UserCtrlMode.name
        
        self.state_cmd: StateAndCmd = kwargs.get("state_cmd")
        self.policy_output: PolicyOutput = kwargs.get("policy_output")
        
        self.user_lowcmd_suber = ChannelSubscriber(TOPIC_USER_LOWCMD, LowCmd_)
        self.user_lowcmd_suber.Init(self.user_lowcmd_handler, 10)
        
        self.user_lowcmd: LowCmd_ = None

    def user_lowcmd_handler(self, msg: LowCmd_):
        self.user_lowcmd = msg
    
    def enter(self):
        pass
        
    def run(self):
        for j, motor_idx in enumerate(self.joint2motor_idx):
            self.policy_output.actions[motor_idx] = self.user_lowcmd.motor_cmd[j] if self.user_lowcmd else 0.0
            self.policy_output.kps[motor_idx] = self.user_lowcmd.kps[j] if self.user_lowcmd else 0.0
            self.policy_output.kds[motor_idx] = self.user_lowcmd.kds[j] if self.user_lowcmd else 0.0
    
    def exit(self):
        pass
