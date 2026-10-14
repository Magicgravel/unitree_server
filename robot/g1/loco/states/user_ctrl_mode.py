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
        self.user_lowcmd = None
        
    def run(self):
        if self.user_lowcmd is not None:
            for motor_idx in range(len(self.user_lowcmd.motor_cmd)):
                self.policy_output.actions[motor_idx] = self.user_lowcmd.motor_cmd[motor_idx].q
                self.policy_output.kps[motor_idx] = self.user_lowcmd.motor_cmd[motor_idx].kp
                self.policy_output.kds[motor_idx] = self.user_lowcmd.motor_cmd[motor_idx].kd
    
    def exit(self):
        self.user_lowcmd = None
