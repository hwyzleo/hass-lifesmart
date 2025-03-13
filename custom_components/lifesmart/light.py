import binascii
import hashlib
import json
import logging
import struct
import time
import urllib.request

import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    ENTITY_ID_FORMAT,
    LightEntityFeature,
)

from . import (
    DOMAIN,
    DEVICES,
    LIGHT_TYPES,
    SPOT_TYPES,
    LifeSmartDevice
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """通过配置入口设置灯平台"""
    param = hass.data[DOMAIN][config_entry.entry_id]
    exclude_items = param["exclude"]

    # 从 Lifesmart 获取设备列表
    devices = hass.data[DOMAIN][DEVICES]

    # 过滤设备并创建实体
    lights = []
    for dev in devices:
        if dev["me"] in exclude_items:
            continue
        devtype = dev["devtype"]
        if devtype in LIGHT_TYPES:
            for idx in dev["data"]:
                if idx in ["RGB", "RGBW", "dark", "dark1", "dark2", "dark3", "bright", "bright1", "bright2", "bright"]:
                    lights.append(LifeSmartLight(dev, idx, dev["data"][idx], param))

    async_add_entities(lights, True)


class LifeSmartLight(LifeSmartDevice, LightEntity):
    """LifeSmart灯实体"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self._attr_supported_features = LightEntityFeature.EFFECT
        self.entity_id = ENTITY_ID_FORMAT.format(
            (dev['devtype'] + "_" + dev['agt'] + "_" + dev['me'] + "_" + idx).lower())
        self._attr_unique_id = self.entity_id
        if val['type'] % 2 == 1:
            self._state = True
        else:
            self._state = False
        value = val['val']
        if value == 0:
            self._hs = None
        else:
            rgbhexstr = "%x" % value
            rgbhexstr = rgbhexstr.zfill(8)
            rgbhex = bytes.fromhex(rgbhexstr)
            rgba = struct.unpack("BBBB", rgbhex)
            rgb = rgba[1:]
            self._hs = color_util.color_RGB_to_hs(*rgb)
            _LOGGER.info("hs_rgb: %s", str(self._hs))

    @property
    def supported_color_modes(self):
        return {ColorMode.HS}

    @property
    def color_mode(self):
        return ColorMode.HS

    async def async_added_to_hass(self):
        if self._devtype not in SPOT_TYPES:
            return
        rmdata = {}
        rmlist = LifeSmartLight._lifesmart_GetRemoteList(self)
        for ai in rmlist:
            rms = LifeSmartLight._lifesmart_GetRemotes(self, ai)
            rms['category'] = rmlist[ai]['category']
            rms['brand'] = rmlist[ai]['brand']
            rmdata[ai] = rms
        self._attributes.setdefault('remotelist', rmdata)

    @property
    def is_on(self):
        return self._state

    @property
    def hs_color(self):
        return self._hs

    def turn_on(self, **kwargs):
        if ATTR_HS_COLOR in kwargs:
            self._hs = kwargs[ATTR_HS_COLOR]

        rgb = color_util.color_hs_to_RGB(*self._hs)
        rgba = (0,) + rgb
        rgbhex = binascii.hexlify(struct.pack("BBBB", *rgba)).decode("ASCII")
        rgbhex = int(rgbhex, 16)

        if super()._lifesmart_epset(self, "0xff", rgbhex, self._idx) == 0:
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        if super()._lifesmart_epset(self, "0x80", 0, self._idx) == 0:
            self._state = False
            self.schedule_update_ha_state()

    @staticmethod
    def _lifesmart_GetRemoteList(self):
        appkey = self._appkey
        apptoken = self._apptoken
        usertoken = self._usertoken
        userid = self._userid
        agt = self._agt
        url = "https://api.ilifesmart.com/app/irapi.GetRemoteList"
        tick = int(time.time())
        sdata = "method:GetRemoteList,agt:" + agt + ",time:" + str(
            tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
        sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
        send_values = {
            "id": 1,
            "method": "GetRemoteList",
            "params": {
                "agt": agt
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
        header = {'Content-Type': 'application/json'}
        send_data = json.dumps(send_values)
        req = urllib.request.Request(url=url, data=send_data.encode('utf-8'), headers=header, method='POST')
        response = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        return response['message']

    @staticmethod
    def _lifesmart_GetRemotes(self, ai):
        appkey = self._appkey
        apptoken = self._apptoken
        usertoken = self._usertoken
        userid = self._userid
        agt = self._agt
        url = "https://api.ilifesmart.com/app/irapi.GetRemote"
        tick = int(time.time())
        sdata = "method:GetRemote,agt:" + agt + ",ai:" + ai + ",needKeys:2,time:" + str(
            tick) + ",userid:" + userid + ",usertoken:" + usertoken + ",appkey:" + appkey + ",apptoken:" + apptoken
        sign = hashlib.md5(sdata.encode(encoding='UTF-8')).hexdigest()
        send_values = {
            "id": 1,
            "method": "GetRemote",
            "params": {
                "agt": agt,
                "ai": ai,
                "needKeys": 2
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
        header = {'Content-Type': 'application/json'}
        send_data = json.dumps(send_values)
        req = urllib.request.Request(url=url, data=send_data.encode('utf-8'), headers=header, method='POST')
        response = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        return response['message']['codes']
