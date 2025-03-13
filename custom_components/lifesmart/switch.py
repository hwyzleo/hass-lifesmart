import logging

from homeassistant.components.switch import (
    SwitchEntity,
    ENTITY_ID_FORMAT,
)

from . import (
    DOMAIN,
    DEVICES,
    SWITCH_TYPES,
    LifeSmartDevice
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """通过配置入口设置开关平台"""
    param = hass.data[DOMAIN][config_entry.entry_id]
    exclude_items = param["exclude"]

    # 从 Lifesmart 获取设备列表
    devices = hass.data[DOMAIN][DEVICES]

    # 过滤设备并创建实体
    switches = []
    for dev in devices:
        if dev["me"] in exclude_items:
            continue
        devtype = dev["devtype"]
        if devtype in SWITCH_TYPES:
            for idx in dev["data"]:
                if idx in ["L1", "L2", "L3", "P1", "P2", "P3"]:
                    switches.append(LifeSmartSwitch(dev, idx, dev["data"][idx], param))

    async_add_entities(switches, True)


class LifeSmartSwitch(LifeSmartDevice, SwitchEntity):
    """LifeSmart开关实体"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self.entity_id = ENTITY_ID_FORMAT.format(
            (dev['devtype'] + "_" + dev['agt'] + "_" + dev['me'] + "_" + idx).lower())
        self._attr_unique_id = self.entity_id
        if val['type'] % 2 == 1:
            self._state = True
        else:
            self._state = False

    @property
    def is_on(self):
        return self._state

    async def async_added_to_hass(self):
        """添加实体时触发"""

    def _get_state(self):
        return self._state

    def turn_on(self, **kwargs):
        if super()._lifesmart_epset(self, "0x81", 1, self._idx) == 0:
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        if super()._lifesmart_epset(self, "0x80", 0, self._idx) == 0:
            self._state = False
            self.schedule_update_ha_state()
