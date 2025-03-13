import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    ENTITY_ID_FORMAT,
)

from . import (
    DOMAIN,
    DEVICES,
    BINARY_SENSOR_TYPES,
    GUARD_SENSOR_TYPES,
    MOTION_SENSOR_TYPES,
    LifeSmartDevice
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """通过配置入口设置二进制传感器平台"""
    param = hass.data[DOMAIN][config_entry.entry_id]
    exclude_items = param["exclude"]

    # 从 Lifesmart 获取设备列表
    devices = hass.data[DOMAIN][DEVICES]

    # 过滤设备并创建实体
    binary_sensors = []
    for dev in devices:
        if dev["me"] in exclude_items:
            continue
        devtype = dev["devtype"]
        if devtype in BINARY_SENSOR_TYPES:
            for idx in dev['data']:
                if idx in ["M", "G", "B", "AXS", "P1"]:
                    binary_sensors.append(LifeSmartBinarySensor(dev, idx, dev['data'][idx], param))

    async_add_entities(binary_sensors, True)


class LifeSmartBinarySensor(LifeSmartDevice, BinarySensorEntity):
    """LifeSmart二进制传感器实体"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self.entity_id = ENTITY_ID_FORMAT.format(
            (dev['devtype'] + "_" + dev['agt'] + "_" + dev['me'] + "_" + idx).lower())
        self._attr_unique_id = self.entity_id
        devtype = dev['devtype']
        if devtype in GUARD_SENSOR_TYPES:
            self._device_class = "door"
        elif devtype in MOTION_SENSOR_TYPES:
            self._device_class = "motion"
        else:
            self._device_class = "smoke"
        if (val['val'] == 1 and self._device_class != "door") or (val['val'] == 0 and self._device_class == "door"):
            self._state = True
        else:
            self._state = False

    @property
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        return self._device_class
