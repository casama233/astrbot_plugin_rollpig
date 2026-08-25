# v3.11.12

## 日报人物资料修复

- 日报奖项目标／受害者即使从未作为 RollPig 指令发送者，也可从结构化 mention、平台原生 ID 与可选实时群成员资料补齐昵称和头像。
- aiocqhttp／OneBot 实时资料查询限制为 4 秒 timeout、最多 4 路并发，且网络 I/O 不在插件 data lock 内执行。
- 未知平台不会猜测头像 URL；新增 profile alias、fallback、live lookup、cache 与 MRO wiring 回归覆盖。
- 不修改日报统计、奖项算法、SQLite schema 或自动投递语义。

## 帮助与字体

- QQ 原生 `@` 使用提醒改为紧邻相关帮助指令显示，降低复制／手打昵称导致目标解析失败的概率。
- 该提醒覆盖既有 `/吃群友 @某人` 输入方式，但本版**不新增或扩展「吃群友」玩法**，也不改变其成功率、状态或惩罚逻辑。
- 缩短预约烤猪与次日保护的帮助文案，并更新 KNMaiyuan 字体以恢复 `1–5`、`1–9` 等范围中的 `–` 可见字形。
- 随仓库保留 KNMaiyuan 的 SIL Open Font License 1.1 notice。

## Source archive 与兼容性

- GitHub source archive 不再排除运行时中文字体，修复从 source archive 安装时可能回退到缺少 CJK 字形的系统字体。
- 正式 GitHub Release ZIP 继续沿用现有 16 MB 打包限制与字体裁剪策略。
- 可由 v3.11.11 直接升级；AstrBot 最低版本仍为 `>=4.24.2`。
- 不新增指令、不新增配置键，不修改 SQLite schema、Resource Protocol v1、rights-v3 投稿协议或「吃群友」玩法规则。
