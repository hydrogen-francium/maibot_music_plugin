# MaiBot 点歌插件

轻量化的点歌插件，支持多音源点歌、音乐卡片、语音播放、热评、歌词等功能。

## 功能特性

- **多音源支持**: 网易云音乐、QQ音乐、酷狗、酷我等
- **点歌命令**: 支持关键词点歌、平台指定点歌
- **序号选择**: 搜索后通过序号快速选择歌曲
- **查歌词**: 搜索并显示歌曲歌词图片
- **多种发送模式**: 音乐卡片、语音、文件、文本
- **超时撤回**: 选歌列表超时后自动撤回，保持聊天界面整洁

## 安装

1. 将插件文件夹放入 MaiBot 的 `plugins` 目录
2. 安装依赖：`pip install aiohttp aiofiles Pillow httpx`
3. 重启 MaiBot

## 配置说明

编辑 `config.toml`：

```toml
[general]
default_player_name = "网易点歌"    # 默认点歌平台
song_limit = 5                     # 搜索歌曲数量限制(1-20)
select_mode = "text(文本模式)"      # 选择模式：text(文本模式)或single(单曲模式)
timeout = 30                       # 点歌超时时间（秒）

[send]
send_modes = [                     # 发送模式优先级列表
    "card(卡片模式)",
    "record(语音模式)",
    "file(文件模式)",
    "text(文本模式)"
]
enable_comments = true             # 是否启用热评
enable_lyrics = false              # 是否启用歌词图片
timeout_recall = true              # 超时后是否撤回选歌消息

[napcat]
host = "127.0.0.1"                 # NapCat 服务地址
port = 9999                        # NapCat HTTP 服务端口（MaiBot 默认使用 9999）
token = ""                         # NapCat 认证 Token（留空表示不需要）

[network]
proxy = ""                         # 代理地址，如 http://127.0.0.1:7890
nodejs_base_url = "https://163api.qijieya.cn"  # 网易云 NodeJS 服务地址

[cache]
clear_cache = true                 # 重载插件时是否清空歌曲缓存

[api_keys]
# 网易云 API 密钥（一般无需修改）
enc_sec_key = "..."
enc_params = "..."
```

### NapCat 配置说明

**撤回功能需要 NapCat 的 HTTP 服务支持：**

1. 访问 NapCat WebUI (`http://IP:6099`)
2. 进入「网络配置」→「OneBot 服务」
3. 确保 **HTTP 服务**已启用，端口设为 `9999`（或你喜欢的端口）
4. 保存配置并重启 NapCat

如果使用 Docker 部署 MaiBot，NapCat 的 HTTP 端口默认是 `9999`。

## 使用说明

### 点歌命令

```
点歌 <歌名> [序号]
```

示例：
- `点歌 稻香` - 搜索歌曲并显示列表
- `点歌 稻香 1` - 直接播放第一首
- `网易云 稻香` - 使用网易云搜索
- `qq点歌 稻香` - 使用 QQ 音乐搜索

### 查歌词

```
查歌词 <歌名>
歌词 <歌名>
```

### 选择歌曲

发送点歌命令后，会显示歌曲列表：

```
【网易云音乐】
1. 稻香 - 周杰伦
2. 稻香 (Live) - 周杰伦
3. ...

请回复序号选择歌曲，或回复「取消」取消点歌
```

回复 `1`、`2` 等序号选择歌曲，或回复 `取消` 取消点歌。

**三种结束方式都会自动撤回选歌列表：**
- ✅ 选择歌曲 → 撤回列表 → 发送歌曲
- ✅ 取消点歌 → 撤回列表 → 提示"已取消"
- ✅ 超时 → 撤回列表 → 提示"已超时"

## 更新日志

### v2.2.0 (2026-03-21)

**新增功能**
- 选歌列表自动撤回功能（三种结束方式都会撤回）
- 新增 NapCat HTTP API 直接调用，获取真实 message_id
- 支持群聊和私聊场景的撤回

**改进**
- 重写撤回管理器，使用任务调度机制
- 添加 2 分钟撤回时间限制检查（QQ 限制）
- 优化配置结构，新增 `[napcat]` 配置节

**依赖更新**
- 新增 `httpx` 依赖

### v2.1.0

- 初始版本
- 支持多音源点歌
- 支持音乐卡片、语音、文件、文本发送模式
- 支持热评和歌词显示

## 项目结构

```
氢_music_plugin/
├── plugin.py              # 主插件文件
├── config.toml            # 配置文件
├── core/                  # 核心模块
│   ├── __init__.py
│   ├── downloader.py      # 下载器
│   ├── model.py           # 数据模型
│   ├── napcat_api.py      # NapCat HTTP API
│   ├── platform.py        # 音乐平台
│   ├── recall_manager.py  # 撤回管理器
│   ├── renderer.py        # 歌词渲染器
│   └── sender.py          # 消息发送器
├── fonts/                 # 字体文件
└── README.md              # 本文件
```

## 致谢

- 参考 [MaiBot-Napcat-Adapter](https://github.com/MaiM-with-u/MaiBot-Napcat-Adapter) 实现 NapCat API 调用
- 使用 [NapCat](https://github.com/NapNeko/NapCatQQ) 作为 QQ 协议端
- 原 AstrBot 版本插件: [astrbot_plugin_music](https://github.com/Zhalslar/astrbot_plugin_music)
- kimi

## License

MIT License
