import logging

from homeassistant.components.sensor import (
    SensorEntity,
    ENTITY_ID_FORMAT,
)
from homeassistant.const import UnitOfTemperature

from . import (
    DOMAIN,
    DEVICES,
    BINARY_SENSOR_TYPES,
    GAS_SENSOR_TYPES,
    OT_SENSOR_TYPES,
    LifeSmartDevice
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """通过配置入口设置传感器平台"""
    param = hass.data[DOMAIN][config_entry.entry_id]
    exclude_items = param["exclude"]

    # 从 Lifesmart 获取设备列表
    devices = hass.data[DOMAIN][DEVICES]

    # 过滤设备并创建实体
    sensors = []
    for dev in devices:
        if dev["me"] in exclude_items:
            continue
        devtype = dev["devtype"]
        if devtype in BINARY_SENSOR_TYPES:
            for idx in dev["data"]:
                if dev['devtype'] in OT_SENSOR_TYPES and idx in ["Z", "V", "P3", "P4"]:
                    sensors.append(LifeSmartSensor(dev, idx, dev['data'][idx], param))
                else:
                    sensors.append(LifeSmartSensor(dev, idx, dev['data'][idx], param))

    async_add_entities(sensors, True)


class LifeSmartSensor(LifeSmartDevice, SensorEntity):
    """LifeSmart传感器实体"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self.entity_id = ENTITY_ID_FORMAT.format(
            (dev['devtype'] + "_" + dev['agt'] + "_" + dev['me'] + "_" + idx).lower())
        self._attr_unique_id = self.entity_id
        devtype = dev['devtype']
        if devtype in GAS_SENSOR_TYPES:
            self._unit = "None"
            self._device_class = "None"
            self._state = val['val']
        else:
            if idx == "T" or idx == "P1":
                self._device_class = "temperature"
                self._unit = UnitOfTemperature.CELSIUS
            elif idx == "H" or idx == "P2":
                self._device_class = "humidity"
                self._unit = "%"
            elif idx == "Z":
                self._device_class = "illuminance"
                self._unit = "lx"
            elif idx == "V":
                self._device_class = "battery"
                self._unit = "%"
            elif idx == "P3":
                self._device_class = "None"
                self._unit = "ppm"
            elif idx == "P4":
                self._device_class = "None"
                self._unit = "mg/m3"
            else:
                self._unit = "None"
                self._device_class = "None"
            self._state = val['v']

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

    @property
    def state(self):
        return self._state
