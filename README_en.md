# unitree_server

Unitree robot server: exposes RPC services externally and forwards high-level `unitree_sdk2` interface calls to `unitree_mujoco`.

```
unitree_sdk (provides high-level interfaces, called by clients) <---> unitree_server (simulates the PC1 server, handles interface calls) <---> unitree_mujoco (robot simulation) or unitree_robot (real robot)
```

Supported: Unitree G1

Planned support: Unitree Go2, Unitree R1

## Features

| G1 Service | Module | Description |
|------|------|------|
| Locomotion control (`--loco`) | `G1LocoServer` | Full-body motion control based on FSM + motion policy (ONNX), [policy source](robot/g1/loco/policy/README.md) |
| Audio playback (`--audio`) | `G1AudioServer` | Receives and plays PCM audio streams (volume control / stop playback) |
| (In development) Upper-limb actions (`--arm`) | `G1ArmActionServer` | Executes built-in/custom upper-limb actions and retrieves action lists |

| Go2 Service | Module | Description |
|------|------|------|
| (In development) Motion control (`--sport`) | `Go2SportServer` | Full-body motion control based on FSM + motion policy (ONNX), [policy source](robot/go2/loco/policy/README.md) |

## Directory Structure

```
unitree_server/
├── unitree_server.py            # Server entry point
├── robot/
│   ├── g1/
│   │   ├── loco/                    # Locomotion control service
│   │   │   ├── g1_loco_server.py        #   RPC server
│   │   │   ├── motion.py                #   Motion controllers (MotionController / MoveController)
│   │   │   ├── config.yaml              #   Locomotion config
│   │   │   ├── fsm/                     #   Finite state machine
│   │   │   ├── states/                  #   FSM states (zero torque / damping / fixed posture / walking)
│   │   │   ├── common/                  #   Simulation / real robot low-level communication and data structures
│   │   │   └── policy/                  #   Motion policy (ONNX + deploy config)
│   │   ├── audio/                       # Audio service
│   │   └── arm/                         # Upper-limb action service (in development)
│   ├── go2/
│   │   └── sport/                   # Motion control service (in development)
│   ├── ...
├── example/                     # Client example scripts
└── unitree_mujoco/              # Simulation submodule (git submodule)
```

## Installation

```bash
# 1. Clone the repository and pull the simulation submodule
git clone https://github.com/Magicgravel/unitree_server.git
cd unitree_server
git submodule update --init --recursive

# 2. Set up a virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install unitree_sdk2py
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
pip install -e unitree_sdk2_python
# If installation fails, see:
# https://support.unitree.com/home/zh/developer/Python#heading-5

# 4. Fix a bug in unitree_sdk2_python at line 22
sed -i 's/^\(\s*\)self\.__apiBinarySet = {}\s*$/\1self.__apiBinarySet = set()/' unitree_sdk2py/rpc/server.py
```

## Quick Start

### 1. Start the server

```bash
# Simulation mode: start locomotion control + audio + upper-limb actions
python3 unitree_server.py --sim --loco --audio --arm

# Real robot mode: locomotion control only (modify network interface as needed)
# Must enter debug mode first
python3 unitree_server.py --loco --interface eth0 --domain_id 0
```

### 2. Command-line Arguments

| Argument | Default | Description |
|------|--------|------|
| `--domain_id` | `0` | DDS domain ID |
| `--interface` | `lo` | Network interface connected to the robot |
| `--sim` | OFF | Run `unitree_mujoco` simulation |
| `--robot` | `g1` | Robot model |
| `--joystick` | OFF | Enable gamepad to emulate R3 |
| `--loco` | OFF | Enable locomotion control service |
| `--audio` | OFF | Enable audio playback service |
| `--arm` | OFF | Enable upper-limb action service |

### 3. Client Examples

Clients connect to `unitree_server` using `unitree_sdk2` with `network_interface=lo, domain_id=1`.

```bash
# Integrated test for G1 LocoClient, AudioClient, and G1ArmActionClient interfaces
example/g1_sdk_test.ipynb

# Keyboard robot control (Go2/G1 etc.; switch SportClient per script comments)
python3 example/ctrl_keyboard.py lo

# Play WAV audio (requires 16kHz mono PCM)
python3 example/t_g1_play_wav.py lo example/test.wav
```

## Server Interfaces

- **G1**
  - **Locomotion control** (`service: "loco"`)
    - `GetFsmId`: Get FSM state
    - `SetFsmId`: Switch FSM state
      - Zero torque: 0
      - Damping: 1
      - Locked stand: 4
      - Motion control mode: 500, 501, 801, 802
    - `SetVelocity`: Set forward / lateral / yaw velocity
    - `SetArmTask`: Set arm task (in development)
    - `SwitchToUserCtrl`: Switch to user control mode
    - `SwitchToInternalCtrl`: Switch to internal motion control
  - **Audio** (`service: "audio"`)
    - `PlayStream`: Stream and play PCM data
    - `PlayStop` / `GetVolume` / `SetVolume`
  - **Upper-limb actions** (`in development` `service: "arm action"`)
    - `ExecuteAction` / `GetActionList` / `ExecuteCustomAction` / `StopCustomAction`
- **Go2**
  - **Motion control** (`service: "sport"`)
    - In development...

For specific API IDs, see `unitree_sdk2py/{robot}/{loco,audio,arm}/*_api.py`.

- G1 API reference: https://support.unitree.com/home/zh/G1_developer/services_interface
- Go2 API reference: https://support.unitree.com/home/zh/developer/Motion_Services_Interface_V2.0

## Notes

- `G1LocoServer` waits for `rt/lowstate` data before continuing. Make sure `unitree_mujoco` simulation is running or the network interface can reach the robot.
- Audio playback uses system `aplay` to play 16kHz mono S16_LE PCM. `alsa-utils` is required.
- In simulation mode, a MuJoCo viewer window will open. Exit the viewer or press `Ctrl+C` to stop the service.
