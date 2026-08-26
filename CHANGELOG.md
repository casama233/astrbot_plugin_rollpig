# 更新

## 未發佈

- `roasted-pig` 与 `pigsleep` 的本地高质量替换版进入来源受控的公共资源迁移流程：两者均沿用既有 Bearlele/MegSopern MIT 资源身份，不增加目录 ID；前者为同图优化，后者为基于 MIT 原图的大幅重绘，并以精确 SHA-256 与 machine-readable provenance gate 防止误替换。
- `papa-pig` 继续因外部下载来源／再分发权未证实而保持 withheld；PigHub-only 本地资源不在本次迁移范围内。
- 公共灾备猪源在来源／再分发审计期间改为 fail-closed：官方链只访问 curryudon primary，即使旧配置仍保留 Vercel/GitHub 镜像也不会读取；主源不可用时继续使用最近一次已验证本地缓存或内置资源。
- Felis 34 项直读资源新增项目自有 EX1–EX5 文案层：仅由本仓库语义规格生成 `description`/`analysis`，不读取 Felis EX/variant 文案或图片；固定 allowlist、provenance 与 text-only 合约均有回归测试。

## v3.11.12

发布日期：2026-08-25

v3.11.12 是 v3.11.11 之后的日报人物资料与帮助渲染稳定性 patch：补齐日报奖项目标的昵称／头像解析，修复帮助字体与 GitHub source archive 的中文字体保留，并把 QQ 原生 `@` 使用提醒放到相关帮助行附近。本版不新增或扩展「吃群友」玩法。

### 日报人物资料

- 日报 award target／victim 即使从未作为 RollPig 指令发送者，也可从结构化 mention、平台原生 ID 与可选实时群成员资料补齐 display name／avatar。
- aiocqhttp／OneBot 实时资料查询限制为 4 秒 timeout、最多 4 路并发，并保证网络 I/O 不在插件 data lock 内执行；未知平台不会猜测头像 URL。
- 新增 profile alias、fallback、live lookup、cache 与 MRO wiring 回归测试；不修改日报统计、奖项算法、SQLite schema 或自动投递语义。

### 帮助、字体与归档

- QQ 原生 `@` 提醒从帮助卡顶部下沉到相关指令附近；其中包含既有 `/吃群友 @某人` 的输入提示，但不改变该指令的成功率、状态、惩罚或其他玩法逻辑。
- 缩短预约烤猪与次日保护的帮助文案，并更新 KNMaiyuan 字体以恢复 `1–5`、`1–9` 等范围中的 `–` 可见字形。
- 随仓库保留 KNMaiyuan 的 SIL Open Font License 1.1 notice；GitHub source archive 不再排除运行时中文字体，避免以 source archive 安装时回退到缺少 CJK 的系统字体。

### 兼容性

- 可由 v3.11.11 直接升级；AstrBot 最低版本仍为 `>=4.24.2`。
- 不新增指令、不新增配置键，不修改 SQLite schema、Resource Protocol v1、rights-v3 投稿协议或「吃群友」玩法规则。

## v3.11.11

发布日期：2026-08-23

v3.11.11 是 v3.11.10 之后的玩家文案与 Wiki 一致性修复版：被吃后的次日惩罚早已改为概率强制重复猪，但「吃群友」失败回复、指令说明与排障页仍残留旧的抽取失败／锁天说法；本版统一为实际规则。

### 被吃后次日惩罚文案

- 「吃群友」失败后的提示改为次日可能抽到重复猪，不再误报可能抽猪失败。
- JSON 相容后端移除不可达的旧「请明天再来」回复分支；次日抽取继续正常完成，命中概率时仅从已解锁池强制选择重复猪。
- 新增源码与文档一致性回归测试，防止旧的失败／锁天文案再次出现。

### Wiki 与兼容性

- `docs/COMMANDS.md` 的今日小猪、吃群友与 FAQ 说明同步改为强制重复猪语义。
- 排障 Wiki明确说明默认 20% 命中时仍正常完成抽取，不会锁到自然日结束。
- 既有配置键 `eaten_next_day_failure_percent`、默认值、SQLite schema、Resource Protocol v1 与 rights-v3 投稿协议均不变；可由 v3.11.10 直接升级。

## v3.11.10

发布日期：2026-08-21

v3.11.10 在不扩大 curryudon 公共再分发范围的前提下恢复后期 Felis
资源可用性：34 项固定 allowlist 由非商业 AstrBot 客户端直接读取 Felis 官方
上游并在 Bot 本机缓存，公共来源、Felis 直读层与管理员本地覆盖继续相互隔离。

### Felis 官方直读资源层

- 新增默认启用的非商业 Felis 官方直读路径，仅本机缓存审计过的 34 项基础资源。
- 资源不进入 curryudon 公共 CDN/Manifest；同步过程校验 manifest、大小、SHA-256 与图片内容后原子切换。
- 网络失败继续使用最近一次完整缓存；Felis EX/variant 与未来新增资源不会自动纳入。
- 配置、署名、来源与资源许可边界同步记录于 `docs/CONFIGURATION.md`、`ATTRIBUTION.md` 与 `RESOURCE_PROVENANCE.md`。

### 分层优先级与停用行为

- 公共来源同 ID 继续优先于 Felis；Felis 只补齐公共层没有的 34 项，管理员本地覆盖与 tombstone 规则保持不变。
- 关闭 `felis_direct_enabled` 后不会删除已有缓存，但缓存不会继续并入运行时图鉴。
- 图片读取路径继续保持本地 override 与既有 EX 解析规则，并在 cloud 与 bundled 基础图片之间加入 Felis 本机缓存层。

### 兼容性与维护记录

- 随机烤群友继续先单独显示 `@指令發起者`，再在转盘句中标识被烤对象，避免混淆两种身份。
- 可由 v3.11.9 直接升级；AstrBot 最低版本仍为 `>=4.24.2`，SQLite schema、Resource Protocol v1 与 rights-v3 投稿协议不变。
- 本版本不宣称 PigHub 或其他第三方资源获得新的开源授权，也不将 Felis 资源重新托管为 curryudon 公共镜像。

## v3.11.9

发布日期：2026-08-20

v3.11.9 是 v3.11.8 之后的渲染稳定性 patch，收录已合入 #176 的烤猪料理卡缺图降级，并继续保持现有 provenance-safe 公共源与 rights-aware 审核边界。
