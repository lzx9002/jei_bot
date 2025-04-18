from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config
from ..ban_advertisement import ban_advertisement

__plugin_meta__ = PluginMetadata(
    name="ban_advertisement",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

