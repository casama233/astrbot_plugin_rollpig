# Bundled lineage 手写 EX 文案层

本页记录非 Felis 小猪逐步脱离 deterministic generic EX baseline 的维护边界。

## 为什么单独做这一层

当前运行时会先为 active catalog 中每只小猪生成 deterministic EX1–EX5 安全基线。它保证任何 bundled、cloud-only、未来新增或管理员本地内容都有完整 EX 展示，但通用的「开始养熟／熟客上线／招牌常驻」等阶段句并不适合作为长期最终文案。

因此仓库新增 `resource/bundled_ex_copy.json`，用于分批保存本项目重新创作的逐猪、逐级 text-only EX 文案。它和 Felis 34 项的 `resource/felis_direct_ex_copy.json` 是两条不同 provenance 边界。

## Provenance 边界

`bundled_ex_copy.json` 必须满足：

- `provenance.scope = bundled-lineage-text-only`；
- `quarantined_ex_used = false`；
- 只能引用当前 `resource/pig.json` 中存在的 ID；
- 每只已手写小猪必须完整提供 EX1–EX5；
- 每级只允许 `description` 与 `analysis`，不允许 `image`；
- 五级短描述和完整文案都必须逐级不同。

2026-08-19 provenance remediation 隔离的历史 authored `resource/pig_ex_variants.json` 与 `resource/ex_curated/` **不会因为本计划恢复**。新的手写层从现行 base 名称、描述、analysis 与可核验的角色／网络语境重新创作，不把旧隔离 corpus 当素材来源。

## Active catalog 口径

不要把仓库 bundled catalog 数量直接等同于历史生产 public source 的 allow-list 数量。

历史 provenance 记录曾审计出 204 个 production canonical records，其中 157 allow、47 quarantine；但当前公开仓库并不保存那份生产 allow-list 的完整 canonical ID 清单。因此本手写层采取更窄、可证明的策略：

1. authoring 只接受 `resource/pig.json` 已有 lineage ID；
2. runtime 只对当前 active catalog 中同 ID 的项目生效；
3. cloud-only、未来新增或尚未完成 lineage review 的 ID 继续使用 deterministic baseline；
4. 如果以后取得新的可审计 active ID 来源，再单独扩展 authoring scope，而不是猜测历史 157 项。

## Runtime 优先级

EX 展示文案按以下方向叠加：

1. deterministic generic baseline；
2. 当前来源中合法的 cloud／bundled variant；
3. `bundled-lineage-text-only` 项目手写层；
4. Felis 34 项独立 `felis-direct-text-only` 手写层；
5. 管理员 local override 保持最高优先级。

因此开始手写非 Felis 文案不会破坏未完成小猪的安全兜底，也不会让 bundled layer 越权覆盖 Felis 隔离层或管理员本地编辑。

## Phase 1

首批完成 8 只，共 40 组独立 EX 文案：

- `human`
- `pig`
- `zhuge-liang`
- `zombie-pig`
- `skeleton-pig`
- `explosive-pig`
- `magic-pig`
- `mechanical-pig`

后续批次继续优先选择 base 画面／基础文案笑点明确、generic baseline 违和感高的小猪，并在需要时先核对实际梗或作品机制，再落 EX1–EX5。
