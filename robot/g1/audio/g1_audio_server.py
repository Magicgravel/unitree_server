import json
import subprocess
import threading
from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
    RPC_ERR_SERVER_INTERNAL,
)
from unitree_sdk2py.g1.audio.g1_audio_api import (
    AUDIO_SERVICE_NAME,
    AUDIO_API_VERSION,
    
    ROBOT_API_ID_AUDIO_START_PLAY,
    ROBOT_API_ID_AUDIO_STOP_PLAY,
    ROBOT_API_ID_AUDIO_GET_VOLUME,
    ROBOT_API_ID_AUDIO_SET_VOLUME,
)

class G1AudioServer(Server):
    def __init__(self):
        super().__init__(AUDIO_SERVICE_NAME)
        self._volume = 80
        self._player = None
        self._lock = threading.Lock()

    def Init(self):
        self._SetApiVersion(AUDIO_API_VERSION)
        self._RegistBinaryHandler(ROBOT_API_ID_AUDIO_START_PLAY, self._OnStartPlay, False)
        self._RegistHandler(ROBOT_API_ID_AUDIO_STOP_PLAY, self._OnStopPlay, False)
        self._RegistHandler(ROBOT_API_ID_AUDIO_GET_VOLUME, self._OnGetVolume, False)
        self._RegistHandler(ROBOT_API_ID_AUDIO_SET_VOLUME, self._OnSetVolume, False)

    def _OnStartPlay(self, pcm_binary):
        # print("[AudioServer] start playing PCM stream.")
        with self._lock:
            if self._player is None or self._player.poll() is not None:
                self._player = subprocess.Popen(
                    ["aplay", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1"],
                    stdin=subprocess.PIPE,
                )
            try:
                self._player.stdin.write(bytes(pcm_binary))
                self._player.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                print(f"[AudioServer] play PCM failed: {e}")
                self._player = None
                return RPC_ERR_SERVER_INTERNAL, []
        return RPC_OK, []

    def _OnStopPlay(self, parameter):
        with self._lock:
            if self._player is not None:
                if self._player.poll() is None:
                    try:
                        self._player.stdin.close()
                    except OSError:
                        pass
                    try:
                        self._player.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        self._player.kill()
                        self._player.wait()
                self._player = None
        print("[AudioServer] playback stopped.")
        return RPC_OK, ""

    def _OnGetVolume(self, parameter):
        return RPC_OK, json.dumps({"volume": self._volume})

    def _OnSetVolume(self, parameter):
        try:
            p = json.loads(parameter)
            self._volume = int(p.get("volume", self._volume))
        except (ValueError, TypeError):
            return RPC_ERR_SERVER_API_PARAMETER, ""
        print(f"[AudioServer] volume set to {self._volume}")
        return RPC_OK, ""