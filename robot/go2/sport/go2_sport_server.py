import json
import os
import threading
import yaml

from unitree_sdk2py.rpc.server import Server
from unitree_sdk2py.rpc.internal import (
    RPC_OK,
    RPC_ERR_SERVER_API_PARAMETER,
)
from unitree_sdk2py.go2.sport.sport_api import (
    SPORT_SERVICE_NAME,
    SPORT_API_VERSION,
    
    SPORT_API_ID_DAMP,
    SPORT_API_ID_BALANCESTAND,
    SPORT_API_ID_STOPMOVE,
    SPORT_API_ID_STANDUP,
    SPORT_API_ID_STANDDOWN,
    SPORT_API_ID_RECOVERYSTAND,
    SPORT_API_ID_EULER,
    SPORT_API_ID_MOVE,
    # SPORT_API_ID_SIT,
    # SPORT_API_ID_RISESIT,
    # SPORT_API_ID_SPEEDLEVEL,
    # SPORT_API_ID_HELLO,
    # SPORT_API_ID_STRETCH,
    # SPORT_API_ID_CONTENT,
    # SPORT_API_ID_DANCE1,
    # SPORT_API_ID_DANCE2,
    # SPORT_API_ID_SWITCHJOYSTICK,
    # SPORT_API_ID_POSE,
    # SPORT_API_ID_SCRAPE,
    # SPORT_API_ID_FRONTFLIP,
    # SPORT_API_ID_FRONTJUMP,
    # SPORT_API_ID_FRONTPOUNCE,
    # SPORT_API_ID_HEART,
    # SPORT_API_ID_STATICWALK,
    # SPORT_API_ID_TROTRUN,
    # SPORT_API_ID_ECONOMICGAIT,
    # SPORT_API_ID_LEFTFLIP,
    # SPORT_API_ID_BACKFLIP,
    # SPORT_API_ID_HANDSTAND,
    # SPORT_API_ID_FREEWALK,
    # SPORT_API_ID_FREEBOUND,
    # SPORT_API_ID_FREEJUMP,
    # SPORT_API_ID_FREEAVOID,
    # SPORT_API_ID_CLASSICWALK,
    # SPORT_API_ID_WALKUPRIGHT,
    # SPORT_API_ID_CROSSSTEP,
    # SPORT_API_ID_AUTORECOVERY_SET,
    # SPORT_API_ID_AUTORECOVERY_GET,
    # SPORT_API_ID_SWITCHAVOIDMODE,
)


class Go2SportServer(Server):
    def __init__(self):
        super().__init__(SPORT_SERVICE_NAME)
    
    def Init(self):
        self._SetApiVersion(SPORT_API_VERSION)
        self._RegistHandler(SPORT_API_ID_DAMP, self._OnDamp, False)
        self._RegistHandler(SPORT_API_ID_BALANCESTAND, self._OnBalanceStand, False)
        self._RegistHandler(SPORT_API_ID_STOPMOVE, self._OnStopMove, False)
        self._RegistHandler(SPORT_API_ID_STANDUP, self._OnStandUp, False)
        self._RegistHandler(SPORT_API_ID_STANDDOWN, self._OnStandDown, False)
        self._RegistHandler(SPORT_API_ID_RECOVERYSTAND, self._OnRecoveryStand, False)
        self._RegistHandler(SPORT_API_ID_EULER, self._OnEuler, False)
        self._RegistHandler(SPORT_API_ID_MOVE, self._OnMove, False)
        # self._RegistHandler(SPORT_API_ID_SIT, self._OnSit, False)
        # self._RegistHandler(SPORT_API_ID_RISESIT, self._OnRiseSit, False)
        # self._RegistHandler(SPORT_API_ID_SPEEDLEVEL, self._OnSpeedLevel, False)
        # self._RegistHandler(SPORT_API_ID_HELLO, self._OnHello, False)
        # self._RegistHandler(SPORT_API_ID_STRETCH, self._OnStretch, False)
        # self._RegistHandler(SPORT_API_ID_CONTENT, self._OnContent, False)
        # self._RegistHandler(SPORT_API_ID_DANCE1, self._OnDance1, False)
        # self._RegistHandler(SPORT_API_ID_DANCE2, self._OnDance2, False)
        # self._RegistHandler(SPORT_API_ID_SWITCHJOYSTICK, self._OnSwitchJoystick, False)
        # self._RegistHandler(SPORT_API_ID_POSE, self._OnPose, False)
        # self._RegistHandler(SPORT_API_ID_SCRAPE, self._OnScrape, False)
        # self._RegistHandler(SPORT_API_ID_FRONTFLIP, self._OnFrontFlip, False)
        # self._RegistHandler(SPORT_API_ID_FRONTJUMP, self._OnFrontJump, False)
        # self._RegistHandler(SPORT_API_ID_FRONTPOUNCE, self._OnFrontPounce, False)
        # self._RegistHandler(SPORT_API_ID_HEART, self._OnHeart, False)
        # self._RegistHandler(SPORT_API_ID_STATICWALK, self._OnStaticWalk, False)
        # self._RegistHandler(SPORT_API_ID_TROTRUN, self._OnTrotRun, False)
        # self._RegistHandler(SPORT_API_ID_ECONOMICGAIT, self._OnEconomicGait, False)
        # self._RegistHandler(SPORT_API_ID_LEFTFLIP, self._OnLeftFlip, False)
        # self._RegistHandler(SPORT_API_ID_BACKFLIP, self._OnBackFlip, False)
        # self._RegistHandler(SPORT_API_ID_HANDSTAND, self._OnHandStand, False)
        # self._RegistHandler(SPORT_API_ID_FREEWALK, self._OnFreeWalk, False)
        # self._RegistHandler(SPORT_API_ID_FREEBOUND, self._OnFreeBound, False)
        # self._RegistHandler(SPORT_API_ID_FREEJUMP, self._OnFreeJump, False)
        # self._RegistHandler(SPORT_API_ID_FREEAVOID, self._OnFreeAvoid, False)
        # self._RegistHandler(SPORT_API_ID_CLASSICWALK, self._OnClassicWalk, False)
        # self._RegistHandler(SPORT_API_ID_WALKUPRIGHT, self._OnWalkUpright, False)
        # self._RegistHandler(SPORT_API_ID_CROSSSTEP, self._OnCrossStep, False)
        # self._RegistHandler(SPORT_API_ID_AUTORECOVERY_SET, self._OnAutoRecoverySet, False)
        # self._RegistHandler(SPORT_API_ID_AUTORECOVERY_GET, self._OnAutoRecoveryGet, False)
        # self._RegistHandler(SPORT_API_ID_SWITCHAVOIDMODE, self._OnSwitchAvoidMode, False)
    
    def _OnDamp(self, parameter):
        pass
    
    def _OnBalanceStand(self, parameter):
        pass
    
    def _OnStopMove(self, parameter):
        pass
    
    def _OnStandUp(self, parameter):
        pass

    def _OnStandDown(self, parameter):
        pass
    
    def _OnRecoveryStand(self, parameter):
        pass
    
    def _OnEuler(self, parameter):
        pass
    
    def _OnMove(self, parameter):
        pass