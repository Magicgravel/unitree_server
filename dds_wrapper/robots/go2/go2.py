# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/robots/go2/go2.h

import time

from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient


def shutdown():
    """Close the default controller.

    Run this function before publishing to rt/lowcmd.
    """
    msc = MotionSwitcherClient()
    msc.SetTimeout(3.0)
    msc.Init()

    while True:
        status, data = msc.CheckMode()
        name = ""
        if status == 0 and data is not None:
            name = data.get("name", "")
        if not name:
            break
        if msc.ReleaseMode() != 0:
            print("[dds_wrapper] Warning: Failed to switch to Release Mode.")
        time.sleep(3)
