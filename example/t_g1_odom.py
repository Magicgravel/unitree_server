import sys
import time
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize

from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

TOPIC = 'rt/lf/odommodestate'

def msg_handler(msg: SportModeState_):
    estimator_state = msg

    print("position info: ")
    print("x: ", estimator_state.position[0])
    print("y: ", estimator_state.position[1])
    print("z: ", estimator_state.position[2])

    print("velocity info: ")
    print("x: ", estimator_state.velocity[0])
    print("y: ", estimator_state.velocity[1])
    print("z: ", estimator_state.velocity[2])

    print("eular angle info: ")
    print("x: ", estimator_state.imu_state.rpy[0])
    print("y: ", estimator_state.imu_state.rpy[1])
    print("z: ", estimator_state.imu_state.rpy[2])

    print("yaw speed info: ")
    print(estimator_state.yaw_speed)

    print("Quaternion info: ")
    print("w: ", estimator_state.imu_state.quaternion[0])
    print("x: ", estimator_state.imu_state.quaternion[1])
    print("y: ", estimator_state.imu_state.quaternion[2])
    print("z: ", estimator_state.imu_state.quaternion[3])

if __name__ == '__main__':
    ChannelFactoryInitialize(0, sys.argv[1])  # 改为您用的设备连接机器人的网口名称
    
    suber = ChannelSubscriber(TOPIC, SportModeState_)
    suber.Init(msg_handler, 10)
    
    while True:
        time.sleep(10)
