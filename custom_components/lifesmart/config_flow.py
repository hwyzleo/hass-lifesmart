import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from . import (
    DOMAIN,
    CONF_LIFESMART_USERNAME,
    CONF_LIFESMART_PASSWORD,
    CONF_LIFESMART_APPKEY,
    CONF_LIFESMART_APPTOKEN,
    CONF_EXCLUDE_ITEMS,
    login_lifesmart,
    auth_lifesmart,
)

_LOGGER = logging.getLogger(__name__)


class LifeSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理配置流的类"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """用户通过 UI 添加集成时的处理"""
        errors = {}
        if user_input is not None:
            # 验证用户输入
            login_res = await self.hass.async_add_executor_job(
                login_lifesmart,
                user_input[CONF_LIFESMART_USERNAME],
                user_input[CONF_LIFESMART_PASSWORD],
                user_input[CONF_LIFESMART_APPKEY],
            )
            if not login_res or login_res.get("code") != "success":
                errors["base"] = "invalid_auth"
            else:
                # 验证通过，创建配置入口
                return self.async_create_entry(
                    title=f"LifeSmart ({user_input[CONF_LIFESMART_USERNAME]})",
                    data=user_input,
                )

        # 显示配置表单
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_LIFESMART_USERNAME): str,
                vol.Required(CONF_LIFESMART_PASSWORD): str,
                vol.Required(CONF_LIFESMART_APPKEY): str,
                vol.Required(CONF_LIFESMART_APPTOKEN): str,
                vol.Optional(CONF_EXCLUDE_ITEMS, default=[]): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """选项流（用于更新配置）"""
        return LifeSmartOptionsFlow()


class LifeSmartOptionsFlow(config_entries.OptionsFlow):
    """处理配置选项更新"""

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # 验证用户输入
            if await self._validate_credentials(user_input["username"], user_input["password"]):
                # 直接返回配置数据，无需设置 config_entry
                return self.async_create_entry(
                    title=user_input["username"],
                    data=user_input
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("appkey"): str,
                vol.Required("apptoken"): str,
            }),
            errors=errors
        )

    @staticmethod
    async def _validate_credentials(username, password):
        # 验证逻辑（如调用 API）
        return True  # 示例
