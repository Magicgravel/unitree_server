import socket
import struct
import sys
from typing import Optional
import wave

# Constants
GROUP_IP = "239.168.123.161"
PORT = 5555
WAV_SECOND = 30  # seconds to record
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # bytes per sample (16-bit)
CHANNELS = 1
WAV_LEN = SAMPLE_RATE * SAMPLE_WIDTH * WAV_SECOND  # total bytes

def get_local_ip_for_multicast() -> Optional[str]:
    """
    Find the local IP address that matches 192.168.123.x
    by inspecting all network interfaces.
    """
    def get_interfaces():
        import psutil
        ifaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ifaces[interface] = addr.address
        return ifaces

    try:
        interfaces = get_interfaces()
        for ip in interfaces.values():
            if ip.startswith("192.168.123."):
                print(f"Found local IP: {ip}")
                return ip
        print("No matching local IP found (192.168.123.x)")
        return None
    except Exception as e:
        print(f"Error detecting IP: {e}")
        return None

def write_wave_file(filename: str, rate: int, data: bytes, channels: int, sample_width: int):
    """Write raw PCM data to a .wav file."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(data)
    print(f"WAV file saved: {filename}")

def thread_mic():
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind to any interface on the port
    sock.bind(('', PORT))  # '' means INADDR_ANY

    # Get local IP for multicast interface
    local_ip = get_local_ip_for_multicast()
    if not local_ip:
        print("Failed to get local IP. Exiting.")
        return

    # Join multicast group
    mreq = struct.pack('4s4s', socket.inet_aton(GROUP_IP), socket.inet_aton(local_ip))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("Joined multicast group. Start receiving...")

    # Buffer to accumulate PCM data
    received_bytes = 0
    pcm_data = b''

    while received_bytes < WAV_LEN:
        try:
            data, _ = sock.recvfrom(2048)  # buffer size
            if len(data) > 0:
                pcm_data += data
                received_bytes += len(data)
                print(f"Received {received_bytes}/{WAV_LEN} bytes", end='\r')
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

    print(f"\nRecording finished! Total received: {len(pcm_data)} bytes")

    # Write to WAV file
    write_wave_file("record.wav", SAMPLE_RATE, pcm_data, CHANNELS, SAMPLE_WIDTH)

if __name__ == "__main__":
    try:
        thread_mic()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)