# v3.11.7

## 来源、资源与公共源安全整改

- 本版本继续采用 credit-first 的来源说明策略；README / LICENSE / ATTRIBUTION / RESOURCE_PROVENANCE 已补充 RollPig 系列沿革以及与 `Felis2026/nonebot-plugin-rollpig-plus` 的参考／移植关系。
- 旧 bundled 手写 EX 文案与历史 compatibility-floor 自动发布路径保持隔离；正式公共静态源当前使用 `provenance-safe-base-only` 发布集，共 157 项，另有 47 项因来源／再分发依据尚未逐项确认而继续 quarantine。
- 当前正式静态源携带 `NOTICE.md`、`PROVENANCE.json` 与 `LICENSES/`；隔离资源、旧 authored EX、旧 roast-copy 与 compatibility-floor payload 不进入公开 release。

## 公共源投稿权利审核

- 公共源基础小猪与 EX 投稿统一升级为 rights-aware `submission_version: 3`；投稿前必须提供作者、权利人、HTTPS 来源、署名文本和可核验的再分发依据。
- 依据许可证投稿时必须填写许可证标识；依据明确授权投稿时必须提供 HTTPS 授权证据 URL；再分发确认与真实性声明必须显式勾选。
- 管理员批准投稿不再等于发布：批准必须显式确认 `rights_verified=true` 并填写权利审核备注，结果保持 `not_published`，后续发布必须经过独立 provenance-safe 流程。
- 管理面板展示 rights 证据并对缺失权利资料的旧投稿 fail-closed；旧 EX envelope v2 独立投稿／“批准即发布”页面已停用并引导回新的统一投稿入口。

## 生产安全边界

- 插件代码本身不会自动启动、开放或重新配置公共源服务；服务端部署与发布仍是独立的受控流程。
- 在独立离线 E2E、生产 canary 与最终只读审计完成后，生产端当前已运行 rights-aware 2.3.0 review service，并恢复受协议门禁保护的 review API：无正确协议头返回 403，管理员接口无 bearer token 返回 401，legacy envelope v2 返回 400。
- 审核服务仅允许写专用 review-state 目录，公共静态资源目录不在其 writable path 中；审核通过不会自动修改公开 `v1`。
- 当前生产公开 `v1` 仍为 157 项 base-only 发布集，47 项隔离资源继续不发布。

## 升级

- AstrBot 最低版本仍为 `>=4.24.2`。
- Resource Protocol v1、SQLite 游戏数据 schema、抽取／保底／烤猪等玩法规则不变。
- 公共源投稿协议升级为 rights-aware v3；旧投稿客户端应 fail-closed，而不是绕过新的权利资料要求。

> 本版本记录的是来源透明度、资源隔离和发布控制方面的技术整改事实，不代表对所有历史内容作 blanket license／法律权属结论，也不代表任何外部争议程序已经结束。
