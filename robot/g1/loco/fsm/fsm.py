from .fsm_state import FSMState

CHANGE = 1
NORMAL = 2

class FSM:
    def __init__(self, fsm_state_list: list[FSMState]=None):
        self.fsm_mode = NORMAL
        self.state = {}
        self.current_state: FSMState = None
        self.next_state: FSMState = None
        
        if fsm_state_list != None:
            for fsm_state in fsm_state_list:
                if isinstance(fsm_state, FSMState):
                    self.register(fsm_state)
                    print(f'{fsm_state.name} registed.')
    
    def register(self, state: FSMState):
        self.state[state.name] = state
        # print(f'FSM register state: {state.name}')
    
    def change(self, fsm_state):
        if isinstance(fsm_state, FSMState):
            self.next_state = fsm_state
        elif isinstance(fsm_state, str) and (fsm_state in self.state.keys()):
            self.next_state = self.state[fsm_state]
        self.fsm_mode = CHANGE
        print(f'FSM will change to {self.next_state.name}')
    
    def run(self):
        if self.fsm_mode == NORMAL:
            self.current_state.run()
        elif self.fsm_mode == CHANGE:
            if self.current_state != None:
                self.current_state.exit()
            self.current_state = self.next_state
            self.current_state.enter()
            self.next_state = None
            self.fsm_mode = NORMAL
            self.current_state.run()