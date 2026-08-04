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
- 页面卸载时企业增强层会断开 MutationObserver，避免旧页面观察器污染下一次进入。

## 浏览器行为验收

v3.1.0 的发布验证使用 Node 22 与 jsdom 实际构造管理页 DOM，并执行以下四个场景：

1. `ui/assets` 返回 401 时，数据总览仍能加载，且可切换到猪猪图鉴。
2. 认证资源正常返回时，企业主题、交互反馈和深度 Analytics 均完成注入，页面不产生相对 UI 子资源请求。
3. `analytics/insights` 失败时，只显示 Analytics 局部错误，核心页面仍可操作。
4. AstrBot 单页容器二次进入时，页面令牌更新，企业装饰和 Analytics 可重新挂载。

浏览器行为测试、前端语法、内联模块语法、123 项 pytest、Python 编译与 pre-commit 均须通过后，验证任务才允许写回产品分支。
