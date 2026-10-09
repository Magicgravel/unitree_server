import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from wav import read_wav, play_pcm_stream

if __name__ == "__main__":
    net_interface = sys.argv[1]
    wav_path = sys.argv[2]

    ChannelFactoryInitialize(0, net_interface)
    audioClient = AudioClient()
    audioClient.SetTimeout(10.0)
    audioClient.Init()
    
    if wav_path == 'stop':
        audioClient.PlayStop("example")
        print("[INFO] Stopped playback.")
        exit(0)
    
    audioClient.SetVolume(80)

    pcm_list, sample_rate, num_channels, is_ok = read_wav(wav_path)
    print(f"[DEBUG] Read success: {is_ok}")
    print(f"[DEBUG] Sample rate: {sample_rate} Hz")
    print(f"[DEBUG] Channels: {num_channels}")
    print(f"[DEBUG] PCM byte length: {len(pcm_list)}")
    
    if not is_ok or sample_rate != 16000 or num_channels != 1:
        print("[ERROR] Failed to read WAV file or unsupported format (must be 16kHz mono)")
        exit(1)

    play_pcm_stream(audioClient, pcm_list, "example")

    # audioClient.PlayStop("example")
