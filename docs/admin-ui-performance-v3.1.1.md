# v3.1.1 管理页性能架构

## 默认路径

管理页首次进入只运行内联核心模块与一个小型 Analytics 按钮注册器。默认路径不会请求 `ui/assets`，不会注入 Analytics CSS/JavaScript，也不会创建 DOM 观察器或后台轮询。

## 按需 Analytics

用户点击“深度分析”后，按钮注册器才通过 AstrBot 认证 Bridge 请求固定白名单资源：

- `analytics-theme.css`
- `ui-analytics.js`

源码只保存在当前页面内存中，不写入 `sessionStorage`。第二次点击仅刷新聚合数据，不重新下载资源。

## SPA 生命周期

每次管理页实例以当前 `.shell` 元素作为身份。新根节点出现时，旧实例的 `AbortController` 会解除按钮和刷新事件；Analytics 渲染前也会确认状态仍属于当前根节点，避免旧异步请求写入新页面。

## 性能验收

- jsdom：40 次默认 SPA 重入，增强 API 请求、`MutationObserver` 和 `setInterval` 均为 0。
- Chromium：20 次点击加载与 SPA 重入后，当前 DOM 只保留一份按钮、Analytics 套件、样式和脚本；强制 GC 后 JS 堆增长必须低于 24 MiB。
- 真实运行结果写入 `docs/performance-v3.1.1.json`。
