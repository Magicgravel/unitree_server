# Copyright (c) 2025, Unitree Robotics Co., Ltd.
# All rights reserved.
#
# Python port of unitree/dds_wrapper/common/Publisher.h

import copy
import threading
import time

from unitree_sdk2py.core.channel import ChannelPublisher


class PublisherBase:
    """Base class for convenient publishing to topics.

    Port of unitree::robot::PublisherBase.
    """

    def __init__(self, topic, msg_type):
        self._topic = topic
        self._msg_type = msg_type
        self._publisher = ChannelPublisher(topic, msg_type)
        self._publisher.Init()

    def Write(self, sample, timeout=None):
        return self._publisher.Write(sample, timeout)

    def Close(self):
        self._publisher.Close()


class _Turn:
    REALTIME = 0
    NON_REALTIME = 1
    LOOP_NOT_STARTED = 2


class RealTimePublisher:
    """Publishes a message from a background thread with a realtime-safe handoff.

    Port of unitree::robot::RealTimePublisher. See
    https://github.com/ros-controls/realtime_tools for the original concept.

    Typical usage::

        pub = LowCmd("rt/lowcmd")
        while True:
            if pub.trylock():
                pub.msg_.motor_cmd[0].q = 1.0
                pub.unlockAndPublish()
            time.sleep(0.002)
    """

    def __init__(self, topic, msg_type):
        self._topic = topic
        self._msg_type = msg_type

        self._publisher = ChannelPublisher(topic, msg_type)
        self._publisher.Init()

        # Subclasses build the fully-initialized message here, before the
        # publishing thread starts (avoids the constructor race of the C++ code).
        self.msg_ = self._default_msg()

        self._mutex = threading.Lock()
        self._keep_running = True
        self._is_running = False
        self._turn = _Turn.LOOP_NOT_STARTED

        self._thread = threading.Thread(
            target=self._publishing_loop,
            name="rt_pub_{}".format(topic),
            daemon=True,
        )
        self._thread.start()

    def _default_msg(self):
        """Return a default-initialized message. Subclasses must override."""
        raise NotImplementedError

    def stop(self):
        self._keep_running = False

    def is_running(self):
        return self._is_running

    def trylock(self):
        """Try to get unique access to ``msg_`` from the realtime loop."""
        if self._mutex.acquire(blocking=False):
            if self._turn == _Turn.REALTIME:
                return True
            self._mutex.release()
            return False
        return False

    def lock(self):
        """Block until unique access to ``msg_`` is acquired."""
        while not self._mutex.acquire(blocking=False):
            time.sleep(0.001)

    def unlock(self):
        """Release ``msg_`` without publishing."""
        self._mutex.release()

    def unlockAndPublish(self):
        """Release ``msg_`` and hand it over to the publishing loop."""
        self._turn = _Turn.NON_REALTIME
        self._mutex.release()

    def pre_communication(self):
        """Hook called before sending the message."""
        pass

    def post_communication(self):
        """Hook called after sending the message."""
        pass

    def _publishing_loop(self):
        self._is_running = True
        self._turn = _Turn.REALTIME

        while self._keep_running:
            # Lock msg_ and copy it.
            self.lock()
            while self._turn != _Turn.NON_REALTIME and self._keep_running:
                self.unlock()
                time.sleep(0.001)
                self.lock()

            self.pre_communication()
            outgoing = copy.deepcopy(self.msg_)
            self._turn = _Turn.REALTIME
            self.unlock()

            if self._keep_running:
                self._publisher.Write(outgoing)
            self.post_communication()

        self._is_running = False
