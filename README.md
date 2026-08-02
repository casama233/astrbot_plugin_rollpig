<div align="center">

![astrbot_plugin_rollpig](https://raw.githubusercontent.com/casama233/astrbot_plugin_rollpig/main/logo.png)

# astrbot_plugin_rollpig
_✨ [astrbot](https://github.com/AstrBotDevs/AstrBot) 今日小猪 ✨_ 

本仓库是基于 `MegSopern/astrbot_plugin_rollpig` 的功能增强维护分支。保留原作者
Bear_lele、MegSopern 的署名与 MIT License；增强分支由 casama233 继续维护。
上游项目：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.24.2%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/作者-MegSopern-pink)](https://github.com/MegSopern)
![动态访问量](https://count.kjchmc.cn/get/@astrbot_plugin_rollpig?theme=gelbooru)

</div>

## 🌟 项目介绍
每日用户可随机抽取专属“今日小猪”，并生成配图展示名称、描述和性格。无需繁琐配置，支持自定义猪猪库和素材。自动缓存结果，每日刷新，避免重复。适合群聊互动或签到，增添聊天趣味。
## 📦 安装：

```bash
# 克隆仓库到插件目录
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig

# 控制台重启AstrBot
```

## 🐷 使用 🐷

**今日小猪／今日小豬** - 抽取今天属于你的小猪类型 🐖

- 每个用户每天只能抽取一次 🐽  
- 重复抽取不会改变结果 🐷  
- 每天 0 点自动重置 🐖

**我的猪圈／我的豬圈 [页码]** - 查看永久解锁的小猪图鉴

- 每次抽取会永久记录已解锁的小猪
- 重复抽中会累计该小猪的抽取次数
- 重复抽中会提升 `EX Lv.`，图鉴同时展示本命猪与最高等级
- 连续重复时触发渐进保底，提高后续解锁新猪的机会
- 图鉴每页展示 12 只小猪，例如：`/我的猪圈 2`

### 更多玩法

| 指令 | 功能 |
| --- | --- |
| `/昨日小猪`／`/昨日小豬` | 查看昨天真实抽到的小猪 |
| `/明日小猪`／`/明日小豬` | 查看明日固定预测与猪运星级，不提前解锁 |
| `/本周小猪`／`/本週小豬` | 生成本周七日小猪周报 |
| `/随机小猪 [1-9]`／`/隨機小豬` | 从本地图鉴随机展示，不影响今日结果 |
| `/找猪 关键词`／`/找豬` | 按 ID、名称、描述或完整文案搜索本地图鉴 |
| `/今日烤猪`／`/今日烤豬` | 把今日小猪生成趣味料理卡，不改变抽取结果 |

昨日和本周记录从升级至 v1.5.0 后开始完整保存；升级当天现有的今日记录会自动迁移。

## 🖥️ 猪圈管理面板

AstrBot 管理面板的「插件页面」中会出现「今日小猪」管理页，支持：

- 新增小猪：一次填写 ID、名称、描述、完整文案并上传图片
- 也可在面板内搜索／分页浏览 PigHub.top，选定图片后手动填写名称、描述与文案
- PigHub 选图后可填写画面／创作引导词，并在生成 AI 草稿时查看实时阶段进度
- 上传图片自动居中裁切并标准化为 `512×512 PNG`
- 搜索、编辑、删除现有小猪；历史解锁统计不会因删除素材而丢失
- 查看云资源版本与同步状态，并可在管理面板手动立即同步
- 查看总使用人数、累计抽取、今日活跃、人均解锁、平均收藏率
- 查看近 14 日使用／解锁折线图与热门小猪柱状图

管理页修改后的图鉴和图片保存在 AstrBot 的插件数据目录中，升级插件时不会覆盖。图鉴按以下优先级合并：

1. 公共云资源（不可用时回退插件内置资源）
2. 管理面板的本地新增／编辑与自定义图片
3. 本地删除屏蔽（确保已删除的云端小猪不会在下次同步后复活）

公共资源默认每 24 小时检查一次，单文件限制 10 MiB。下载会校验 manifest 中的尺寸与 SHA-256，并在整包通过后才原子替换；任何失败都继续使用旧缓存或内置资源。

可在插件配置中关闭连续重复保底或今日烤猪，并调整每层保底增加的概率。

---

## 🐖 新增小猪 🐖

插件资源路径：

```
astrbot_plugin_rollpig/resource
```

- **pig.json** 小猪信息，例如：

```json
[
    {
        "id": "pig",
        "name": "猪",
        "description": "普通小猪",
        "analysis": "你性格温和，喜欢简单的生活，容易满足。在别人眼中可能有些慵懒，但你知道如何享受生活的美好。"
    }
]
```

- **image/** 小猪图片  
    - 图片命名需和信息中的 `id` 一致  
    - 支持图片类型：`["png", "jpg", "jpeg", "webp", "gif"]`

---

### 🐽 目录结构示例 🐽

```
astrbot_plugin_rollpig/
├─ main.py               # 插件主逻辑（AstrBot插件核心）
└─ resource/
    ├─ pig.json          # 小猪信息数据
    └─ image/
        └─ pig.png       # 小猪图片（与id对应）
```

---

## 🐖 注意事项 🐖

- 新增小猪时只需在 `pig.json` 添加对象，并将对应图片放到 `image/` 文件夹即可 🐷  
- 图片自动按 id 匹配，无需在 JSON 中写图片后缀 🐖  

## 🎖️ 致谢
- 本插件基于[nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)的核心逻辑进行改造。
- 欢迎前往原仓库为作者的辛苦付出点亮 ⭐ Star 支持！

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE) 开源，详情请查阅许可证文件

![Star History Chart](https://api.star-history.com/svg?repos=casama233/astrbot_plugin_rollpig&type)


## 2.4.0 稳定性与安全更新

- 今日抽取改为单事务写入，避免并发造成今日结果与永久图鉴不一致。
- `@他人` 仅查看已有结果，不再替对方抽取，也不能绕过被吃惩罚。
- 用户与群组 ID 加入平台命名空间；旧数据在读取时保持兼容。
- JSON 损坏时保留 `.corrupt-*` 副本，并优先尝试 `.bak` 恢复。
- AI 文案增加可配置超时并按小猪分片加锁，避免单次模型卡住全部请求。
- 云资源限制重定向主机、拒绝私网解析、限制图片像素，并边下载边落盘。
- 管理页写操作增加同源与 CSRF 校验；缩略图改用压缩 PNG，降低响应体积。
- 新增每日边界时区配置，并修正图片句柄与裁剪行为。
