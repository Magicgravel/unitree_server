from .gamepad import Gamepad

class TeleopGamepad:
    def __init__(self, fsm_controller, config, network_interface=''):
        self.gamepad = Gamepad(network_interface)
        self.gamepad.Init()
        
        self.fsm_controller = fsm_controller
        self.config = config
        self.prev_buttons = {}
        self.btn_list = ['L1', 'L2', 'R1', 'R2', 'A', 'B', 'X', 'Y', 'Up', 'Down', 'Left', 'Right', 'Start', 'Select', 'F1', 'F3']

    def map_button(self, name):
        name = name.lower()
        mapping = {
            'lt': 'L2', 'rt': 'R2',
            'lb': 'L1', 'rb': 'R1',
            'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right',
            'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y',
            '1': 'L1', '3': 'R1',
            'start': 'Start', 'select': 'Select',
            'f1': 'F1', 'f3': 'F3'
        }
        return mapping.get(name, name)

    def update(self):
        if not self.gamepad or not hasattr(self.gamepad, 'botton') or not self.gamepad.botton:
            return

        current_state_name = getattr(self.fsm_controller.current_state, 'name', None)
        fsm_config = self.config.get('FSM', {})
        if current_state_name and current_state_name in fsm_config:
            transitions = fsm_config[current_state_name].get('transitions', {})
            for next_state, cond_str in transitions.items():
                parts = [p.strip() for p in cond_str.split('+')]
                condition_met = True
                for part in parts:
                    if '.on_pressed' in part:
                        btn_name = part.replace('.on_pressed', '').strip()
                        btn_attr = self.map_button(btn_name)
                        curr = getattr(self.gamepad.botton, btn_attr, 0)
                        prev = self.prev_buttons.get(btn_attr, 0)
                        if not (curr == 1 and prev == 0):
                            condition_met = False
                            break
                    else:
                        btn_name = part.strip()
                        btn_attr = self.map_button(btn_name)
                        curr = getattr(self.gamepad.botton, btn_attr, 0)
                        if curr != 1:
                            condition_met = False
                            break
                if condition_met:
                    print(f"Gamepad Transition: {current_state_name} -> {next_state}")
                    self.fsm_controller.change(next_state)
                    break
        
        # update prev buttons
        for b in self.btn_list:
            self.prev_buttons[b] = getattr(self.gamepad.botton, b, 0)
