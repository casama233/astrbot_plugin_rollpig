# 公共灾备猪源 Fail-Closed 边界

## 当前状态

在公共资源来源／再分发权审计完成前，RollPig Plus 的官方灾备镜像暂时 **fail-closed**。

官方资源链当前只访问权威 primary：

`https://curryudon.top/astrbot-rollpig/v1/manifest.json`

即使旧安装的持久化配置仍保留 Vercel 或 GitHub mirror URL，运行时 hard gate 也不会访问这些公共镜像。这样可以避免 primary 暂时不可用时，客户端把整改前的 stale snapshot 当成灾备资源重新启用。

如果 primary 不可用，插件继续使用最近一次已经完整验证的本地 cloud cache；没有可用缓存时再使用发行包内置资源。这个行为不会切换到未经当前 provenance contract 验证的公共 mirror。

审计期间，官方 Vercel/GitHub mirror 的 `v1/manifest.json` 应保持不可用；出现可成功读取的公开 manifest 应视为需要立即处理的回归，而不是可接受的容灾状态。

## 私人／自定义资源源

管理员显式设置的兼容 HTTPS 私人 manifest 仍保持单一来源语义，不会被本次公共 mirror hard gate 改写，也不会在失败时偷偷切回官方公共链。

使用私人来源时，管理员仍需自行确认该来源的访问权限、内容来源及再分发依据。

## 为什么同时锁客户端与镜像仓库

仅删除灾备仓库当前资源并不足够：旧安装可能已经保存 mirror URL，而自动同步或旧部署也可能在未来重新暴露 stale snapshot。

因此当前整改采用双重边界：

1. 镜像仓库当前 publication tree 不再提供 `public/v1`，并停止自动同步；
2. 插件 runtime 对官方链只允许 primary，忽略旧的公共 Vercel/GitHub fallback 配置。

任一侧单独回归，都不能让未经审计的公共 mirror 自动重新成为客户端资源来源。

## 恢复公共灾备镜像的条件

以后只有在同一个独立审查变更中同时满足以下条件，才应解除 hard gate：

- mirror candidate 与权威公共源使用同一份已审计的 **provenance-safe base-only** publication；
- 实际发布包携带可供普通使用者查看的 `NOTICE.md`、`PROVENANCE.json` 与适用的 `LICENSES/`；
- authored EX、EX 图片、`pig_ex_variants.json`、`roast_copy.json`、历史 compatibility-floor payload 等扩展内容，除非已逐项建立明确再分发依据，否则不能进入 mirror；
- mirror CI 除 Resource Protocol、大小与 SHA-256 外，还要验证 publication profile、来源材料和禁止内容；
- 客户端对 mirror 有对应的 provenance-safe contract 校验，不能只凭 schema/client/version 就接受；
- 对 failover 做真实端到端验证，确认 primary 故障时不会降级到旧 snapshot。

解除 `PUBLIC_MIRROR_FAIL_CLOSED` 不应作为单独的便利性改动提交。

## 审计边界

保留旧 Git commit／审计记录不等于继续把旧 snapshot 作为当前公共资源源提供。历史证据应保留以便追踪整改事实；当前可访问的自动发布与客户端 fallback 路径则应保持 fail-closed，直到来源和再分发依据满足上述恢复条件。
