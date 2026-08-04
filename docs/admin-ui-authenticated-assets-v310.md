# v3.1.0 管理页增强资源架构

## 不可破坏的核心层

`pages/pig-manager/index.html` 内的原始 ES 模块独立负责数据总览、猪猪图鉴、云资源同步、SQLite 管理和安全更新。即使增强资源接口、企业主题或 Analytics 全部失败，核心层仍必须可以初始化和切换视图。

## 认证增强层

- 浏览器仅直接加载 AstrBot 官方 `/api/plugin/page/bridge-sdk.js`。
- 小型内联 bootstrap 调用 `bridge.apiGet('ui/assets')`。
- 后端只读取 `UI_ASSET_FILES` 固定白名单，不接受文件名或路径参数。
- 返回内容包含版本、整包哈希、每项 SHA-256、类型和 UTF-8 源码。
- 客户端按 style → feedback → enterprise → analytics 顺序注入，并以 `3.1.0` 作为会话缓存键。

## 故障边界

- Bridge 或 `ui/assets` 失败：显示增强层诊断，核心页面继续运行。
- 单一增强脚本异常：记录具体模块，其他模块继续加载。
- `analytics/insights` 失败：只在深度分析区域显示重试，不影响普通总览和管理操作。
- AstrBot SPA 重新进入：新的页面令牌会触发脚本重挂载；样式复用，Analytics 根据当前 DOM 重新建立。
