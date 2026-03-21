"""网易云音乐 NodeJS 版本"""
from typing import ClassVar, Optional

from src.plugin_system.apis import logging_api

from ..config import PluginConfig
from ..model import Platform, Song
from .base import BaseMusicPlayer

logger = logging_api.get_logger("music_plugin")


class NetEaseMusicNodeJS(BaseMusicPlayer):
    """
    网易云音乐（NodeJS API）
    """

    platform: ClassVar[Platform] = Platform(
        name="netease_nodejs",
        display_name="网易云音乐(NodeJS)",
        keywords=["nj", "nodejs"],
    )

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.base_url = config.nodejs_base_url

    async def fetch_songs(
        self, keyword: str, limit: int = 5, extra: Optional[str] = None
    ) -> list[Song]:
        # 搜索接口
        search_url = f"{self.base_url}/search"
        result = await self._request(
            url=search_url,
            method="GET",
            data={"keywords": keyword, "limit": limit},
        )

        if not result or not isinstance(result, dict):
            logger.error(f"搜索返回了意料之外的数据：{result}")
            return []

        songs_data = result.get("result", {}).get("songs", [])

        songs = []
        for s in songs_data[:limit]:
            song = Song(
                id=str(s.get("id")),
                name=s.get("name"),
                artists="、".join(a["name"] for a in s.get("artists", [])),
                duration=s.get("duration"),
            )
            songs.append(song)

        return songs
