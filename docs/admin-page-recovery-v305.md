# v3.0.5 管理页可用性恢复

## 故障表现

v3.0.4 中，今日小猪插件内部页面只显示顶部导航，数据总览、猪猪图鉴以及同步、存储和更新区域无法显示。

## 恢复策略

- 恢复 v3.0.3 已验证可用的轻量 `index.html` 页面骨架。
- 撤销将约 2800 行企业主题和 Analytics 资源整体内联到主 HTML 的方案。
- 保持 SQLite 单一权威、后端 API、玩法逻辑和用户数据不变。
- 深度 Analytics 暂时降级，页面可用性优先。

## 发布门槛

- 真实提取 `<script type="module">` 并通过 Node 语法检查。
- 确认 `view-overview`、`view-catalog`、存储、更新和图鉴 DOM 锚点均存在。
- 主页面体积不得超过 300 KB。
- 禁止重新出现 `rollpig-inline-assets:start` 整页内联标记。
- Python 3.10、3.12、完整 pytest 与 pre-commit 必须通过。

一次性恢复任务已验证真实主模块语法、122 项测试与 pre-commit；最终发布仍需永久只读双版本 CI 通过。
