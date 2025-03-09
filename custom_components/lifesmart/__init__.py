import subprocess
import urllib.request
import json
import time
import datetime
import hashlib
import logging
import threading
import websocket
import asyncio

import voluptuous as vol
import sys

sys.setrecursionlimit(100000)

from homeassistant.const import (
    CONF_FRIENDLY_NAME,
)
from homeassistant.components.climate.const import HVACMode

from homeassistant.core import callback
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

SPEED_OFF = "Speed_Off"
SPEED_LOW = "Speed_Low"
SPEED_MEDIUM = "Speed_Medium"
SPEED_HIGH = "Speed_High"

CONF_LIFESMART_APPKEY = "appkey"
CONF_LIFESMART_APPTOKEN = "apptoken"
CONF_LIFESMART_USERTOKEN = "usertoken"
CONF_LIFESMART_USERID = "userid"
CONF_EXCLUDE_ITEMS = "exclude"
CONF_LIFESMART_USERNAME = "username"
CONF_LIFESMART_PASSWORD = "password"

# 开关
SWITCH_TYPES = [
    "SL_SF_RC",
    "SL_SW_RC",
    "SL_SW_IF3",
    "SL_SF_IF3",
    "SL_SW_CP3",
    "SL_SW_RC3",
    "SL_SW_IF2",
    "SL_SF_IF2",
    "SL_SW_CP2",
    "SL_SW_FE2",
    "SL_SW_RC2",
    "SL_SW_ND2",
    "SL_MC_ND2",
    "SL_SW_IF1",
    "SL_SW_IF2",
    "SL_SF_IF1",
    "SL_SW_CP1",
    "SL_SW_FE1",
    "SL_OL_W",
    "SL_SW_RC1",
    "SL_SW_ND1",
    "SL_MC_ND1",
    "SL_SW_ND3",
    "SL_MC_ND3",
    "SL_SW_ND2",
    "SL_MC_ND2",
    "SL_SW_ND1",
    "SL_MC_ND1",
    "SL_S",
    "SL_SPWM",
    "SL_P_SW",
    "SL_SW_DM1",
    "SL_SW_MJ2",
    "SL_SW_MJ1",
    "SL_OL",
    "SL_OL_3C",
    "SL_OL_DE",
    "SL_OL_UK",
    "SL_OL_UL",
    "OD_WE_OT1",
    "SL_NATURE",
    "SL_SC_BB"
]
# 灯
LIGHT_TYPES = [
    "SL_OL_W",
    "SL_SW_IF1",
    "SL_SW_IF3",
    "SL_CT_RGBW"
]
QUANTUM_TYPES = [
    "OD_WE_QUAN"
]
SPOT_TYPES = [
    "MSL_IRCTL",
    "OD_WE_IRCTL",
    "SL_SPOT"
]
# 传感器
BINARY_SENSOR_TYPES = [
    "SL_SC_G",
    "SL_SC_BG",
    "SL_SC_MHW ",
    "SL_SC_BM",
    "SL_SC_CM",
    "SL_P_A"
]
# 窗帘
COVER_TYPES = [
    "SL_DOOYA",
    "SL_SW_WIN"
]
# 气体传感器
GAS_SENSOR_TYPES = [
    "SL_SC_WA ",
    "SL_SC_CH",
    "SL_SC_CP",
    "ELIQ_EM"
]
EV_SENSOR_TYPES = [
    "SL_SC_THL",
    "SL_SC_BE",
    "SL_SC_CQ"
]
OT_SENSOR_TYPES = [
    "SL_SC_MHW",
    "SL_SC_BM",
    "SL_SC_G",
    "SL_SC_BG"
]
# 锁
LOCK_TYPES = [
    "SL_LK_LS",
    "SL_LK_GTM",
    "SL_LK_AG",
    "SL_LK_SG",
    "SL_LK_YL"
]
LIFESMART_STATE_LIST = [
    HVACMode.OFF,
    HVACMode.AUTO,
    HVACMode.FAN_ONLY,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY
]
# 空净
CLIMATE_TYPES = [
    "V_AIR_P",
    "SL_CP_DN",
    "OD_MFRESH_M8088"
]

ENTITY_ID = 'entity_id'
DOMAIN = 'lifesmart'
LIFESMART_STATE_MANAGER = 'lifesmart_wss'


def request_lifesmart(path, payload):
    """
    请求 lifesmart
    :param path: 接口地址
    :param payload: 请求内容
    :return: 响应结果
    """
    base = "https://api.ilifesmart.com/app"
    whole_url = base + path
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url=whole_url, data=payload.encode('utf-8'), headers=headers, method='POST')
    return json.loads(urllib.request.urlopen(req).read().decode('utf-8'))


def login_lifesmart(username, password, appkey):
    """
    登录 lifesmart 获取用户 token

    :param username: 用户名
    :param password: 密码
    :param appkey: 应用密钥
    :return: 登录响应结果
    """
    path = "/auth.login"
    payload = json.dumps({
        "uid": username,
        "pwd": password,
        "appkey": appkey
    })
    response = request_lifesmart(path, payload)
    if response['code'] == "success":
        return response
    else:
        return False


def auth_lifesmart(userid, token, appkey):
    """
    授权 lifesmart app

    :param userid: 用户 ID
    :param token: 用户 Token
    :param appkey: appkey
    """
    path = "/auth.do_auth"
    payload = json.dumps({
        "userid": userid,
        "token": token,
        "appkey": appkey,
        "rgn": "cn"
    })
    response = request_lifesmart(path, payload)
    if response['code'] == "success":
        return response
    else:
        return False


def get_all_devices_from_lifesmart(appkey, apptoken, usertoken, userid):
    """
    从 lifesmart获取所有设备

    :param appkey: appkey
    :param apptoken: apptoken
    :param usertoken: 用户 token
    :param userid: 用户 id
    :return: 所有设备
    """
    path = "/api.EpGetAll"
    tick = int(time.time())
    sdata = "method:EpGetAll,time:" + str(
        tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
    sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
    send_values = {
        "id": 1,
        "method": "EpGetAll",
        "system": {
            "ver": "1.0",
            "lang": "en",
            "userid": userid,
            "appkey": appkey,
            "time": tick,
            "sign": sign
        }
    }
    send_data = json.dumps(send_values)
    response = request_lifesmart(path, send_data)
    if response['code'] == 0:
        return response['message']
    return False


def send_keys_to_lifesmart(appkey, apptoken, usertoken, userid, agt, me, category, brand, ai, keys):
    """
    发送普通指令
    :param appkey: 应用 Key
    :param apptoken: 应用令牌
    :param usertoken: 用户令牌
    :param userid: 用户 ID
    :param agt: 欲操作的超级碗的 agt
    :param me: 欲操作的超级碗的 me
    :param category: 欲操作的设备的分类
    :param brand: 欲操作的设备的品牌
    :param ai: 欲操作的设备的 ID
    :param keys: 相应设备的键值
    :return: 指令返回结果
    """
    path = "/irapi.SendKeys"
    tick = int(time.time())
    # keys = str(keys)
    sdata = "method:SendKeys,agt:" + agt + ",ai:" + ai + ",brand:" + brand + ",category:" + category + ",keys:" + \
            keys + ",me:" + me + ",time:" + str(tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + \
            appkey + ",apptoken:" + apptoken
    sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
    _LOGGER.debug("sendkey: %s", str(sdata))
    send_values = {
        "id": 1,
        "method": "SendKeys",
        "params": {
            "agt": agt,
            "me": me,
            "category": category,
            "brand": brand,
            "ai": ai,
            "keys": keys
        },
        "system": {
            "ver": "1.0",
            "lang": "en",
            "userid": userid,
            "appkey": appkey,
            "time": tick,
            "sign": sign
        }
    }
    send_data = json.dumps(send_values)
    response = request_lifesmart(path, send_data)
    return response


def send_ac_keys_to_lifesmart(appkey, apptoken, usertoken, userid, agt, me, category, brand, ai, keys, power, mode,
                              temp, wind, swing):
    """
    发送空调指令
    :param appkey: 应用 Key
    :param apptoken: 应用令牌
    :param usertoken: 用户令牌
    :param userid: 用户 ID
    :param agt: 欲操作的超级碗的 agt
    :param me: 欲操作的超级碗的 me
    :param category: 欲操作的设备的分类
    :param brand: 欲操作的设备的品牌
    :param ai: 欲操作的设备的 ID
    :param keys: 相应设备的键值
    :param power: 开关
    :param mode: 运转模式
    :param temp: 温度
    :param wind: 风速
    :param swing: 风向
    :return: 指令返回结果
    """
    path = "/irapi.SendACKeys"
    tick = int(time.time())
    # keys = str(keys)
    sdata = "method:SendACKeys,agt:" + agt + ",ai:" + ai + ",brand:" + brand + ",category:" + category + ",keys:" + keys + ",me:" + me + ",mode:" + str(
        mode) + ",power:" + str(power) + ",swing:" + str(swing) + ",temp:" + str(temp) + ",wind:" + str(
        wind) + ",time:" + str(
        tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
    sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
    _LOGGER.debug("sendackey: %s", str(sdata))
    send_values = {
        "id": 1,
        "method": "SendACKeys",
        "params": {
            "agt": agt,
            "me": me,
            "category": category,
            "brand": brand,
            "ai": ai,
            "keys": keys,
            "power": power,
            "mode": mode,
            "temp": temp,
            "wind": wind,
            "swing": swing
        },
        "system": {
            "ver": "1.0",
            "lang": "en",
            "userid": userid,
            "appkey": appkey,
            "time": tick,
            "sign": sign
        }
    }
    send_data = json.dumps(send_values)
    response = request_lifesmart(path, send_data)
    return response


def setup(hass, config):
    """初始化参数"""
    param = {
        'appkey': config[DOMAIN][CONF_LIFESMART_APPKEY],
        'apptoken': config[DOMAIN][CONF_LIFESMART_APPTOKEN],
        'username': config[DOMAIN][CONF_LIFESMART_USERNAME],
        'password': config[DOMAIN][CONF_LIFESMART_PASSWORD]
    }
    login_res = login_lifesmart(param['username'], param['password'], param['appkey'])
    param['token'] = login_res['token']
    param['userid'] = login_res['userid']
    auth_res = auth_lifesmart(param['userid'], param['token'], param['appkey'])
    param['usertoken'] = auth_res['usertoken']

    """获取设备"""
    exclude_items = config[DOMAIN][CONF_EXCLUDE_ITEMS]
    devices = get_all_devices_from_lifesmart(param['appkey'], param['apptoken'], param['usertoken'], param['userid'])
    # _LOGGER.warning("lifesmart devices: %s", str(devices))
    for dev in devices:
        if dev['me'] in exclude_items:
            continue
        devtype = dev['devtype']
        dev['agt'] = dev['agt'].replace("_", "")
        if devtype in SWITCH_TYPES:
            discovery.load_platform(hass, "switch", DOMAIN, {"dev": dev, "param": param}, config)
        elif devtype in BINARY_SENSOR_TYPES:
            discovery.load_platform(hass, "binary_sensor", DOMAIN, {"dev": dev, "param": param}, config)
        elif devtype in COVER_TYPES:
            discovery.load_platform(hass, "cover", DOMAIN, {"dev": dev, "param": param}, config)
        elif devtype in SPOT_TYPES:
            discovery.load_platform(hass, "light", DOMAIN, {"dev": dev, "param": param}, config)
        elif devtype in CLIMATE_TYPES:
            discovery.load_platform(hass, "climate", DOMAIN, {"dev": dev, "param": param}, config)
        elif devtype in GAS_SENSOR_TYPES or devtype in EV_SENSOR_TYPES:
            discovery.load_platform(hass, "sensor", DOMAIN, {"dev": dev, "param": param}, config)
        if devtype in OT_SENSOR_TYPES:
            discovery.load_platform(hass, "sensor", DOMAIN, {"dev": dev, "param": param}, config)
        if devtype in LIGHT_TYPES:
            discovery.load_platform(hass, "light", DOMAIN, {"dev": dev, "param": param}, config)

    def send_keys(call):
        agt = call.data['agt']
        me = call.data['me']
        category = call.data['category']
        brand = call.data['brand']
        ai = call.data['ai']
        keys = call.data['keys']
        restkey = send_keys_to_lifesmart(param['appkey'], param['apptoken'], param['usertoken'], param['userid'], agt,
                                         me, category, brand, ai, keys)
        # _LOGGER.debug("sendkey: %s", str(restkey))

    def send_ac_keys(call):
        agt = call.data['agt']
        me = call.data['me']
        category = call.data['category']
        brand = call.data['brand']
        ai = call.data['ai']
        keys = call.data['keys']
        power = call.data['power']
        mode = call.data['mode']
        temp = call.data['temp']
        wind = call.data['wind']
        swing = call.data['swing']
        restackey = send_ac_keys_to_lifesmart(param['appkey'], param['apptoken'], param['usertoken'], param['userid'],
                                              agt, me, category, brand, ai, keys, power, mode, temp, wind, swing)
        # _LOGGER.debug("sendkey: %s", str(restackey))

    def get_fan_mode(_fanspeed):
        fanmode = None
        if _fanspeed < 30:
            fanmode = SPEED_LOW
        elif _fanspeed < 65 and _fanspeed >= 30:
            fanmode = SPEED_MEDIUM
        elif _fanspeed >= 65:
            fanmode = SPEED_HIGH
        return fanmode

    async def set_event(msg):
        if msg['msg']['idx'] != "s" and msg['msg']['me'] not in exclude_items:
            devtype = msg['msg']['devtype']
            agt = msg['msg']['agt'].replace("_", "")
            if devtype in SWITCH_TYPES and msg['msg']['idx'] in ["L1", "L2", "L3", "P1", "P2", "P3"]:
                enid = "switch." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                if msg['msg']['type'] % 2 == 1:
                    hass.states.set(enid, 'on', attrs)
                else:
                    hass.states.set(enid, 'off', attrs)
            elif devtype in BINARY_SENSOR_TYPES and msg['msg']['idx'] in ["M", "G", "B", "AXS", "P1"]:
                enid = "binary_sensor." + (
                        devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                if msg['msg']['val'] == 1:
                    hass.states.set(enid, 'on', attrs)
                else:
                    hass.states.set(enid, 'off', attrs)
            elif devtype in COVER_TYPES and msg['msg']['idx'] in ["P1", "OP"]:
                enid = "cover." + (devtype + "_" + agt + "_" + msg['msg']['me']).lower()
                attrs = dict(hass.states.get(enid).attributes)
                _LOGGER.warning("msg: %s", str(msg))
                nval = msg['msg']['val']
                ntype = msg['msg']['type']
                if nval == 0:
                    attrs['current_position'] = 0
                else:
                    attrs['current_position'] = 100

                _LOGGER.warning("websocket_cover_attrs: %s", str(attrs))
                nstat = None
                if ntype % 2 == 0 and nval == 0:
                    nstat = "closed"
                elif ntype % 2 == 1 and nval == 1:
                    nstat = "open"

                _LOGGER.warning("nstat: %s", nstat)
                hass.states.set(enid, nstat, attrs)
            elif devtype in EV_SENSOR_TYPES:
                enid = "sensor." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                hass.states.set(enid, msg['msg']['v'], attrs)
            elif devtype in GAS_SENSOR_TYPES and msg['msg']['val'] > 0:
                enid = "sensor." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                hass.states.set(enid, msg['msg']['val'], attrs)
            elif devtype in SPOT_TYPES or devtype in LIGHT_TYPES:
                enid = "light." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                if msg['msg']['type'] % 2 == 1:
                    hass.states.set(enid, 'on', attrs)
                else:
                    hass.states.set(enid, 'off', attrs)
            # elif devtype in QUANTUM_TYPES and msg['msg']['idx'] == "P1":
            #    enid = "light."+(devtype + "_" + agt + "_" + msg['msg']['me'] + "_P1").lower()
            #    attrs = hass.states.get(enid).attributes
            #    hass.states.set(enid, msg['msg']['val'], attrs)
            elif devtype in CLIMATE_TYPES:
                enid = "climate." + (devtype + "_" + agt + "_" + msg['msg']['me']).lower().replace(":", "_").replace(
                    "@", "_")
                _idx = msg['msg']['idx']
                attrs = dict(hass.states.get(enid).attributes)
                nstat = hass.states.get(enid).state
                if _idx == "O":
                    if msg['msg']['type'] % 2 == 1:
                        nstat = attrs['last_mode']
                        hass.states.set(enid, nstat, attrs)
                    else:
                        nstat = HVACMode.OFF
                        hass.states.set(enid, nstat, attrs)
                if _idx == "P1":
                    if msg['msg']['type'] % 2 == 1:
                        nstat = HVACMode.HEAT
                        hass.states.set(enid, nstat, attrs)
                    else:
                        nstat = HVACMode.OFF
                        hass.states.set(enid, nstat, attrs)
                if _idx == "P2":
                    if msg['msg']['type'] % 2 == 1:
                        attrs['Heating'] = "true"
                        hass.states.set(enid, nstat, attrs)
                    else:
                        attrs['Heating'] = "false"
                        hass.states.set(enid, nstat, attrs)
                elif _idx == "MODE":
                    if msg['msg']['type'] == 206:
                        if nstat != HVACMode.OFF:
                            nstat = LIFESMART_STATE_LIST[msg['msg']['val']]
                        attrs['last_mode'] = nstat
                        hass.states.set(enid, nstat, attrs)
                elif _idx == "F":
                    if msg['msg']['type'] == 206:
                        attrs['fan_mode'] = get_fan_mode(msg['msg']['val'])
                        hass.states.set(enid, nstat, attrs)
                elif _idx == "tT" or _idx == "P3":
                    if msg['msg']['type'] == 136:
                        attrs['temperature'] = msg['msg']['v']
                        hass.states.set(enid, nstat, attrs)
                elif _idx == "T" or _idx == "P4":
                    if msg['msg']['type'] == 8 or msg['msg']['type'] == 9:
                        attrs['current_temperature'] = msg['msg']['v']
                        hass.states.set(enid, nstat, attrs)
            elif devtype in LOCK_TYPES:
                if msg['msg']['idx'] == "BAT":
                    enid = "sensor." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                    attrs = hass.states.get(enid).attributes
                    hass.states.set(enid, msg['msg']['val'], attrs)
                elif msg['msg']['idx'] == "EVTLO":
                    enid = "binary_sensor." + (
                            devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                    val = msg['msg']['val']
                    ulk_way = val >> 12
                    ulk_user = val & 0xfff
                    ulk_success = True
                    if ulk_user == 0:
                        ulk_success = False
                    attrs = {"unlocking_way": ulk_way, "unlocking_user": ulk_user, "devtype": devtype,
                             "unlocking_success": ulk_success,
                             "last_time": datetime.datetime.fromtimestamp(msg['msg']['ts'] / 1000).strftime(
                                 "%Y-%m-%d %H:%M:%S")}
                    if msg['msg']['type'] % 2 == 1:
                        hass.states.set(enid, 'on', attrs)
                    else:
                        hass.states.set(enid, 'off', attrs)
            if devtype in OT_SENSOR_TYPES and msg['msg']['idx'] in ["Z", "V", "P3", "P4"]:
                enid = "sensor." + (devtype + "_" + agt + "_" + msg['msg']['me'] + "_" + msg['msg']['idx']).lower()
                attrs = hass.states.get(enid).attributes
                hass.states.set(enid, msg['msg']['v'], attrs)

    def on_message(ws, message):
        _LOGGER.warning("websocket_msg: %s", str(message))
        msg = json.loads(message)
        if 'type' not in msg:
            return
        if msg['type'] != "io":
            return
        asyncio.run(set_event(msg))

    def on_error(ws, error):
        _LOGGER.debug("websocket_error: %s", str(error))

    def on_close(ws):
        _LOGGER.debug("lifesmart websocket closed...")

    def on_open(ws):
        tick = int(time.time())
        sdata = "method:WbAuth,time:" + str(tick) + ",userid:" + param['userid'] + ",usertoken:" + param[
            'usertoken'] + ",appkey:" + param['appkey'] + ",apptoken:" + param['apptoken']
        sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
        send_values = {
            "id": 1,
            "method": "WbAuth",
            "system": {
                "ver": "1.0",
                "lang": "en",
                "userid": param['userid'],
                "appkey": param['appkey'],
                "time": tick,
                "sign": sign
            }
        }
        header = {'Content-Type': 'application/json'}
        send_data = json.dumps(send_values)
        ws.send(send_data)
        _LOGGER.debug("lifesmart websocket sending_data...")

    hass.services.register(DOMAIN, 'send_keys', send_keys)
    hass.services.register(DOMAIN, 'send_ackeys', send_ac_keys)
    ws = websocket.WebSocketApp("wss://api.ilifesmart.com:8443/wsapp/",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    hass.data[LIFESMART_STATE_MANAGER] = LifeSmartStatesManager(ws=ws)
    hass.data[LIFESMART_STATE_MANAGER].start_keep_alive()
    return True


class LifeSmartDevice(Entity):
    """LifeSmart base device."""

    def __init__(self, dev, idx, val, param):
        """Initialize the switch."""
        self._name = dev['name'] + "_" + idx
        self._appkey = param['appkey']
        self._apptoken = param['apptoken']
        self._usertoken = param['usertoken']
        self._userid = param['userid']
        self._agt = dev['agt']
        self._me = dev['me']
        self._idx = idx
        self._devtype = dev['devtype']
        attrs = {"agt": self._agt, "me": self._me, "idx": self._idx, "devtype": self._devtype}
        self._attributes = attrs

    @property
    def object_id(self):
        """Return LifeSmart device id."""
        return self.entity_id

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def name(self):
        """Return LifeSmart device name."""
        return self._name

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return False

    @property
    def should_poll(self):
        """check with the entity for an updated state."""
        return False

    @staticmethod
    def _lifesmart_epset(self, type, val, idx):
        # self._tick = int(time.time())
        url = "https://api.ilifesmart.com/app/api.EpSet"
        tick = int(time.time())
        appkey = self._appkey
        apptoken = self._apptoken
        userid = self._userid
        usertoken = self._usertoken
        agt = self._agt
        me = self._me
        sdata = "method:EpSet,agt:" + agt + ",idx:" + idx + ",me:" + me + ",type:" + type + ",val:" + str(
            val) + ",time:" + str(
            tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
        sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
        send_values = {
            "id": 1,
            "method": "EpSet",
            "system": {
                "ver": "1.0",
                "lang": "en",
                "userid": userid,
                "appkey": appkey,
                "time": tick,
                "sign": sign
            },
            "params": {
                "agt": agt,
                "me": me,
                "idx": idx,
                "type": type,
                "val": val
            }
        }
        header = {'Content-Type': 'application/json'}
        send_data = json.dumps(send_values)
        req = urllib.request.Request(url=url, data=send_data.encode('utf-8'), headers=header, method='POST')
        response = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        _LOGGER.info("epset_send: %s", str(send_data))
        _LOGGER.info("epset_res: %s", str(response))
        return response['code']

    @staticmethod
    def _lifesmart_epget(self):
        url = "https://api.ilifesmart.com/app/api.EpGet"
        tick = int(time.time())
        appkey = self._appkey
        apptoken = self._apptoken
        userid = self._userid
        usertoken = self._usertoken
        agt = self._agt
        me = self._me
        sdata = "method:EpGet,agt:" + agt + ",me:" + me + ",time:" + str(
            tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
        sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
        send_values = {
            "id": 1,
            "method": "EpGet",
            "system": {
                "ver": "1.0",
                "lang": "en",
                "userid": userid,
                "appkey": appkey,
                "time": tick,
                "sign": sign
            },
            "params": {
                "agt": agt,
                "me": me
            }
        }
        header = {'Content-Type': 'application/json'}
        send_data = json.dumps(send_values)
        req = urllib.request.Request(url=url, data=send_data.encode('utf-8'), headers=header, method='POST')
        response = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        return response['message']['data']


class LifeSmartStatesManager(threading.Thread):

    def __init__(self, ws):
        """Init LifeSmart Update Manager."""
        threading.Thread.__init__(self)
        self._run = False
        self._lock = threading.Lock()
        self._ws = ws

    def run(self):
        while self._run:
            _LOGGER.debug('lifesmart: starting wss...')
            self._ws.run_forever()
            _LOGGER.debug('lifesmart: restart wss...')
            time.sleep(10)

    def start_keep_alive(self):
        """Start keep alive mechanism."""
        with self._lock:
            self._run = True
            threading.Thread.start(self)

    def stop_keep_alive(self):
        """Stop keep alive mechanism."""
        with self._lock:
            self._run = False
            self.join()
