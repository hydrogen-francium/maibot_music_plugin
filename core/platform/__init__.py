"""音乐平台模块"""
from .base import BaseMusicPlayer

# 确保基类先加载，再加载子类以触发 __init_subclass__
from .ncm import NetEaseMusic
from .ncm_nodejs import NetEaseMusicNodeJS
from .txqq import TXQQMusic

__all__ = ["NetEaseMusic", "NetEaseMusicNodeJS", "BaseMusicPlayer", "TXQQMusic"]
