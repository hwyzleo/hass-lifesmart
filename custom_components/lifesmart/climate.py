import logging
import time

from homeassistant.components.climate import ENTITY_ID_FORMAT, ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
)
from homeassistant.const import (
    PRECISION_WHOLE,
    TEMP_CELSIUS,
)

from . import (
    DOMAIN,
    DEVICES,
    CLIMATE_TYPES,
    LifeSmartDevice
)

_LOGGER = logging.getLogger(__name__)

SPEED_OFF = "Speed_Off"
SPEED_LOW = "Speed_Low"
SPEED_MEDIUM = "Speed_Medium"
SPEED_HIGH = "Speed_High"
DEVICE_TYPE = "climate"
LIFESMART_STATE_LIST = [
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY
]
LIFESMART_STATE_LIST2 = [
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT
]
FAN_MODES = [
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH
]
GET_FAN_SPEED = {
    SPEED_LOW: 15,
    SPEED_MEDIUM: 45,
    SPEED_HIGH: 76
}

AIR_TYPES = ["V_AIR_P"]

THER_TYPES = ["SL_CP_DN"]

LIFESMART_STATE_LIST = []


async def async_setup_entry(hass, config_entry, async_add_entities):
    """通过配置入口设置空调平台"""
    param = hass.data[DOMAIN][config_entry.entry_id]
    exclude_items = param["exclude"]

    # 从 Lifesmart 获取设备列表
    devices = hass.data[DOMAIN][DEVICES]

    # 过滤设备并创建实体
    climates = []
    for dev in devices:
        if dev["me"] in exclude_items:
            continue
        devtype = dev["devtype"]
        if devtype in CLIMATE_TYPES:
            if "T" not in dev['data'] and "P3" not in dev['data']:
                continue
            devices.append(LifeSmartClimate(dev, "idx", "0", param))

    async_add_entities(climates, True)


class LifeSmartClimate(LifeSmartDevice, ClimateEntity):
    """LifeSmart空净实体"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self._name = dev['name']
        cdata = dev['data']
        self.entity_id = ENTITY_ID_FORMAT.format(
            (dev['devtype'] + "_" + dev['agt'] + "_" + dev['me']).lower().replace(":", "_").replace("@", "_"))
        self._attr_unique_id = self.entity_id
        if dev['devtype'] in AIR_TYPES:
            self._modes = LIFESMART_STATE_LIST
            if cdata['O']['type'] % 2 == 0:
                self._mode = LIFESMART_STATE_LIST[0]
            else:
                self._mode = LIFESMART_STATE_LIST[cdata['MODE']['val']]
            self._attributes.update({"last_mode": LIFESMART_STATE_LIST[cdata['MODE']['val']]})
            self._current_temperature = cdata['T']['v']
            self._target_temperature = cdata['tT']['v']
            self._min_temp = 10
            self._max_temp = 35
            self._fanspeed = cdata['F']['val']
        else:
            self._modes = LIFESMART_STATE_LIST2
            if cdata['P1']['type'] % 2 == 0:
                self._mode = LIFESMART_STATE_LIST2[0]
            else:
                self._mode = LIFESMART_STATE_LIST2[1]
            if cdata['P2']['type'] % 2 == 0:
                self._attributes.setdefault('Heating', "false")
            else:
                self._attributes.setdefault('Heating', "true")
            self._current_temperature = cdata['P4']['val'] / 10
            self._target_temperature = cdata['P3']['val'] / 10
            self._min_temp = 5
            self._max_temp = 35

    @property
    def precision(self):
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        return self._mode

    @property
    def hvac_modes(self):
        return self._modes

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def target_temperature_step(self):
        return 1

    @property
    def fan_mode(self):
        fanmode = None
        if self._fanspeed < 30:
            fanmode = SPEED_LOW
        elif self._fanspeed < 65 and self._fanspeed >= 30:
            fanmode = SPEED_MEDIUM
        elif self._fanspeed >= 65:
            fanmode = SPEED_HIGH
        return fanmode

    @property
    def fan_modes(self):
        return FAN_MODES

    def set_temperature(self, **kwargs):
        new_temp = int(kwargs['temperature'] * 10)
        _LOGGER.info("set_temperature: %s", str(new_temp))
        if self._devtype in AIR_TYPES:
            super()._lifesmart_epset(self, "0x88", new_temp, "tT")
        else:
            super()._lifesmart_epset(self, "0x88", new_temp, "P3")

    def set_fan_mode(self, fan_mode):
        super()._lifesmart_epset(self, "0xCE", GET_FAN_SPEED[fan_mode], "F")

    def set_hvac_mode(self, hvac_mode):
        if self._devtype in AIR_TYPES:
            if hvac_mode == HVAC_MODE_OFF:
                super()._lifesmart_epset(self, "0x80", 0, "O")
                return
            if self._mode == HVAC_MODE_OFF:
                if super()._lifesmart_epset(self, "0x81", 1, "O") == 0:
                    time.sleep(2)
                else:
                    return
            super()._lifesmart_epset(self, "0xCE", LIFESMART_STATE_LIST.index(hvac_mode), "MODE")
        else:
            if hvac_mode == HVAC_MODE_OFF:
                super()._lifesmart_epset(self, "0x80", 0, "P1")
                time.sleep(1)
                super()._lifesmart_epset(self, "0x80", 0, "P2")
                return
            else:
                if super()._lifesmart_epset(self, "0x81", 1, "P1") == 0:
                    time.sleep(2)
                else:
                    return

    @property
    def supported_features(self):
        if self._devtype in AIR_TYPES:
            return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
        else:
            return SUPPORT_TARGET_TEMPERATURE

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp
