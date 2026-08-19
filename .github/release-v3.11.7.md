# v3.11.7

## 公共源投稿权利审核

- 公共源基础小猪与 EX 投稿统一升级为 rights-aware `submission_version: 3`；投稿前必须提供作者、权利人、HTTPS 来源、署名文本和可核验的再分发依据。
- 依据许可证投稿时必须填写许可证标识；依据明确授权投稿时必须提供 HTTPS 授权证据 URL；再分发确认与真实性声明必须显式勾选。
- 管理员批准投稿不再等于发布：批准必须显式确认 `rights_verified=true` 并填写权利审核备注，结果保持 `not_published`，后续发布必须经过独立 provenance-safe 流程。
- 管理面板展示 rights 证据并对缺失权利资料的旧投稿 fail-closed；旧 EX envelope v2 独立投稿／“批准即发布”页面已停用并引导回新的统一投稿入口。

## 安全边界

- 本版本只改造客户端与维护者管理 UI 的投稿／审核契约，不会自行恢复生产 review API，也不会启动生产 review service。
- 当前公开静态源仍使用已审核的 provenance-safe 157 项资源；47 项隔离资源与自动发布路径保持隔离。

## 升级

- AstrBot 最低版本仍为 `>=4.24.2`。
- Resource Protocol v1、SQLite 游戏数据 schema、抽取／保底／烤猪等玩法规则不变。
