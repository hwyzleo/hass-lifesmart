from homeassistant.components.cover import (
    ENTITY_ID_FORMAT,
    ATTR_POSITION,
    CoverEntity,
)

from . import LifeSmartDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """
    安装窗帘设备
    :param hass:
    :param config:
    :param add_entities:
    :param discovery_info:
    :return:
    """
    if discovery_info is None:
        return
    dev = discovery_info.get("dev")
    param = discovery_info.get("param")
    devices = []
    if dev["devtype"] == "SL_SW_WIN":
        idx = "OP"
    else:
        idx = "P1"
    devices.append(LifeSmartCover(dev, idx, dev['data'][idx], param))
    add_entities(devices)


class LifeSmartCover(LifeSmartDevice, CoverEntity):
    """LifeSmart 窗帘设备"""

    def __init__(self, dev, idx, val, param):
        super().__init__(dev, idx, val, param)
        self._name = dev['name']
        self.entity_id = ENTITY_ID_FORMAT.format((dev['devtype'] + "_" + dev['agt'] + "_" + dev['me']).lower())
        self._pos = val['val']
        self._device_class = "curtain"
        self._devtype = dev["devtype"]

    @property
    def current_cover_position(self):
        return self._pos

    @property
    def is_closed(self):
        return self.current_cover_position <= 0

    def close_cover(self, **kwargs):
        """关闭窗帘"""
        if self._devtype == "SL_SW_WIN":
            idx = "CL"
        else:
            idx = "P3"
        super()._lifesmart_epset(self, "0x81", 1, idx)

    def open_cover(self, **kwargs):
        """打开窗帘"""
        if self._devtype == "SL_SW_WIN":
            idx = "OP"
        else:
            idx = "P1"
        super()._lifesmart_epset(self, "0x81", 1, idx)

    def stop_cover(self, **kwargs):
        """停止窗帘"""
        if self._devtype == "SL_SW_WIN":
            idx = "ST"
        else:
            idx = "P2"
        super()._lifesmart_epset(self, "0x81", 1, idx)

    def set_cover_position(self, **kwargs):
        """设置窗帘在指定位置"""
        position = kwargs.get(ATTR_POSITION)
        super()._lifesmart_epset(self, "0xCE", position, "P2")

    @property
    def device_class(self):
        return self._device_class
