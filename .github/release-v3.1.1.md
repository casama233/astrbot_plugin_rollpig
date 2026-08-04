## 管理页性能修复

- 默认只加载轻量核心页面，不再自动拉取整包增强资源。
- Analytics 改为点击“深度分析”后按需加载。
- 移除大型源码 `sessionStorage` 缓存、100ms Bridge 轮询、持续 `MutationObserver` 和同步状态自动轮询。
- SPA 实例按当前页面根节点绑定，并通过 `AbortController` 清理旧事件，避免重复挂载。
- 通过 pytest、jsdom 回归测试与真实 Chromium 20 次 SPA 重入性能测试。
