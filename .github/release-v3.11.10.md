# v3.11.10

## Felis 官方直读／本机缓存

- 新增独立的 Felis 资源 overlay：非商业 AstrBot 客户端直接读取
  `Felis2026/rollpig-resources` 官方 Manifest，只接收固定的 34 项 allowlist。
- 下载会逐项校验 Manifest 协议、大小、SHA-256、图片解码与尺寸；整套验证完成后才
  原子切换 `felis_resources/active`，上游暂时不可用时继续保留最近一次完整缓存。
- Felis 资源不会加入 curryudon 公共 Manifest/CDN；未来新增 ID、EX 文案与 variant
  图片也不会被自动纳入。

## 图鉴分层与来源边界

- 运行时图鉴按公共 cloud 基础层、Felis 补充层、管理员 local override 与 tombstone
  规则组合；公共层已有的 ID 不会被 Felis 覆盖。
- 图片读取在 cloud 与 bundled 基础图片之间加入 Felis 本机缓存，原有 local override
  和 EX 行为保持兼容。
- `felis_direct_enabled=false` 时保留磁盘缓存以便回滚，但不将其并入运行时图鉴。
- 同步状态公开 Felis 上游仓库、资源协议、版本、缓存数量、最近成功时间和错误状态。

## 许可与兼容性

- 文档与 NOTICE 明确记录 Felis 来源、非商业 Bot 直读／本机缓存模式及禁止公共镜像的
  边界；不把下载能力描述成 PigHub 或其他第三方内容的开源再分发许可。
- 可由 v3.11.9 直接升级；AstrBot 最低版本仍为 `>=4.24.2`。
- 不改变 SQLite schema、Resource Protocol v1、rights-v3 投稿协议、抽取概率或玩法状态。

## 验证

- 真实 Felis 官方上游同步：34/34 条记录、34/34 张图片通过完整校验。
- 自动化测试：Felis 同步成功／失败保留、坏哈希、缓存完整性、来源优先级、配置与文档
  contract 均有覆盖。

> 本版本恢复的是客户端使用能力，并不对第三方资源作 blanket license 或版权保证。
