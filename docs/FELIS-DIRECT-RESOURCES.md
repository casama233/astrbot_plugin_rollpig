# Felis 直读资源层

本插件以非商业 Bot 方式直接读取 [Felis rollpig-resources](https://github.com/Felis2026/rollpig-resources) 官方 manifest，只选审计过的 34 个基础资源 ID。资源写入 Bot 自己的数据目录 `felis_resources/active`，不会进入 curryudon 公共 CDN、公共 Manifest 或本项目资源镜像。

每次同步都会校验 manifest 协议、文件大小、SHA-256、图片格式与尺寸，并在临时目录完整成功后原子切换 active。网络失败时继续使用最近一次完整缓存；**直读协议仍不处理 Felis EX/variant 资源，也不会自动纳入未来新增 ID。**

## EX 文案隔离

为了让这 34 只直读小猪拥有 EX1–EX5 成长文案，同时不扩大上游资源使用范围，本项目维护独立的 `resource/felis_direct_ex_copy.json`：

- 当前固定 34 个 Felis direct ID 已全部采用本项目逐猪、逐级手写的 EX1–EX5 `description` 与 `analysis`，不再依赖 `name`、`theme`、`progress`、`lesson` 语义种子生成最终展示文案。
- 运行时只读取这些本地 text-only 文案；**不存在 `image` 字段或 Felis EX 图片下载入口**。
- 文案规格必须完整覆盖固定 34 ID，每只都必须明确提供 EX1–EX5 五级且每级同时包含 `description` 与 `analysis`；并声明 `provenance.scope = felis-direct-text-only` 与 `upstream_ex_used = false`。校验失败时放弃该层并回退既有 EX 安全基线。
- 手写内容只参考固定 34 ID 的基础图片、基础名称／描述／analysis 所表达的角色与笑点，并由本项目重新创作文案；不会读取、搬运或改写 Felis upstream EX/variant 文案与 EX 图片。
- 当 cloud/bundled EX 存在时，本地 Felis 文案层在其后应用到这 34 ID，因此不会从远端 EX 差分继承图片或文案；管理员 local override 仍保持最高优先级。
- 该层只影响展示文案，不改变抽取 ID、稀有度、保底、收藏计数、EX 等级计算或任何玩法状态。

来源与许可：

- 基础资源来源仓库：<https://github.com/Felis2026/rollpig-resources>
- 基础资源协议：<https://github.com/Felis2026/rollpig-resources/blob/main/RESOURCES-LICENSE.md>
- 基础资源使用方式：非商业 Bot 客户端直读上游、本机缓存，并保留来源与署名。
- EX1–EX5 文案层：由 `astrbot_plugin_rollpig` 项目独立维护，不读取 Felis 上游 EX/variant 文案或 EX 图片。

公共 curryudon cloud 层优先；34 项 Felis 仅补充 cloud 中不存在的 ID；基础图片读取顺序为 local override → EX → cloud → Felis overlay → bundled，最后仍由 local override/tombstone 控制图鉴显示。对 Felis 34 ID，项目自有 EX 文案层不会提供 EX 图片。