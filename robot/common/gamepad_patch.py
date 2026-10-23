import pygame


class GamepadPatch:
    def __init__(self, index=0):
        pygame.init()
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
            self.joystick = pygame.joystick.Joystick(index) 
            self.joystick.init()
        else:
            print("未找到手柄")
        
        self.button_dict = {"LS": 8, "RS": 9}
    
    def set_patch(self, button_dict):
        self.button_dict = button_dict
    
    def patch(self, unitree_joystick):
        pygame.event.pump()
        for name, button_id in self.button_dict.items():
            if self.joystick.get_button(button_id):
                getattr(unitree_joystick, name).update(True)
            else:
                getattr(unitree_joystick, name).update(False)

