class FSMState:
    def __init__(self):
        self.name = ''
        self.control_dt = 0.02
    
    def enter(self):
        raise NotImplementedError("enter() function must be implement!")
    
    def run(self):
        raise NotImplementedError("run() function must be implement!")
    
    def exit(self):
        raise NotImplementedError("exit() function must be implement!")