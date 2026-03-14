"""配置模块 - 类型定义

此模块仅用于类型提示，实际的配置类定义在 plugin.py 中的 MusicPluginConfig。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 仅在类型检查时导入，避免循环导入
    try:
        from ..plugin import MusicPluginConfig as PluginConfig
    except ImportError:
        class PluginConfig:  # type: ignore
            """类型占位"""
            pass
else:
    # 运行时创建一个简单的占位类
    class PluginConfig:
        """运行时占位配置类
        
        实际的配置实例是 plugin.py 中的 MusicPluginConfig 类。
        如果直接使用此类会抛出 RuntimeError。
        """
        def __init__(self, *args, **kwargs):
            raise RuntimeError("请使用 plugin.py 中的 MusicPluginConfig 类")
