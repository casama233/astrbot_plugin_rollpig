# Felis 直读资源层

本插件以非商业 Bot 方式直接读取 [Felis rollpig-resources](https://github.com/Felis2026/rollpig-resources) 官方 manifest，只选审计过的 34 个基础资源 ID。资源写入 Bot 自己的数据目录 `felis_resources/active`，不会进入 curryudon 公共 CDN、公共 Manifest 或本项目资源镜像。

每次同步都会校验 manifest 协议、文件大小、SHA-256、图片格式与尺寸，并在临时目录完整成功后原子切换 active。网络失败时继续使用最近一次完整缓存；不处理 Felis EX/variant 资源，也不会自动纳入未来新增 ID。

来源与许可：

- 来源仓库：<https://github.com/Felis2026/rollpig-resources>
- 资源协议：<https://github.com/Felis2026/rollpig-resources/blob/main/RESOURCES-LICENSE.md>
- 使用方式：非商业 Bot 客户端直读上游、本机缓存，并保留来源与署名。

公共 curryudon cloud 层优先；34 项 Felis 仅补充 cloud 中不存在的 ID；图片读取顺序为 local override → EX → cloud → Felis overlay → bundled，最后仍由 local override/tombstone 控制图鉴显示。
