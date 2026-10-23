ROBOT = 'go2'
ROBOT_SCENE = "unitree_mujoco/unitree_robots/" + ROBOT + "/scene.xml" # Robot scene
DOMAIN_ID = 1
INTERFACE = 'lo'

USE_JOYSTICK = True
JOYSTICK_TYPE = "xbox" # support "xbox" and "switch" gamepad layout
JOYSTICK_DEVICE = 0 # Joystick number

PRINT_SCENE_INFORMATION = False
ENABLE_ELASTIC_BAND = False

SIMULATE_DT = 0.005  # Need to be larger than the runtime of viewer.sync()
VIEWER_DT = 0.02  # 50 fps for viewer
