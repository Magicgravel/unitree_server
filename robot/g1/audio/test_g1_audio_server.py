from pathlib import Path
import sys
LIB_DIR = Path('~/my/unitree_mujoco').expanduser().resolve()
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from simulate_python.audio.audio_server import AudioServer

if __name__ == "__main__":
    ChannelFactoryInitialize(0, "lo")
    audio_server = AudioServer()
    audio_server.Init()
    audio_server.Start()
    
    print("[AudioServer] initialized.")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("[AudioServer] shutting down.")
        audio_server._OnStopPlay("{}")