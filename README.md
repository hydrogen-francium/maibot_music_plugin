# MaiBot 点歌插件

轻量化的点歌插件，支持多音源、多种发送模式。

## 功能特性

- 🎵 **多音源支持**: 网易云音乐、QQ音乐、酷狗音乐、酷我音乐、百度音乐、一听音乐、咪咕音乐、荔枝FM、蜻蜓FM、喜马拉雅、5sing原创/翻唱、全民K歌
- 🎯 **智能点歌**: 支持关键词搜索，序号快速选择
- 📝 **查歌词**: 搜索并渲染歌词为精美图片
- 🎨 **多种发送模式**: 
  - 音乐卡片 (QQ平台显示为音乐卡片)
  - 语音消息 (直接播放)
  - 文件发送 (MP3文件)
  - 文本链接
- 💬 **热评展示**: 自动展示网易云热评

## 安装方法

1. 将插件文件夹复制到 MaiBot 的 `plugins/` 目录
2. 安装依赖: `pip install aiohttp aiofiles Pillow`
3. 重启 MaiBot

## 使用方法

### 点歌命令

```
点歌 <歌名>              # 使用默认平台点歌
点歌 <歌名> <序号>       # 指定序号直接播放
网易点歌 <歌名>          # 使用网易云音乐
QQ点歌 <歌名>            # 使用QQ音乐
酷狗点歌 <歌名>          # 使用酷狗音乐
...                      # 其他平台类似
```

**示例:**
- `点歌 稻香`
- `点歌 晴天 1`
- `网易点歌 七里香`
- `QQ点歌 青花瓷`

点歌后会显示歌曲列表，回复序号即可选择播放。

### 查歌词

```
查歌词 <歌名>
```

**示例:**
- `查歌词 稻香`

## 配置文件

插件自动生成 `config.toml` 配置文件:

```toml
[general]
default_player_name = "网易点歌"    # 默认点歌平台
song_limit = 5                      # 搜索歌曲数量限制(1-20)
select_mode = "text(文本模式)"      # 选择模式: text(文本模式)或single(单曲模式)
timeout = 30                        # 点歌超时时间(秒)

[send]
send_modes = [                      # 发送模式优先级
    "card(卡片模式)",
    "record(语音模式)", 
    "file(文件模式)",
    "text(文本模式)"
]
enable_comments = true              # 是否启用热评
enable_lyrics = false               # 是否启用歌词图片

[network]
proxy = ""                          # 代理地址，如 http://127.0.0.1:7890
nodejs_base_url = "https://163api.qijieya.cn"  # 网易云NodeJS服务

[cache]
clear_cache = true                  # 重载插件时是否清空缓存

[api_keys]
enc_sec_key = ""                    # 网易云API密钥(一般无需修改)
enc_params = ""                     # 网易云API参数(一般无需修改)
```

## 目录结构

```
.
├── _manifest.json          # 插件清单
├── plugin.py               # 主插件文件
├── __init__.py             # 包导出
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── config.py           # 配置类型
│   ├── downloader.py       # 文件下载器
│   ├── model.py            # 数据模型(Song, Platform)
│   ├── renderer.py         # 歌词渲染器
│   ├── sender.py           # 消息发送器
│   ├── utils.py            # 工具函数
│   └── platform/           # 音乐平台实现
│       ├── __init__.py
│       ├── base.py         # 平台基类
│       ├── ncm.py          # 网易云音乐
│       ├── ncm_nodejs.py   # 网易云(NodeJS版)
│       └── txqq.py         # TXQQ聚合平台
└── fonts/                  # 字体文件
    └── simhei.ttf          # 黑体字体(歌词渲染用)
```

## 技术说明

本插件基于 MaiBot 插件系统再开发，使用以下组件:

- **Command组件**: 提供点歌、选歌、查歌词命令
- **配置系统**: 使用 MaiBot 的配置管理
- **日志系统**: 使用 MaiBot 的日志 API

## 许可证

MIT License

## 作者

氢

## 致谢

原 AstrBot 版本插件: [astrbot_plugin_music](https://github.com/Zhalslar/astrbot_plugin_music)；
kimi