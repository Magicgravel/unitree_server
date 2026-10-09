import argparse

from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from robot.g1.audio.g1_audio_server import AudioServer

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain_id', type=int, default=0, help='Specify the domain ID')
    parser.add_argument('--interface', type=str, default='lo', help='Specify the network interface to use')
    parser.add_argument('--loco', action='store_true', help='Enable loco mode')
    parser.add_argument('--audio', action='store_true', help='Enable audio')
    args = parser.parse_args()
    
    ChannelFactoryInitialize(args.domain_id, args.interface)
    
    if args.loco:
        # Initialize loco mode here
        pass
    if args.audio:
        server = AudioServer()
        server.start()