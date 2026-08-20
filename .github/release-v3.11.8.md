# v3.11.8

## 稳定性与玩法体验

- 修复 AstrBot 热重载未完整执行旧插件 unload 时，旧 `_background_daily_report` asyncio scheduler 可能继续存活并额外发送猪圈日报的问题。新实例只清理与当前 `plugin_data_dir` 完全相同命名空间中的旧日报 task，原有 `(draw_date, group_id)` 持久化 delivery claim 继续作为最终 at-most-once 边界。
- 普通烤群友、随机烤群友与预约结算继续共用同一 `RoastService` outcome policy；结果权重由 **60% 成功 / 30% 逃脱 / 10% 反噬** 调整为 **70% / 20% / 10%**，并同步更新命令文档、预约说明、玩法 Wiki 与互动演示。
- `DrawService` 默认随机源改为私有 `SystemRandom`，避免同一 AstrBot 进程中其他插件调用 `random.seed(...)` 影响每日抽取；显式 RNG 注入仍保留用于测试。

## 回归与边界

- 新增连续三次热重载的 scheduler 清理回归测试，并验证不同 RollPig 数据命名空间不会被误取消。
- 烤猪 policy 测试锁定 70/20/10；抽取测试锁定默认 RNG 与 process-global random seed 隔离。
- SQLite schema、Resource Protocol v1、插件身份与公共源 rights-v3 schema 不变；可由 v3.11.7 直接升级，AstrBot 最低版本仍为 `>=4.24.2`。

## 来源与公共源安全边界

- 延续 v3.11.7 的 credit-first / provenance-safe 整改，不恢复当前 47 项隔离资源、旧 authored EX、旧 roast-copy 或 compatibility-floor 自动发布路径。
- 公共源投稿继续要求 rights-aware `submission_version: 3`；管理员审核通过仍保持 `not_published`，正式发布必须经过独立 provenance-safe 流程。
- 本版本不改变当前生产 **157 项 base-only** 公共静态源。

> 本版本说明的是已落地的技术变更与发布控制边界，不对所有历史内容作 blanket license／法律权属结论，也不代表任何外部争议程序已经结束。
