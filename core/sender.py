"""发送器模块 - MaiBot版本"""
import asyncio
import base64
import random
from typing import TYPE_CHECKING, List, Optional

from src.plugin_system.apis import logging_api, send_api

if TYPE_CHECKING:
    from src.plugin_system import BaseTool, BaseCommand
    from .config import PluginConfig
    from .downloader import Downloader
    from .model import Song
    from .platform import BaseMusicPlayer
    from .renderer import MusicRenderer

logger = logging_api.get_logger("music_plugin")


async def recall_message(component, message_id: str, display_message: str = "") -> bool:
    """
    撤回消息 - 参考撤回插件实现
    
    Args:
        component: Command 或 Tool 组件实例
        message_id: 要撤回的消息ID
        display_message: 显示消息（可选）
    
    Returns:
        bool: 是否撤回成功
    """
    if not message_id:
        logger.warning("撤回消息失败：message_id 为空")
        return False
    
    # 尝试多种命令名（适配不同平台）
    DELETE_COMMANDS = ["DELETE_MSG", "delete_msg", "RECALL_MSG", "recall_msg"]
    
    for cmd in DELETE_COMMANDS:
        try:
            res = await component.send_command(
                cmd,
                {"message_id": str(message_id)},
                display_message=display_message or "🎵 点歌超时，已自动撤回",
                storage_message=False,
            )
            
            # 检查结果
            ok = False
            if isinstance(res, bool):
                ok = res
            elif isinstance(res, dict):
                if str(res.get("status", "")).lower() in ("ok", "success") or \
                   res.get("retcode") == 0 or res.get("code") == 0:
                    ok = True
            
            if ok:
                logger.debug(f"消息撤回成功：message_id={message_id}, cmd={cmd}")
                return True
                
        except Exception as e:
            logger.debug(f"撤回命令 {cmd} 失败：{e}")
            continue
    
    logger.warning(f"消息撤回失败：message_id={message_id}")
    return False


class MusicSender:
    """音乐发送器 - 适配MaiBot"""
    
    def __init__(
        self, config: "PluginConfig", renderer: "MusicRenderer", downloader: "Downloader"
    ):
        self.cfg = config
        self.renderer = renderer
        self.downloader = downloader

    @staticmethod
    def _format_time(duration_ms):
        """格式化歌曲时长"""
        if not duration_ms:
            return "未知"
        duration = duration_ms // 1000
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    async def send_song_command(
        self,
        command: "BaseCommand",
        player: "BaseMusicPlayer",
        song: "Song",
        modes: List[str] | None = None,
    ):
        """发送歌曲（Command版本）- 参考标准实现"""
        user_id = getattr(command, 'user_id', 'unknown')
        logger.debug(f"用户 {user_id} 点歌：{player.platform.display_name} -> {song.name}_{song.artists}")

        # 获取音频URL（如果没有）
        if not song.audio_url:
            song = await player.fetch_extra(song)
        
        # 构建显示消息
        display_message = f"[音乐：《{song.name}》- {song.artists}]"
        
        sent = False
        target_modes = modes if modes is not None else self.cfg.real_send_modes
        
        for mode in target_modes:
            mode_key = mode.split("(")[0].strip() if "(" in mode else mode
            logger.debug(f"尝试发送模式: {mode_key}")
            
            try:
                if mode_key == "card":
                    # 音乐卡片模式 - 使用 music 类型
                    if song.id:
                        await command.send_custom(
                            message_type="music",
                            content=str(song.id),
                            display_message=display_message
                        )
                        sent = True
                        logger.info(f"音乐卡片发送成功: {song.name}")
                        break
                    
                elif mode_key == "record":
                    # 语音模式 - 使用 voiceurl 类型
                    if song.audio_url:
                        await command.send_custom(
                            message_type="voiceurl",
                            content=song.audio_url,
                            display_message=display_message
                        )
                        sent = True
                        logger.info(f"语音发送成功: {song.name}")
                        break
                    else:
                        logger.warning(f"audio_url 为空，无法发送语音: {song.name}")
                        
                elif mode_key == "file":
                    # 文件模式 - 下载后发送
                    if song.audio_url:
                        file_path = await self.downloader.download_song(song.audio_url)
                        if file_path:
                            # 读取文件转为base64
                            with open(file_path, 'rb') as f:
                                file_base64 = base64.b64encode(f.read()).decode('utf-8')
                            await command.send_custom(
                                message_type="file",
                                content=file_base64,
                                display_message=f"[文件] {song.name}.mp3"
                            )
                            sent = True
                            logger.info(f"文件发送成功: {song.name}")
                            break
                        else:
                            logger.warning(f"文件下载失败: {song.name}")
                    else:
                        logger.warning(f"audio_url 为空，无法发送文件: {song.name}")
                        
                elif mode_key == "text":
                    # 文本模式
                    info = f"🎵 {song.name} - {song.artists}\n"
                    if song.duration:
                        info += f"⏱️ 时长：{self._format_time(song.duration)}\n"
                    if song.audio_url:
                        info += f"🔗 {song.audio_url}"
                    await command.send_text(info)
                    sent = True
                    logger.info(f"文本发送成功: {song.name}")
                    break
                    
            except Exception as e:
                logger.error(f"{mode_key} 发送失败: {e}")
                continue

        if not sent:
            await command.send_text("歌曲发送失败")
            return

        # 发送附加内容
        if self.cfg.enable_comments:
            await self._send_comments_command(command, player, song)
        
        if self.cfg.enable_lyrics:
            await self._send_lyrics_command(command, player, song)

    async def _send_comments_command(self, command: "BaseCommand", player: "BaseMusicPlayer", song: "Song"):
        """发送评论（Command版本）"""
        if not song.comments:
            await player.fetch_comments(song)
        if not song.comments:
            return
        try:
            content = random.choice(song.comments).get("content")
            await command.send_text(f"💬 热评：{content}")
        except Exception:
            pass

    async def _send_lyrics_command(self, command: "BaseCommand", player: "BaseMusicPlayer", song: "Song"):
        """发送歌词图片（Command版本）"""
        if not song.lyrics:
            await player.fetch_lyrics(song)
        if not song.lyrics:
            return
        try:
            image_bytes = self.renderer.draw_lyrics(song.lyrics)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            await command.send_custom(
                message_type="image",
                content=image_base64,
                display_message=f"[歌词] {song.name}"
            )
        except Exception as e:
            logger.error(f"歌词发送失败: {e}")

    async def send_lyrics_command(self, command: "BaseCommand", player: "BaseMusicPlayer", song: "Song") -> bool:
        """发送歌词（供外部调用）"""
        if not song.lyrics:
            await player.fetch_lyrics(song)
        if not song.lyrics:
            return False
        try:
            image_bytes = self.renderer.draw_lyrics(song.lyrics)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            await command.send_custom(
                message_type="image",
                content=image_base64,
                display_message=f"[歌词] {song.name}"
            )
            return True
        except Exception as e:
            logger.error(f"歌词发送失败: {e}")
            return False
