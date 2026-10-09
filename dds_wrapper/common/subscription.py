# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/common/Subscription.h

import threading
import time

from unitree_sdk2py.core.channel import ChannelSubscriber


class SubscriptionBase:
    """Base class for convenient subscription to topics.

    Port of unitree::robot::SubscriptionBase. Note that, like the C++ version,
    the continuous background updates may increase CPU usage.
    """

    def __init__(self, topic, msg_type, handler=None):
        self._topic = topic
        self._msg_type = msg_type

        self.msg_ = self._default_msg()
        self._mutex = threading.Lock()

        self.timeout_ms_ = 1000
        self._last_update_time = time.monotonic() - self.timeout_ms_ / 1000.0

        self._sub = ChannelSubscriber(topic, msg_type)
        if handler is not None:
            self._sub.Init(handler)
        else:
            self._sub.Init(self._default_handler)

    def _default_msg(self):
        """Return a default-initialized message. Subclasses must override."""
        raise NotImplementedError

    def _default_handler(self, msg):
        self._last_update_time = time.monotonic()
        with self._mutex:
            self.pre_communication()
            self.msg_ = msg
            self.post_communication()

    def set_timeout_ms(self, timeout_ms):
        self.timeout_ms_ = timeout_ms

    def isTimeout(self):
        return (time.monotonic() - self._last_update_time) > (self.timeout_ms_ / 1000.0)

    def wait_for_connection(self):
        t0 = time.monotonic()
        warn_info = False
        while self.isTimeout():
            time.sleep(0.1)
            if not warn_info and (time.monotonic() - t0) > 2.0:
                warn_info = True
                print("[dds_wrapper] Warning: Waiting for connection {}".format(self._topic))
        time.sleep(0.1)  # wait for stable communication
        if warn_info:
            print("[dds_wrapper] Info: Connected {}".format(self._topic))

    def pre_communication(self):
        """Hook called before receiving a message."""
        pass

    def post_communication(self):
        """Hook called after receiving a message."""
        pass
