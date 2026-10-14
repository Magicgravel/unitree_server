# unitree_server

Unitree 机器人服务端：对外提供 RPC 服务，把 `unitree_sdk2` 的高层接口调用转发到 `unitree_mujoco`。

```
unitree_sdk(提供高层接口，客户端调用) <---> unitree_server(模拟PC1服务端，处理接口调用) <---> unitree_mujoco(机器人仿真) 或 unitree_robot(实机)
```

支持：Unitree G1

计划支持：Unitree Go2、Unitree R1

## 功能

| G1 服务 | 模块 | 说明 |
|------|------|------|
| 运动控制 (`--loco`) | `G1LocoServer` | 基于 FSM + 运动策略（ONNX）的全身运动控制，[策略来源](robot/g1/loco/policy/README.md) |
| 语音播放 (`--audio`) | `G1AudioServer` | 接收 PCM 音频流并播放（音量控制 / 停止播放） |
| (开发中) 上肢动作 (`--arm`) | `G1ArmActionServer` | 执行内置 / 自定义上肢动作，获取动作列表 |

| Go2 服务 | 模块 | 说明 |
|------|------|------|
| (开发中) 运动控制 (`--sport`) | `Go2SportServer` | 基于 FSM + 运动策略（ONNX）的全身运动控制 |

## 目录结构

```
unitree_server/
├── unitree_server.py            # 服务入口
├── robot/
│   ├── g1/
│   │   ├── loco/                    # 运动控制服务
│   │   │   ├── g1_loco_server.py        #   RPC 服务端
│   │   │   ├── motion.py                #   运动控制器 (MotionController / MoveController)
│   │   │   ├── config.yaml              #   运动控制配置
│   │   │   ├── fsm/                     #   有限状态机
│   │   │   ├── states/                  #   FSM 状态 (零力矩 / 被动 / 固定姿态 / 行走)
│   │   │   ├── common/                  #   仿真 / 实机底层通信、数据结构
│   │   │   └── policy/                  #   运动策略 (ONNX + deploy 配置)
│   │   ├── audio/                       # 语音服务
│   │   └── arm/                         # 上肢动作服务（开发中）
│   ├── go2/
│   │   └── sport/                   # 运动控制服务（开发中）
│   ├── ...
├── example/                     # 客户端示例脚本
└── unitree_mujoco/              # 仿真子模块 (git submodule)
```

## 安装

```bash
# 1. 克隆仓库并拉取仿真子模块
git clone https://github.com/Magicgravel/unitree_server.git
cd unitree_server
git submodule update --init --recursive

# 2. 配置虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 安装 unitree_sdk2py
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
pip install -e unitree_sdk2_python
# 若安装遇到报错请看：
# https://support.unitree.com/home/zh/developer/Python#heading-5

# 4. 修复 unitree_sdk2_python 代码Bug，22行处
sed -i 's/^\(\s*\)self\.__apiBinarySet = {}\s*$/\1self.__apiBinarySet = set()/' unitree_sdk2py/rpc/server.py
```

## 快速开始

### 1. 启动服务

```bash
# 仿真模式，同时启动运动控制 + 语音 + 上肢动作
python3 unitree_server.py --sim --loco --audio --arm

# 实机模式，仅运动控制（网卡按实际修改）
# 需先进调试模式
python3 unitree_server.py --loco --interface eth0 --domain_id 0

# 仅语音服务
python3 unitree_server.py --audio
```

### 2. 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--domain_id` | `0` | DDS 域 ID |
| `--interface` | `lo` | 连接机器人的网卡名称 |
| `--sim` | OFF | 运行 unitree_mujoco 仿真 |
| `--robot` | `g1` | 机器人型号 |
| `--joystick` | OFF | 启动使用游戏手柄模拟R3 |
| `--loco` | OFF | 启动运动控制服务 |
| `--audio` | OFF | 启动语音播放服务 |
| `--arm` | OFF | 启动上肢动作服务 |

### 3. 客户端示例

客户端是用 unitree_sdk2 通过 `network_interface=lo, domain_id=1` 连接到 unitree_server

```bash
# G1 的 LocoClient、AudioClient、G1ArmActionClient 接口综合测试
example/g1_sdk_test.ipynb

# 键盘控制机器人 (Go2/G1 等，按脚本内注释切换 SportClient)
python3 example/ctrl_keyboard.py lo

# 播放 WAV 语音 (需 16kHz 单声道 PCM)
python3 example/t_g1_play_wav.py lo example/test.wav

# 停止播放
python3 example/t_g1_play_wav.py lo stop

# 订阅里程计状态
python3 example/t_g1_odom.py lo

# 从机器人麦克风组播录制 30s 音频
python3 example/t_g1_record.py
```

## 服务端接口

- **G1**
  - **运动控制** (`service: "loco"`)
    - `GetFsmId`：获取 FSM 状态
    - `SetFsmId`：切换 FSM 状态
      - 零力矩：0
      - 阻尼：1
      - 锁定站立：4
      - 运控模式：500，501，801，802
    - `SetVelocity`：设置前进 / 横移 / 转向速度
    - `SetArmTask`：设置手臂任务（开发中）
    - `SwitchToUserCtrl`：切换到用户模式
    - `SwitchToInternalCtrl`：切换到内部运控
  - **语音** (`service: "audio"`)
    - `PlayStream`：流式播放 PCM 数据
    - `PlayStop` / `GetVolume` / `SetVolume`
  - **上肢动作** (`开发中` `service: "arm action"`)
    - `ExecuteAction` / `GetActionList` / `ExecuteCustomAction` / `StopCustomAction`
- **Go2**
  - **运动控制** (`service: "sport"`)
    - 开发中...

具体 API ID 见 `unitree_sdk2py/{robot}/{loco,audio,arm}/*_api.py`。

G1 API 说明：https://support.unitree.com/home/zh/G1_developer/services_interface

## 注意事项

- `G1LocoServer` 会等待 `rt/lowstate` 数据到达后才继续，请确保 打开unitree_mujoco仿真 或 网卡与机器人连通。
- 语音播放使用系统 `aplay` 播放 16kHz 单声道 S16_LE PCM，需安装 `alsa-utils`。
- 仿真模式会打开 MuJoCo viewer 窗口，退出 viewer 或 `Ctrl+C` 可停止服务。