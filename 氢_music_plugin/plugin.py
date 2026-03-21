"""
MaiBot 点歌插件 (轻量版)

轻量化的点歌插件，支持多音源点歌。

核心功能:
- 多音源支持: 网易云音乐、QQ音乐、酷狗、酷我等
- 点歌命令: 支持关键词点歌、平台指定点歌
- 序号选择: 搜索后通过序号快速选择歌曲
- 查歌词: 搜索并显示歌曲歌词
- 多种发送模式: 音乐卡片、语音、文件、文本

作者: 氢
版本: 2.1.0
"""

import asyncio
import traceback
from pathlib import Path
from typing import List, Tuple, Type, Optional, Dict, Any

from src.plugin_system import (
    BasePlugin, register_plugin, 
    BaseCommand, ConfigField,
    ComponentInfo
)
from src.plugin_system.apis import logging_api

from .core.downloader import Downloader
from .core.model import Song
from .core.platform import BaseMusicPlayer, NetEaseMusic, NetEaseMusicNodeJS, TXQQMusic
from .core.renderer import MusicRenderer
from .core.sender import MusicSender

# 获取日志器
logger = logging_api.get_logger("music_plugin")

# 全局插件实例引用
_plugin_instance: Optional["MusicPlugin"] = None

def get_plugin() -> Optional["MusicPlugin"]:
    """获取插件实例"""
    return _plugin_instance


class MusicPluginConfig:
    """插件配置类 - 使用 BasePlugin.get_config 方法读取配置"""
    
    def __init__(self, plugin: BasePlugin):
        """传入插件实例，使用其 get_config 方法读取配置"""
        try:
            self._plugin = plugin
            logger.debug("开始加载插件配置...")
            
            # 通用配置 [general]
            self.default_player_name: str = plugin.get_config("general.default_player_name", "网易点歌")
            self.song_limit: int = plugin.get_config("general.song_limit", 5)
            self.select_mode: str = plugin.get_config("general.select_mode", "text(文本模式)")
            self.timeout: int = plugin.get_config("general.timeout", 30)
            
            # 发送配置 [send]
            self.send_modes: List[str] = plugin.get_config("send.send_modes", [
                "card(卡片模式)",
                "record(语音模式)",
                "file(文件模式)",
                "text(文本模式)"
            ])
            self.enable_comments: bool = plugin.get_config("send.enable_comments", True)
            self.enable_lyrics: bool = plugin.get_config("send.enable_lyrics", False)
            
            # 网络配置 [network]
            self.proxy: str = plugin.get_config("network.proxy", "")
            self.nodejs_base_url: str = plugin.get_config("network.nodejs_base_url", "https://163api.qijieya.cn")
            
            # 缓存配置 [cache]
            self.clear_cache: bool = plugin.get_config("cache.clear_cache", True)
            
            # API密钥 [api_keys]
            self.enc_sec_key: str = plugin.get_config("api_keys.enc_sec_key", 
                "45c8bcb07e69c6b545d3045559bd300db897509b8720ee2b45a72bf2d3b216ddc77fb10daec4ca54b466f2da1ffac1e67e245fea9d842589dc402b92b262d3495b12165a721aed880bf09a0a99ff94c959d04e49085dc21c78bbbe8e3331827c0ef0035519e89f097511065643120cbc478f9c0af96400ba4649265781fc9079")
            self.enc_params: str = plugin.get_config("api_keys.enc_params", 
                "D33zyir4L/58v1qGPcIPjSee79KCzxBIBy507IYDB8EL7jEnp41aDIqpHBhowfQ6iT1Xoka8jD+0p44nRKNKUA0dv+n5RWPOO57dZLVrd+T1J/sNrTdzUhdHhoKRIgegVcXYjYu+CshdtCBe6WEJozBRlaHyLeJtGrABfMOEb4PqgI3h/uELC82S05NtewlbLZ3TOR/TIIhNV6hVTtqHDVHjkekrvEmJzT5pk1UY6r0=")
            
            # 初始化路径
            self.data_dir = Path("data/plugins/music_plugin")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.songs_dir = self.data_dir / "songs"
            self.songs_dir.mkdir(parents=True, exist_ok=True)
            self.font_path = Path(__file__).parent / "fonts" / "simhei.ttf"
            
            self._send_modes = [m.split("(", 1)[0].strip() for m in self.send_modes]
            logger.debug("配置加载完成")
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            logger.error(traceback.format_exc())
            raise
    
    @property
    def http_proxy(self) -> Optional[str]:
        return self.proxy if self.proxy else None
    
    @property
    def real_send_modes(self) -> List[str]:
        return self._send_modes
    
    @property
    def real_song_limit(self) -> int:
        return 1 if "single" in self.select_mode else self.song_limit


# ===== 工具组件：AI点歌 =====

# ===== Command组件：点歌 =====

class MusicCommand(BaseCommand):
    """点歌命令 - 支持多种点歌方式"""
    
    command_name = "music"
    command_description = "点歌命令，支持网易云、QQ音乐、酷狗等多个平台"
    command_pattern = r"^(?P<platform>网易云?|网易点歌|QQ点歌|qq点歌|酷狗点歌|酷我点歌|百度点歌|一听点歌|咪咕点歌|荔枝点歌|蜻蜓点歌|喜马拉雅|5sing原创|5sing翻唱|全民K歌|点歌)\s*(?P<song>.+)?$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行点歌命令"""
        try:
            # 获取插件实例
            plugin = get_plugin()
            if not plugin:
                await self.send_text("插件未初始化")
                return True, "插件未初始化", True
            
            # 获取匹配参数
            platform_cmd = self.matched_groups.get("platform", "")
            song_arg = self.matched_groups.get("song", "")
            
            if not song_arg:
                await self.send_text("请输入要搜索的歌曲名称\n用法：点歌 <歌名> [序号]\n例如：点歌 稻香 或 点歌 稻香 1")
                return True, "未提供歌曲名称", True
            
            # 解析参数（歌名和序号）
            args = song_arg.split()
            index: int = int(args[-1]) if args[-1].isdigit() else 0
            song_name = song_arg.removesuffix(str(index)).strip() if index else song_arg
            
            if not song_name:
                await self.send_text("未指定歌名")
                return True, "未指定歌名", True
            
            # 获取播放器
            logger.debug(f"获取播放器: cmd={platform_cmd}, default={platform_cmd in ['点歌']}")
            logger.debug(f"可用播放器: {len(plugin.players)} 个, 关键词: {plugin.keywords}")
            player = None
            if platform_cmd in ["点歌"]:
                player = plugin.get_player(default=True)
            else:
                player = plugin.get_player(word=platform_cmd)
            
            if not player:
                await self.send_text(f"未找到对应的音乐平台。已注册平台: {plugin.keywords}")
                return True, "未找到播放器", True
            
            # 搜索歌曲
            logger.debug(f"正在通过{player.platform.display_name}搜索歌曲：{song_name}")
            songs = await player.fetch_songs(
                keyword=song_name, 
                limit=plugin.cfg.real_song_limit
            )
            
            if not songs:
                await self.send_text(f"搜索【{song_name}】无结果")
                return True, "搜索无结果", True
            
            # 单曲模式或指定序号直接发送
            if len(songs) == 1 or (index and 1 <= index <= len(songs)):
                selected_song = songs[int(index) - 1] if index else songs[0]
                await plugin.sender.send_song_command(self, player, selected_song)
                return True, f"发送歌曲: {selected_song.name}", True
            
            # 显示歌曲列表供选择
            title = f"【{player.platform.display_name}】"
            formatted_songs = [
                f"{i + 1}. {song.name} - {song.artists}"
                for i, song in enumerate(songs)
            ]
            song_list = "\n".join([title] + formatted_songs)
            message_text = f"{song_list}\n\n请回复序号选择歌曲，或回复「取消」取消点歌"
            
            # 发送消息
            await self.send_text(message_text)
            
            # 存储等待选择状态
            chat_id = getattr(self, 'chat_id', '')
            user_id = getattr(self, 'user_id', '')
            selection_key = f"{chat_id}_{user_id}"
            plugin._pending_selections[selection_key] = {
                "songs": songs,
                "player": player,
                "timestamp": asyncio.get_event_loop().time(),
            }
            
            return True, "显示歌曲列表等待选择", True
            
        except Exception as e:
            logger.error(f"点歌命令执行失败: {e}")
            await self.send_text(f"点歌失败: {str(e)}")
            return False, str(e), True


class MusicSelectCommand(BaseCommand):
    """歌曲选择命令 - 处理点歌后的序号选择"""
    
    command_name = "music_select"
    command_description = "选择歌曲序号"
    command_pattern = r"^(?P<selection>\d+|取消)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行选择"""
        try:
            # 获取插件实例
            plugin = get_plugin()
            if not plugin:
                return True, "插件未初始化", False
            
            selection = self.matched_groups.get("selection", "")
            chat_id = getattr(self, 'chat_id', '')
            user_id = getattr(self, 'user_id', '')
            key = f"{chat_id}_{user_id}"
            
            # 检查是否有待选择的歌曲
            if key not in plugin._pending_selections:
                return True, "无待选择歌曲", False  # 不拦截，让其他处理器处理
            
            pending = plugin._pending_selections[key]
            
            # 检查是否超时（60秒）
            current_time = asyncio.get_event_loop().time()
            if current_time - pending["timestamp"] > 60:
                del plugin._pending_selections[key]
                await self.send_text("点歌已超时，请重新点歌")
                return True, "选择超时", True
            
            # 取消选择
            if selection == "取消":
                del plugin._pending_selections[key]
                await self.send_text("已取消点歌")
                return True, "取消选择", True
            
            # 获取选择的歌曲
            index = int(selection)
            songs = pending["songs"]
            player = pending["player"]
            
            if index < 1 or index > len(songs):
                await self.send_text(f"序号超出范围，请输入 1-{len(songs)} 之间的数字")
                return True, "序号超出范围", True
            
            # 发送选中的歌曲
            selected_song = songs[index - 1]
            await plugin.sender.send_song_command(self, player, selected_song)
            
            # 清除待选择状态
            del plugin._pending_selections[key]
            
            return True, f"发送歌曲: {selected_song.name}", True
            
        except Exception as e:
            logger.error(f"歌曲选择失败: {e}")
            return False, str(e), True


# ===== Command组件：查歌词 =====

class LyricsCommand(BaseCommand):
    """查歌词命令"""
    
    command_name = "lyrics"
    command_description = "查询歌曲歌词"
    command_pattern = r"^(查歌词|歌词)\s+(?P<song_name>.+)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行查歌词"""
        try:
            # 获取插件实例
            plugin = get_plugin()
            if not plugin:
                await self.send_text("插件未初始化")
                return True, "插件未初始化", True
            
            song_name = self.matched_groups.get("song_name", "")
            
            if not song_name:
                await self.send_text("请输入歌曲名称\n用法：查歌词 <歌名>")
                return True, "未提供歌曲名称", True
            
            player = plugin.get_player(default=True)
            if not player:
                await self.send_text("无可用播放器")
                return True, "无播放器", True
            
            # 搜索歌曲
            await self.send_text(f"正在搜索【{song_name}】的歌词...")
            songs = await player.fetch_songs(keyword=song_name, limit=1)
            
            if not songs:
                await self.send_text(f"没找到【{song_name}】相关的歌曲")
                return True, "搜索无结果", True
            
            # 获取并发送歌词
            song = songs[0]
            success = await plugin.sender.send_lyrics_command(self, player, song)
            
            if not success:
                await self.send_text(f"【{song.name}】暂无歌词")
            
            return True, f"查询歌词: {song.name}", True
            
        except Exception as e:
            logger.error(f"查歌词失败: {e}")
            await self.send_text(f"查歌词失败: {str(e)}")
            return False, str(e), True


# ===== 主插件类 =====

@register_plugin
class MusicPlugin(BasePlugin):
    """MaiBot 点歌插件"""
    
    # 插件基本信息
    plugin_name = "music_plugin"
    enable_plugin = True
    dependencies = []
    python_dependencies = ["aiohttp", "aiofiles", "Pillow"]
    config_file_name = "config.toml"
    
    # 配置Schema - 使用嵌套分组结构
    config_schema = {
        "general": {
            "default_player_name": ConfigField(
                type=str, 
                default="网易点歌", 
                description="默认点歌平台"
            ),
            "song_limit": ConfigField(
                type=int, 
                default=5, 
                description="搜索歌曲数量限制(1-20)"
            ),
            "select_mode": ConfigField(
                type=str, 
                default="text(文本模式)", 
                description="选择模式：text(文本模式)或single(单曲模式)"
            ),
            "timeout": ConfigField(
                type=int, 
                default=30, 
                description="点歌超时时间（秒）"
            ),
        },
        "send": {
            "send_modes": ConfigField(
                type=list, 
                default=["card(卡片模式)", "record(语音模式)", "file(文件模式)", "text(文本模式)"],
                description="发送模式优先级列表"
            ),
            "enable_comments": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用热评"
            ),
            "enable_lyrics": ConfigField(
                type=bool, 
                default=False, 
                description="是否启用歌词图片"
            ),
        },
        "network": {
            "proxy": ConfigField(
                type=str, 
                default="", 
                description="代理地址，如 http://127.0.0.1:7890，留空则不使用代理"
            ),
            "nodejs_base_url": ConfigField(
                type=str, 
                default="https://163api.qijieya.cn", 
                description="网易云NodeJS服务地址"
            ),
        },
        "cache": {
            "clear_cache": ConfigField(
                type=bool, 
                default=True, 
                description="重载插件时是否清空歌曲缓存"
            ),
        },
        "api_keys": {
            "enc_sec_key": ConfigField(
                type=str, 
                default="45c8bcb07e69c6b545d3045559bd300db897509b8720ee2b45a72bf2d3b216ddc77fb10daec4ca54b466f2da1ffac1e67e245fea9d842589dc402b92b262d3495b12165a721aed880bf09a0a99ff94c959d04e49085dc21c78bbbe8e3331827c0ef0035519e89f097511065643120cbc478f9c0af96400ba4649265781fc9079",
                description="网易云API密钥(一般无需修改)"
            ),
            "enc_params": ConfigField(
                type=str, 
                default="D33zyir4L/58v1qGPcIPjSee79KCzxBIBy507IYDB8EL7jEnp41aDIqpHBhowfQ6iT1Xoka8jD+0p44nRKNKUA0dv+n5RWPOO57dZLVrd+T1J/sNrTdzUhdHhoKRIgegVcXYjYu+CshdtCBe6WEJozBRlaHyLeJtGrABfMOEb4PqgI3h/uELC82S05NtewlbLZ3TOR/TIIhNV6hVTtqHDVHjkekrvEmJzT5pk1UY6r0=",
                description="网易云API参数(一般无需修改)"
            ),
        },
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global _plugin_instance
        
        # 立即初始化配置（关键配置不能等 initialize）
        # 注意：必须在 super().__init__ 之后，因为需要 self.get_config 方法
        try:
            self.cfg = MusicPluginConfig(self)
        except Exception as e:
            logger.error(f"配置初始化失败: {e}")
            raise
        
        # 立即注册播放器（关键功能）
        self.players: List[BaseMusicPlayer] = []
        self.keywords: List[str] = []
        self._register_players()
        
        # 初始化核心组件（不需要异步的）
        self.renderer = MusicRenderer(self.cfg)
        # sender 需要 downloader，而 downloader 的 initialize() 是异步的
        # 但我们可以先创建实例，异步操作（如清理缓存）在 initialize() 中执行
        self.downloader = Downloader(self.cfg)
        self.sender = MusicSender(self.cfg, self.renderer, self.downloader)
        
        # 等待选择的歌曲（用于点歌选择）
        self._pending_selections: Dict[str, Any] = {}
        
        # 立即设置全局实例
        _plugin_instance = self
        logger.debug(f"MusicPlugin 实例已创建，players: {len(self.players)}")
    
    async def initialize(self):
        """插件异步初始化（在 __init__ 之后调用）"""
        logger.info("开始初始化点歌插件异步组件...")
        try:
            # 下载器的异步初始化（清理缓存等）
            logger.debug("正在初始化下载器缓存...")
            await self.downloader.initialize()
            
            logger.info(f"点歌插件异步初始化完成")
            
        except Exception as e:
            logger.error(f"点歌插件异步初始化失败: {e}")
            logger.error(traceback.format_exc())
            # 不要清除 _plugin_instance，基本功能仍然可用
    
    async def terminate(self):
        """插件终止"""
        global _plugin_instance
        try:
            if self.downloader:
                await self.downloader.close()
            for player in self.players:
                await player.close()
            logger.info("点歌插件已卸载")
        except Exception as e:
            logger.error(f"点歌插件卸载失败: {e}")
        finally:
            # 清除全局引用
            _plugin_instance = None
    
    def _register_players(self):
        """注册音乐播放器"""
        all_subclass = BaseMusicPlayer.get_all_subclass()
        logger.debug(f"发现 {len(all_subclass)} 个播放器类: {[cls.__name__ for cls in all_subclass]}")
        for _cls in all_subclass:
            player = _cls(self.cfg)
            self.players.append(player)
            self.keywords.extend(player.platform.keywords)
            logger.debug(f"注册播放器: {player.platform.name} - {player.platform.display_name}")
        logger.info(f"已注册 {len(self.players)} 个播放器，触发词：{self.keywords}")
    
    def get_player(
        self, name: Optional[str] = None, word: Optional[str] = None, default: bool = False
    ) -> Optional[BaseMusicPlayer]:
        """获取播放器"""
        if default:
            word = self.cfg.default_player_name
        for player in self.players:
            if name:
                name_ = name.strip().lower()
                p = player.platform
                if p.display_name.lower() == name_ or p.name.lower() == name_:
                    return player
            elif word:
                word_ = word.strip().lower()
                for keyword in player.platform.keywords:
                    if keyword.lower() in word_:
                        return player
        return None
    
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        return [
            # Command组件
            (MusicCommand.get_command_info(), MusicCommand),
            (MusicSelectCommand.get_command_info(), MusicSelectCommand),
            (LyricsCommand.get_command_info(), LyricsCommand),
        ]
