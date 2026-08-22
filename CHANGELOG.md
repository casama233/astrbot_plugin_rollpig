# 更新

## v3.11.11

发布日期：2026-08-23

v3.11.11 是 v3.11.10 之后的玩家文案与 Wiki 一致性修复版：被吃后的次日惩罚早已改为概率强制重复猪，但「吃群友」失败回复、指令说明与排障页仍残留旧的抽取失败／锁天说法；本版统一为实际规则。

### 被吃后次日惩罚文案

- 「吃群友」失败后的提示改为次日可能抽到重复猪，不再误报可能抽猪失败。
- JSON 相容后端移除不可达的旧「请明天再来」回复分支；次日抽取继续正常完成，命中概率时仅从已解锁池强制选择重复猪。
- 新增源码与文档一致性回归测试，防止旧的失败／锁天文案再次出现。

### Wiki 与兼容性

- `docs/COMMANDS.md` 的今日小猪、吃群友与 FAQ 说明同步改为强制重复猪语义。
- 排障 Wiki 明确说明默认 20% 命中时仍正常完成抽取，不会锁到自然日结束。
- 既有配置键 `eaten_next_day_failure_percent`、默认值、SQLite schema、Resource Protocol v1 与 rights-v3 投稿协议均不变；可由 v3.11.10 直接升级。

## v3.11.10

发布日期：2026-08-21

v3.11.10 在不扩大 curryudon 公共再分发范围的前提下恢复后期 Felis
资源可用性：34 项固定 allowlist 由非商业 AstrBot 客户端直接读取 Felis 官方
上游并在 Bot 本机缓存，公共来源、Felis 直读层与管理员本地覆盖继续相互隔离。

### Felis 官方直读资源层

- 新增默认启用的非商业 Felis 官方直读路径，仅本机缓存审计过的 34 项基础资源。
- 资源不进入 curryudon 公共 CDN/Manifest；同步过程校验 manifest、大小、SHA-256 与图片内容后原子切换。
- 网络失败继续使用最近一次完整缓存；Felis EX/variant 与未来新增资源不会自动纳入。
- 配置、署名、来源与资源许可边界同步记录于 `docs/CONFIGURATION.md`、`ATTRIBUTION.md` 与 `RESOURCE_PROVENANCE.md`。

### 分层优先级与停用行为

- 公共来源同 ID 继续优先于 Felis；Felis 只补齐公共层没有的 34 项，管理员本地覆盖与 tombstone 规则保持不变。
- 关闭 `felis_direct_enabled` 后不会删除已有缓存，但缓存不会继续并入运行时图鉴。
- 图片读取路径继续保持本地 override 与既有 EX 解析规则，并在 cloud 与 bundled 基础图片之间加入 Felis 本机缓存层。

### 兼容性与维护记录

- 随机烤群友继续先单独显示 `@指令發起者`，再在转盘句中标识被烤对象，避免混淆两种身份。
- 可由 v3.11.9 直接升级；AstrBot 最低版本仍为 `>=4.24.2`，SQLite schema、Resource Protocol v1 与 rights-v3 投稿协议不变。
- 本版本不宣称 PigHub 或其他第三方资源获得新的开源授权，也不将 Felis 资源重新托管为 curryudon 公共镜像。

## 未發佈

- 帮助卡片：缩短预约烤猪与次日保护说明，使其适配单行省略显示；同时替换帮助图片字体，恢复 `1–5`、`1–9` 等范围表达中的 `–` 可见字形。
- 修正「吃群友」失敗後仍提示次日可能抽豬失敗，以及指令 Wiki／排障頁仍描述次日鎖天的過期文案；現在統一說明次日仍可正常抽取、僅可能強制抽到已解鎖的重複豬，並移除 JSON 後端不可達的舊鎖天回覆分支。
- 来源与资源隔离：撤下未经逐项 provenance 核实的 bundled 手写 EX 文案与外部 compatibility-floor 自动发布路径，EX 改用确定性安全基线，并以全新原创 roast-copy 包替换旧 bundled 文案。
- 随机烤群友：命中提示改为先单独标识指令发起人，再在随机转盘句内 @ 被烤对象，避免两个身份挤在消息开头而难以分辨。
- 来源与许可整改：补充 Felis / RollPig Plus 的 MIT 署名、项目沿革与功能／资源 provenance 审计，移除“独立维护”误导性描述，并将未核实再分发权的外部 compatibility-floor 资源纳入隔离与逐项核权流程。
- 烤猪料理卡：当历史小猪图片已退出当前资源源、文件缺失或无法解码时，不再留下大面积空白，改为显示明确的小猪占位与资源 ID，并写入诊断日志。

## v3.11.9

发布日期：2026-08-20

v3.11.9 是 v3.11.8 之后的渲染稳定性 patch，收录已合入 #176 的烤猪料理卡缺图降级，并继续保持现有 provenance-safe 公共源与 rights-aware 审核边界。

### 烤猪料理卡缺图降级

- 当历史小猪图片已退出当前资源源、文件缺失或无法解码时，料理卡不再留下大面积空白，改为用现有 palette/font 绘制本地矢量猪脸占位，并显示资源 ID。
- 图片解析或解码失败会记录包含 `pig_id` 与可用路径的 warning；fallback 不依赖新的外部图片资产。
- 新增 missing resolver 与 corrupt image 回归测试，确保仍输出有效的 800×870 PNG 且占位区域可见。

### 兼容性与公共源边界

- 可由 v3.11.8 直接升级；AstrBot 最低版本仍为 `>=4.24.2`。
- 不修改 70/20/10 烤猪 outcome、文案选择、资源优先级、玩法状态、SQLite schema、Resource Protocol v1 或 rights-v3 schema。
- 生产公共静态源继续保持 157 项 base-only；47 项隔离资源继续不发布；公共源审核通过仍不会自动发布。

## v3.11.8

发布日期：2026-08-20

v3.11.8 是 v3.11.7 之后的稳定性与玩法体验 patch，合入此前待处理的日报热重载修复与烤猪概率／随机数隔离改进，并继续保留 v3.11.7 建立的来源透明度、资源隔离和 rights-aware 公共源边界。

### 猪圈日报热重载稳定性

- 修复 AstrBot 热重载未完整执行旧插件 unload 时，旧 `_background_daily_report` asyncio scheduler 可能继续留在事件循环并额外发送日报的问题。
- 新实例在建立 scheduler 前只清理与当前 `plugin_data_dir` 完全相同数据命名空间中的旧日报 task，不影响其他 RollPig 数据目录或其他插件。
- 原有 `(draw_date, group_id)` 持久化 delivery claim 继续作为最终 at-most-once 边界；新增连续三次热重载与跨命名空间隔离回归测试。

### 烤猪概率与随机数隔离

- 普通烤群友、随机烤群友和预约结算继续共用同一 `RoastService` policy，结果权重由 60% 成功 / 30% 逃脱 / 10% 反噬调整为 70% / 20% / 10%。
- 命令文档、预约规则、玩法 Wiki 与互动演示同步更新为 70/20/10，避免文档与实际行为漂移。
- `DrawService` 默认随机源改为私有 `SystemRandom`，不再受同一 AstrBot 进程中其他插件调用 `random.seed(...)` 的影响；测试仍可显式注入 RNG。

### 来源与公共源边界

- 延续 v3.11.7 的 credit-first / provenance-safe 整改；不恢复当前 47 项隔离资源、旧 authored EX、旧 roast-copy 或 compatibility-floor 自动发布路径。
- 公共源投稿继续要求 rights-aware `submission_version: 3`；审核批准继续保持 `not_published`，正式发布仍必须经过独立 provenance-safe 流程。
- 本版本不改变当前生产 157 项 base-only 公共静态源，也不对所有历史内容作 blanket license／法律权属结论。

### 兼容性

- 可由 v3.11.7 直接升级。
- AstrBot 最低版本仍为 `>=4.24.2`。
- SQLite schema、Resource Protocol v1、插件身份与公共源 rights-v3 schema 不变。

## v3.11.7

发布日期：2026-08-20

v3.11.7 是公共猪源来源与再分发控制的安全整改版本。投稿客户端与管理员审核流程统一升级为 rights-aware envelope v3；内容审核、权利证据审核与正式公共源发布被明确拆分。本版本不会因为管理员批准投稿而自动生成资源版本或修改正式公共源。

### 公共源投稿与权利证据

- 基础小猪与 EX 投稿统一使用 `submission_version: 3`，投稿前必须填写作者／创作者、权利人、HTTPS 原始来源、署名文本以及明确的再分发依据。
- 权利依据分为 `original`、`license`、`explicit_permission`：许可证投稿必须提供许可证标识；明确授权投稿必须提供可核验的 HTTPS 授权证据 URL。
- 投稿者必须分别明确确认 `redistribution_authorized=true` 与真实性声明 `attestation=true`；缺少必要权利资料时客户端直接 fail-closed，不再发送旧 envelope v1/v2 投稿。
- 存在本地 EX 差分时，可在同一 rights-v3 表单中选择连同 EX 文案与图片一起进入同一次权利审核，不再使用旧的独立 envelope-v2 投稿流程。

### 审核与发布分离

- 管理员批准投稿必须显式确认 `rights_verified=true`，并留下至少 8 字的权利审核备注；缺少 rights-v3 证据的历史投稿禁止批准。
- “批准”只代表内容与权利资料通过审核，结果保持 `publication_status=not_published`，不会直接产生新的正式公共源版本。
- 管理面板不再把批准描述为“批准并发布”；正式发布必须另行进入 provenance-safe 流程，并重新验证 NOTICE／PROVENANCE／LICENSES 与资源内容后才能切换公开 `v1`。
- 原 EX 公共源独立页面改为迁移提示，防止继续使用旧 envelope-v2／批准即发布语义。

### 当前安全边界

- 本次客户端升级不会自行启动生产 review service，也不会自行解除生产 `/astrbot-rollpig/api/` 的 Web 层隔离。
- 已恢复的正式静态公共源继续使用当前 provenance-safe base-only 发布集；被隔离资源不会因为本次客户端更新重新进入公开源。
- 权利声明与审核记录用于来源审计和发布控制，不代表软件自动作出版权或法律权属判断。

### 兼容性

- AstrBot 最低版本仍为 `>=4.24.2`。
- Resource Protocol v1、游戏 SQLite 数据 schema、插件身份、命令集合、抽取／保底／烤猪等玩法规则均不变。
- 公共源投稿协议从旧投稿 envelope 升级到 rights-aware v3；不满足新权利资料要求的投稿应 fail-closed，而不是绕过核验。

## v3.11.6

发布日期：2026-08-19

v3.11.6 是在 v3.11.5 基础上的稳定整合 patch：完成公共猪源多层容灾与轻量安装包，修复管理面板布局，并让 EX 管理预览与真实聊天卡保持一致，同时收紧动态 DOM 渲染安全边界。本版不修改 SQLite schema、Resource Protocol、插件身份、命令集合或玩法概率。

### 公共猪源与同步可靠性

- 官方公共源按 `curryudon` 主源 → Vercel 已验证镜像 → 可选 GitHub 镜像顺序故障转移；完整性或协议校验失败才进入下一层，数字版 `resource_version` 不允许由备用源自动降级。
- 自定义／私人 manifest 保持明确的单一来源语义，不会在失败时偷偷切回公开源；最近一次已验证本地缓存与内置资源继续承担离线兜底。
- 全新安装的资源检查默认周期由 24 小时收敛为 6 小时；没有既有云资源版本时首次后台同步约 3–10 秒启动，健康缓存保持 30–120 秒启动抖动，损坏缓存仍走 5 秒快速修复。

### 轻量安装包

- Marketplace 与 GitHub Release 只在打包 staging 副本中保留 22 只可离线使用的 bootstrap 小猪及对应图片；仓库中的完整 99 只基础作者资源与 201 只手写 EX 作者数据保持不变。
- Marketplace 验证包已由此前约 15 MB 量级缩减到约 3.24 MB，同时保留字体、运行代码、离线基础能力以及联网后的完整公共图鉴同步。

### 管理面板与 EX 预览

- 修复桌面端「近 14 日猪圈脉搏」与右侧收藏率／热门小猪整列底部不齐；趋势图可吸收纵向空间而不设置固定 Dashboard 总高度，回访率圆环中心标签在响应式尺寸下保持在圆内。
- EX Base／EX 预览改由后端生产 `render_pig_image` 渲染链生成，与真实聊天发送卡的字体、排版、图片解析及 GIF 动画行为保持一致；Base ↔ EX 对比与 lightbox 继续保留。
- 未保存的 EX 编辑明确显示为待保存；主管理 modal 的动态小猪与 EX 字段改用 DOM `textContent`／`value` 构建，移除动态 `innerHTML` 数据注入面，并加入回归守门。

### 兼容性

- 可由 v3.11.5 直接升级。
- SQLite schema、Resource Protocol v1、插件身份、命令集合、抽取／保底／EX／烤猪规则均不变。
- AstrBot 最低版本仍为 `>=4.24.2`；本地 override 与 tombstone 继续高于公共资源层。

## v3.11.5

发布日期：2026-08-19

v3.11.5 是在 v3.11.4 基础上的展示与字体兼容修复版：统一插件运行时用户可见中文文案为简体，修复内置图片字体缺字，并移除管理面板 KPI 小卡的局部旋转光谱扇区。依仓库保守 SemVer 规则，本次不修改公开资料、配置或数据 schema，因此发布为 patch。

### 本版变更

- 内置烤猪文案、帮助卡、玩法速记、料理卡、历史收藏占位和管理页展示文案统一为简体中文；主字体不支持的“齁”替换为常用表达。
- AI 烤猪、公共源、本地猪与 EX 自定义名称／描述／完整文案在进入展示链时自动繁转简，同时保持 ID、配置键、路径、协议值和繁体命令别名不变。
- AI 烤猪最近文案去重 key 在哈希前统一做简体规范化，升级前后的繁简候选继续映射到同一去重记录。
- 新增展示文案 CI 守门：检查目标文案是否为简体，并逐字对照 `荆南麦圆体.otf` cmap 验证内置图片卡 CJK 字形覆盖；本次修复后纳入守门的静态内置展示文案缺字为 0。
- 移除数据总览五张 KPI 小卡的 `metric::before` 旋转 conic-gradient 光谱扇区及 `overviewSpectral` 动画，解决半透明斜切块只覆盖卡片局部、干扰数据阅读的问题；保留数据可视化、边框与轻量 hover 阴影。

### 兼容性

- 可由 v3.11.4 直接升级。
- 不修改 SQLite schema、Resource Protocol、插件身份、配置键、命令集合或玩法概率；AstrBot 最低版本仍为 `>=4.24.2`。
- `/今日小豬`、`/豬圈日報`、`/隨機烤群友` 等繁体命令 alias、`強行點火` 兼容口令、日报旧动作值及历史繁体数据匹配继续保留。

## v3.11.4

發佈日期：2026-08-18

v3.11.4 是在 v3.11.3 基礎上的穩定整合修復版：收斂烤豬可靠性、被吃後次日懲罰體驗、豬圈日報投遞與版面，以及管理面板 KPI 視覺。依倉庫保守 SemVer 規則，本次不改公開資料／配置 schema，發佈為 patch。

### 本版變更

- 修復 `/隨機烤群友` 候選未先排除豬身安全險、0 Charge 仍可先隨機 @ 群友；烤群友結果與隨機目標改用插件私有 `SystemRandom`，避免同進程其他插件 `random.seed()` 污染。
- 管理面板五張核心 KPI 補齊各自有語義的 mini visualization：總使用人數顯示今日活躍占累計用戶比例、累計抽取使用由永久總量錨定的近 14 日真實累計曲線、今日活躍保留每日活躍曲線、人均解鎖使用圖鑑尺度標尺、平均收藏率使用覆蓋率環形進度；不再靠同一組日活資料複製五條假趨勢。
- 修復烤豬料理卡在 EX 成長 mixin 與本地烤豬文案同時生效時的參數簽名漂移：`render_roast_image` 現在完整轉發 `local_copy`，避免 `/随机烤群友` 等流程因 `takes from 3 to 4 positional arguments but 5 were given` 生成圖片失敗。
- 調整「被吃掉」次日懲罰：不再概率抽豬失敗並鎖定整天；沿用原 20% 配置值改為概率強制抽到已解鎖的重複豬，舊版當日已鎖玩家升級後亦可立即恢復抽取。
- 修復豬圈日報在插件重載／投遞結果不確定時可能重複自動推送：同群同日新增跨實例原子 delivery claim，真正呼叫平台前同步持久化 `sending`；成功後持久化 `sent`，中斷／例外則標記 `uncertain` 並停止自動重試。只有 AstrBot 明確回報「未找到匹配平台」的確定未投遞才釋放 claim 允許稍後重試。
- 修正豬圈日報緊湊版面：KPI 提示文字不再被進度條壓住，五行搞事分布與補貨摘要完整留在面板內，空熱豬榜改為垂直置中，並保持 1200×1280 聊天安全尺寸。

### 相容性

- 可由 v3.11.3 直接升級；不修改 SQLite schema、Resource Protocol、插件身份或 AstrBot 最低版本。
- 既有配置鍵 `eaten_next_day_failure_percent` 保留，數值無需遷移；其玩家語義改為「被吃後次日強制重複豬概率」。
- 自動豬圈日報採 at-most-once 投遞：投遞結果不確定時寧可停止自動重試，管理員仍可手動 `/豬圈日報` 查看當日內容。

## v3.11.3

發佈日期：2026-08-17

v3.11.3 是管理面板安全更新器修復版。它修正「GitHub 已有有效穩定 Release，但更新面板誤報未找到可驗證 Release」的發布發現故障，不修改玩法或資料契約。

### 安全更新器

- 更新檢查改以 GitHub 官方 `releases/latest` 作為主通道，仍保留 Release collection 作相容 fallback；不再因 collection 回傳空列表或陳舊結果而把有效 Latest Release 判定為不存在。
- `latest` 回應仍必須通過既有嚴格驗證：stable SemVer、非 draft／prerelease、官方倉庫 Release URL、精確的 `astrbot_plugin_rollpig_plus-vX.Y.Z.zip` 名稱與官方下載 URL；安全邊界沒有放寬。
- GitHub 請求加入 `Cache-Control: no-cache`／`Pragma: no-cache`，降低中間快取讓更新檢查讀到過期 Release metadata 的風險。
- 當 latest 與列表兩個通道都不可用時，錯誤訊息會同時保留兩邊的失敗原因，方便定位網路／Release 資料問題。
- 新增回歸測試，直接覆蓋「latest 有效但 releases list 為空」這次實際故障型態，以及 latest 無效時的 fallback 行為。

### 升級提示

- v3.11.0–v3.11.2 的舊更新器本身依賴出問題的 Release collection；如果面板已出現「未找到可驗證的 RollPig Plus 穩定 Release」，需要先透過 AstrBot 插件市場／重新安裝或手動覆蓋 v3.11.3 完成一次引導升級。升到 v3.11.3 後，面板安全更新通道即可恢復正常。

### 相容性

- 可由 v3.11.0、v3.11.1、v3.11.2 直接升級。
- 不修改 SQLite schema、Resource Protocol、指令、配置、抽取／保底／EX／烤豬規則或管理 API。

## v3.11.2

發佈日期：2026-08-17

v3.11.2 是管理面板 KPI 與趨勢視覺修復版，集中修正總覽卡片的統計語義、資訊密度與 mini sparkline 失真，不修改插件玩法或資料契約。

### 管理面板 KPI

- 頂部 KPI 收斂為「總使用人數／累計抽取／今日活躍／人均解鎖／平均收藏率」五項；「小豬總數」移回圖鑑／覆蓋語境，不再佔用核心 KPI 槽位。
- 移除「當前快照 · 無歷史序列」等無信息量佔位，改為今日活躍占累計用戶比例、近 14 日抽取增量與日均、昨日比較、人均未探索空間與收藏覆蓋上下文。
- 「累計抽取」不再復用與「今日活躍」等形的日粒度序列，避免同一資料被包裝成兩條不同趨勢；只有真正有時間序列含義的今日活躍保留 mini sparkline。

### 趨勢視覺

- mini sparkline 由硬折線改為帶斜率限制的單調 cubic Hermite／Bézier 曲線，轉折處限制 tangent，避免尖角與平滑後越過真實資料極值。
- 加入最小語義視覺跨度，避免 15 → 16 這類小幅波動因局部 min/max 縮放被誇張成滿幅震盪。
- 保留固定 viewBox、non-scaling stroke、淡面積層與真實末端資料點，提升不同卡片寬度下的可讀性。

### 回歸驗證

- Browser harness 新增非空總覽資料，鎖定五張 KPI 卡、唯一真實 activity sparkline、cubic path、末端點與小波動不得填滿圖高。
- 修正舊 browser harness 的 bootstrap 版本假設與 responsive stylesheet 契約，避免測試因過時前提失真。

### 相容性

- 可由 v3.11.1 直接升級。
- 不修改 SQLite schema、Resource Protocol、指令、配置、抽取／保底／EX／烤豬規則或後端 analytics contract。

## v3.11.1

發佈日期：2026-08-17

v3.11.1 是展示與發布規範修復版，不修改插件運行邏輯。

### README / AstrBot Cloud 相容

- README Logo 由倉庫相對路徑改為 `raw.githubusercontent.com` 絕對地址，避免 AstrBot Cloud 等第三方 Markdown 渲染器無法解析 `./logo.png` 而顯示破圖。
- 首屏文檔導航改為 GitHub 絕對地址，避免第三方渲染器把相對 docs 連結解析到自己的站點路徑。
- 新增 Minecraft 主題動態訪問量組件，使用獨立 key `astrbot_plugin_rollpig_plus`。

### 發布規範

- `CONTRIBUTING.md` 明確版本策略：沒有重大變更時只發 patch（`+0.0.1`）；只有大型、向後兼容的里程碑能力才升 minor，破壞性兼容變更才升 major。

### 相容性

- 可由 v3.11.0 直接升級。
- 不修改 SQLite schema、Resource Protocol、指令、配置、抽取／EX／烤豬規則或管理 API。

## v3.11.0

發佈日期：2026-08-17

v3.11.0 聚焦管理面板資訊語義、EX 日常管理入口的一致性，以及公共豬源審核權限邊界；本版把 #147、#148、#149 收斂成一個經完整回歸後發布的穩定版本。

### 管理面板語義與視覺

- 重整總覽 KPI 與資訊密度：累計抽取不再偽裝成短期趨勢，今日活躍明確標示近 14 日範圍，熱門小豬改為緊湊排行榜並移除大片無效留白。
- AI 烤豬文案運行健康改為狀態驅動：區分未啟用、已啟用無樣本、生成中與已有完成樣本；生成中不進成功率分母，未啟用時不再顯示誤導性的 0%。
- 新增管理面板回歸契約，鎖定資源版本相容、AI 狀態語義、累計值呈現與排行榜版式。

### EX 成長管理入口一致性

- 修復 v3.10.0 第二階段 EX 預覽只落在獨立頁、主管理圖鑑內嵌 modal 仍停留舊版的整合漂移。
- 主管理 modal 現在同步顯示實際生效圖片、名稱、EX 等級、短描述、完整文案與來源，並支援未儲存本地圖片即時預覽與移除圖片後的繼承／基礎圖回退模擬。
- 新增 Base ↔ EX 圖文對比、lazy-load Base 圖、頁內 lightbox 放大與手機端堆疊；雙入口 parity contract 防止日後再次只更新其中一頁。

### 公共豬源審核權限

- 公共豬源 review proxy routes 只在本機存在有效 maintainer token 時註冊；普通安裝者不再暴露審核路由。
- `overview` 只返回布林 capability，不回傳 token；運行中移除 token 會立即撤銷前端審核能力。
- 審核面板、modal、備註與批准／拒絕操作改為 capability 為真時才動態掛載；遠端 Bearer token 驗證繼續作為第二道授權邊界。

### 相容性

- 可由 v3.10.0 直接升級。
- 不修改 SQLite schema、Resource Protocol、抽豬概率、保底、EX 等級與稀疏繼承規則。
- 公共豬源審核 route registration 屬啟動期能力：運行中新增 maintainer token 後需重新啟動插件；移除 token 則 capability 立即失效。

### 本版整合工作

- #147 — 管理面板語義、AI Runtime 狀態與熱門榜大翻修。
- #148 — 主管理 EX modal 與 v3.10 Stage 2 預覽對齊。
- #149 — 公共豬源審核 capability / route / DOM 三層收緊。

### 驗證

- #147 合入前 CI、Marketplace Package、AstrBot Market Smoke 全部通過。
- #148、#149 各自來源分支 CI 與 Marketplace Package 均通過；正式 Release PR 會在整合樹上重新執行完整 pytest、pre-commit、Marketplace Package 與 AstrBot Market Smoke。

## v3.10.0

發佈日期：2026-08-17

v3.10.0 是一次功能整合版本：收斂目前仍有獨立價值的待合工作，補齊動畫 GIF、EX 預覽、AI 小豬工坊與群聊回覆識別，同時把今天已完成但尚未正式版本化的文案、管理分析與維護門禁一起納入穩定版。

### 動畫 GIF 與公共豬源

- PigHub／手動上傳的真正動畫 GIF 不再被單幀轉成 PNG；抽到動畫小豬時會逐幀合成完整 800×800 小豬卡並保留幀時長與循環設定。
- EX 差分支援 `.gif`，本地保存、公共豬源投稿、審核預覽與發布均按實際格式保留動畫；管理縮圖仍使用輕量靜態 PNG。
- 動畫加入 10 MiB、25 MP、8192 邊長、240 幀與 60 秒等安全上限；公共豬源服務端同步升級為 2.2.0。

### EX 成長管理

- 「實際生效預覽」同步顯示最終生效圖片與來源，支援未儲存本地圖片即時預覽，以及移除圖片後對稀疏繼承／公共 EX／基礎圖回退結果的模擬。
- 新增 Base ↔ EX 圖文對比、圖片放大與更清楚的 chat-card 視覺，不改 EX 等級計算與既有稀疏繼承語義。

### AI 小豬工坊

- Pig Manager 新增 AI 小豬工坊：文字策劃復用 AstrBot 當前 AI Provider，可批量產生名稱、ID、視覺特徵、短描述與完整圖鑑文案。
- 可選現有圖鑑小豬作生圖參考，完整圖片先保存在服務端短期草稿，支援按反饋重畫；只有管理員確認後才寫入本地圖鑑。
- 生图 API Key 不回传浏览器；Base URL 预设要求 HTTPS，远端生成图只允许与生图 API 同 hostname 的 HTTPS 地址，避免任意 URL 下载。

### 群聊与烤猪体验

- 所有 RollPig 群聊指令的第一条机器人回复在最上方单独标示 `@指令发起者`；原有玩法目标 `@` 继续保留，私聊不新增多余提及。
- 重做烤猪文案系统：内置 32 菜名 × 79 条猪言猪语正文，共 2,528 组；同群最近 24 次文案组合防重复，并支持 Resource Protocol v1 可选 `roast_copy` 同步。
- AI 烤猪文案改为猪圈世界观 prompt：每只猪每天仍只调用模型一次，但一次生成最多 4 条候选，七日池最多 28 条，兼容旧单条缓存并加入近期防重复。
- `/猪猪帮助` 补充 `@` 指令输入提示，提醒玩家手动输入指令后再选择群友，避免直接复制「指令 + @」失去结构化 At。

### 管理、文档与工程品质

- 修正管理面板 KPI 迷你图数据语义：累计抽取改为真实近 14 日每日抽取；没有历史序列的快照指标不再展示伪趋势。
- README 首屏加入 AI 生成代码风险提示，明确建议重要环境部署前自行审查与测试。
- PR／Release 维护门禁要求 Changelog 与 Wiki-Impact；canonical 指令或配置 schema 改动必须同步 Wiki。
- CI 移除重复／低价值检查，保留 Python 3.12、Marketplace Package、AstrBot 官方加载、Changelog/Wiki 与 pre-commit 等实质发布门禁。

### 本版整合工作

- #135 — 群聊指令首条回复标示发起者。
- #137 — CI 去重与发布门禁收敛。
- #140 — AI 小猪工坊。
- #142 — 动画 GIF 小猪端到端支持。
- #143 — EX 实际生效图片预览。
- #144 — EX Base ↔ EX 对比、放大与第二阶段预览。
- 公共猪源服务 #10 — GIF／EX GIF 服务端端到端支持。

### 兼容性

- 可由 v3.9.1 直接升级。
- SQLite schema 不变。
- Resource Protocol 维持 v1；公共猪源 submission envelope 维持 v2。
- 抽猪概率、新猪保底、跨日疲劳保底、EX 等级与 Roast Charge 规则不变。

### 验证

- 整合树全量 pytest：453 passed。
- pre-commit：全部通过。
- 各来源 PR 的 Python／Marketplace／AstrBot smoke 已逐一审查；最终 Release PR 再跑合并后正式门禁。
## v3.9.1 (2026-08-17)

v3.9.1 是 v3.9.0 的维护版本，集中修正 **管理面板迷你趋势图失真** 与 **动态帮助卡繁简混排／字体问题**，不改游戏规则、数据格式或资源协议。

## 管理面板

- 修正顶部 KPI mini sparkline 仍以 0 作固定 Y 轴基线，令全部为正值的时间序列被压扁；现在按实际局部 min/max 自适应缩放，并为平坦／非平坦数据加入安全留白。
- sparkline 几何统一由实际 `width / height / padding` 计算，移除硬编码 area baseline；SVG stroke 使用 `non-scaling-stroke`，卡片尺寸变化时不再把线宽一起拉伸。
- 这些变更只影响管理页视觉呈现，不修改任何统计值或分析口径。

## 动态帮助卡

- `/猪猪帮助` 生成的快速指令卡固定使用 **简体中文 `zh-CN`**：标题、分类、说明、页尾与显示命令全部统一为简体。
- 显示命令改用已注册的简体 canonical 命令，例如 `/今日小猪`、`/我的猪圈`、`/猪圈日报`、`/烤箱补货`。
- renderer 不再优先使用 `font_traditional`，帮助卡统一使用标准中文 `font_bold`，避免繁体专用字体造成缺字、错字形或繁简混排。
- 帮助图片 cache version 升级，旧的繁体 bitmap 不会继续命中。
- 繁体指令 alias 仍完整保留；玩家仍可输入 `/今日小豬`、`/豬豬幫助` 等旧指令，只是不再显示于生成图片。

## Changelog 维护

- 修复 `CHANGELOG.md` 在 v3.6.5 之后的历史断档：重新以已发布的 `.github/release-v*.md` 为来源回填 v3.7.0～v3.9.0 正式版本记录。
- 「未发布」区重新清空，避免已经上线的功能长期留在未发布章节造成版本语义错乱。

## 本版合入 PR

- #131 — 修正管理面板 KPI mini sparkline 的局部缩放与 SVG 几何。
- #132 — 快速指令帮助卡固定简体中文并移除繁体字体依赖。

## 兼容性

可由 v3.9.0 直接升级。本版不改变：

- SQLite schema 与永久猪籍 authority
- Resource Protocol v1
- 抽猪概率、新猪保底与跨日疲劳保底
- EX 等级计算
- Roast Charge、60/30/10、`/添柴` 与预约结算规则

## 验证

- Python 3.10 / 3.12 全量 CI
- Marketplace Package
- AstrBot Market Smoke
- 管理趋势 UI contract
- 动态帮助、字体、cache 与 Wiki bridge contract

## v3.9.0 (2026-08-16)

v3.9.0 聚焦在 **管理体验、聊天可读性、Wiki 与视觉一致性**。本版把原本已存在但分散的 EX 能力真正接回主管理页，同时重做动态帮助、猪圈日报与管理分析视觉。

### 管理页：EX 1–5 正式回到主流程

- 每张小猪卡与既有小猪编辑流程都可直接进入 **EX Lv.1–5 管理**。
- 可分级编辑短描述、完整文案、差分图片，支持图片上传／移除／预览与单层重设。
- 保留既有稀疏继承规则，直接显示每层「实际生效」结果与来源。
- 公共猪源详情不再只有关闭按钮：新增目前实例 EX 摘要、管理本地 EX、在本地图鉴定位。
- 完全复用既有 `ExAdminMixin` / `ex/variants` API，没有新增第二套 EX 存储格式，也不改 EX 等级或玩法语义。

### 聊天图片与字体

- `/猪猪帮助` 改成更短的双栏瀑布流快速指令卡，移除大量卡中卡与无效留白；最坏完整功能组合也受高度回归门槛保护。
- 帮助卡完整保留繁体中文字体路径，避免罕见繁体字退回缺字／错字形。
- 指令描述收敛成一句话，完整机制与数值交由 Wiki 说明。
- `猪圈日报` 重做为更紧凑的视觉战报，改善信息层级与聊天端扫读效率。
- 图鉴缩图背景与管理面板视觉对齐，减少透明素材在不同页面的底色落差。

### 管理分析

- 近 14 日猪圈脉搏由硬折线改为不改动真实数据点的平滑 Bézier 曲线。
- 修正趋势面板被右栏强制拉高造成的大面积空白。
- 新增峰值活跃、日均活跃、14 日抽取总数、14 日新解锁总数摘要带。

### Wiki

- 玩家首页、快速开始、玩法与故障排查进一步去重，降低相同规则散落多页造成的维护漂移。
- 修复 AstrBot Plugin Page sandbox 内 Wiki 链接无法正常开启的问题。
- Wiki 固定为 Slate 深色主题，移除容易造成视觉不一致的亮色切换路径。

### 本版合入 PR

- #121 — 繁体帮助卡字体完整性
- #122 — 玩家 Wiki 去重与简化
- #123 — 管理页 Wiki sandbox 导航
- #124 — 紧凑动态帮助卡
- #125 — 14 日趋势平滑与摘要
- #126 — 图鉴缩图背景一致性
- #127 — 主管理页 EX 1–5 / 公共猪源操作整合
- #128 — 紧凑视觉猪圈日报
- #129 — Wiki 深色 Slate 单主题

### 兼容性

可由 v3.8.1 直接升级。本版不改变：

- SQLite schema 与永久猪籍 authority
- Resource Protocol v1
- 抽猪概率、新猪保底与跨日疲劳保底
- EX 等级计算
- Roast Charge、60/30/10、`/添柴` 与预约结算规则

### 验证

本批 PR 在合入过程中除各自 CI 外，针对重叠区域额外做了组合回归：

- 繁体字体 + 紧凑帮助卡共同契约
- Wiki sandbox 导航 + 14 日趋势 + EX 主管理页共同契约
- EX integration JavaScript `node --check`
- Python 3.10 / 3.12 CI、Marketplace Package、AstrBot Market Smoke 由 release PR 再做最终整体验证。

## v3.8.1 (2026-08-16)

这是一个针对 **AstrBot 后台插件首页／升级残留** 的修复版本。

### 修复内容

- 修复从旧版本以 overlay/overwrite 方式升级后，`pages/ex-manager/`、`pages/ex-public-source/` 可能残留，导致 AstrBot 仍把 **EX 成长管理** 当成插件主管理页的问题。
- 新增启动时 installation migration：确认新版替代页存在后，自动清理 RollPig 明确拥有的 legacy Plugin Page。
- 若旧 Page 目录因权限或文件占用无法完整删除，会退而停用其 `index.html`，避免 AstrBot 继续 discover 旧入口。
- 替代页缺失时不删旧页；未知／用户自建 Page 不会被 migration 触碰。
- 新增真实 overlay-upgrade 回归测试，直接验证旧 `ex-manager` 残留 → migration → `pig-manager` 恢复为第一个 Plugin Page 的完整流程。
- 将 installation migration module 纳入 CI 显式 compile gate。

### 升级后预期

AstrBot Plugin Page 应只发现：

1. `pig-manager` — 猪圈管理（默认首页）
2. `pig-manager-ex` — EX 成长管理
3. `pig-manager-ex-public-source` — EX 公共源

已受旧版残留影响的安装，在加载 v3.8.1 后会自动自愈，不需要手动删除旧 Page 目录。

### 兼容性

可由 v3.8.0 直接升级。本版不修改：

- SQLite schema
- Resource Protocol v1
- 抽猪概率／新猪保底
- EX 等级计算与官方 EX 文案
- Roast Charge／`/添柴` 数值与结算
- 永久猪籍 authority

### 验证

修复 PR #119 已通过：

- CI（Python 3.10 / 3.12）
- Marketplace Package
- AstrBot Market Smoke
- 官方 AstrBot plugin load worker

## v3.8.0 (2026-08-15)

> **这次不是再补一个小 hotfix，而是把「养熟、添柴、说猪话、看 Wiki」四条线一起收成正式版本。**
>
> v3.8.0 集中完成官方 EX 内容、烤箱／预约安全、contextual `/添柴`、玩家文案与文档统一，以及 Wiki 真正按内容宽度响应的版面系统。

### ⭐ 201 / 201 官方猪全部手写 EX1–EX5

官方有效图鉴现在完整覆盖 **201 只小猪 × 5 个 EX 等级**：

- 每只都有明确手写的 EX Lv.1–5；
- 五级 `description` 各不相同；
- 五级 `analysis` 各不相同；
- compatibility 恢复的旧官方猪也包含在正式 EX corpus；
- Resource Source 发布前会验证 handcrafted EX ID 与最终官方猪 ID 完全一致。

通用 EX 生成器仍保留，但只作本地／非官方／未完成内容的安全兜底；正式官方猪不能靠模板混过 release gate。

EX 仍是展示与收藏成长层：**不修改猪 ID、抽取概率、保底、60/30/10 或玩法资格。**

### 🪵 `/添柴` 现在真的只要记一条命令

`/添柴` 成为玩家正式入口，并按群聊上下文自己判断你在给哪口锅送柴：

- `/添柴 @目标` → 明确加入该目标的待结算预约；
- 有烤箱补货轮次时，裸 `/添柴` → 支持补货；
- 没有补货且只有一张待结算预约时，裸 `/添柴` → 自动加入那张预约；
- 同时有多张预约时 → 要求 `@目标`，不替玩家乱猜；
- 主厨建立预约时已算第一位参与者，不能再把自己重复塞进柴火簿；
- 已 resolved 的预约保持终态，不会被竞态请求重新打开。

旧 `/添煤`、`/加煤`、`/烤箱添煤`、`/烤箱添柴` 只保留为向后兼容入口，不再出现在玩家帮助与主文档中。

### 🔥 烤箱补货与预约结算再加一道保险

这版把群体补货和预约的异常／竞态边界一起收紧：

- 补货依赖父级烤群友玩法开关；
- 单轮补货加入 TTL，默认 120 分钟，超时僵尸轮会关闭；
- 补货进入结算后若遇到 storage error，采 fail-closed 封账，避免部分玩家已拿到 Charge 后重试再次发放；
- 若进程在 `completing` 阶段中断，重启后同样按已进入结算处理；
- 建立／添柴与抽猪触发共用 reservation lock，锁内再次确认目标状态；
- 60% 成功 / 30% 逃脱 / 10% 反噬没有改动。

### 🐷 整个插件开始说同一种「猪话」

玩家高频文案、动态 `/猪猪帮助`、预约／补货提示、错误 fallback、永久猪圈和官方基础猪文案做了一次完整 Piggy Voice 收口。

其中 48 只过去偏「人格测评模板」的官方基础猪重新手写 `analysis`，从抽象形容词改成具体角色设定、群聊行为和最后补一刀的节奏。

`/我的猪圈` 也不再像后台数据表：

- `我的猪圈 · 猪籍档案`
- `现役入圈`
- `老猪留档`
- `最常返场`
- `老猪籍`
- `还没拱进你家`

但收藏 authority、历史保留、排序、EX、总抽取次数与分页规则完全不变。

群聊 mention 排版也统一为 `@某人` 单独一行，再从下一行开始正文，长提示更容易扫读。

### 📚 README / Wiki / 指令与配置文档一起更新

这次文档不是「功能改了顺手补两句」，而是完整审查玩家入口与维护手册。实际修掉的过期信息包括：

- 玩家页仍主推 `/添煤`；
- `COMMANDS.md` 还把实现固定写成 v3.6.3；
- 8 小时仍被描述成整个人的单一 cooldown，而不是每缺一格 Charge 的恢复时间；
- `CONFIGURATION.md` 漏掉 `group_roast_max_charges`；
- 预约配置 hint 没有主推 `/添柴 @目标`。

新增文案／文档 contract tests，之后这些语义再漂回去会直接让 CI 变红。

### 🖥️ Wiki 响应式改成看「真正内容宽度」

v3.7.3 先修了手机 Hero 被切掉；v3.8.0 进一步把整套自制 Wiki UI 改成真正的 responsive system。

MkDocs Material 的左右 navigation / TOC 会先吃掉桌面宽度，所以现在元件不只看 viewport，而是用 content container queries 根据 `.md-content__inner` 真正拿到的宽度变形。

同时修正 `md_in_html` 在最终 HTML 中自动加入 `<p>` wrapper 后，原先 direct-child flex/grid 规则失效的问题，涵盖 Hero、HUD、按钮、徽章、跑马灯、Charge、OLD → NEW、60/30/10、creator pipeline、triage 等自制元件。

首页桌面版会隐藏文档 sidebar、让 landing page 有更多空间；**手机版仍保留 Material navigation drawer**。中等宽度的顶部 tabs 改为安全横向 scroll，不再硬挤标签。

### 🧪 发版验证

功能 PR 合并前已分别通过：

- Python 3.10 / 3.12 full pytest
- pre-commit
- Piggy Wiki strict build + rendered Markdown contract
- Marketplace Package
- AstrBot Market Smoke
- 当前官方 AstrBot plugin load worker
- AstrBot Resource Source（涉及 EX／官方资源的变更）

本发版 PR 会再基于所有 PR 已合并后的最新 `main` 跑一次完整门槛；合并后由既有 Release workflow 自动建立 `v3.8.0` tag、ZIP 与 `SHA256SUMS`。

### ⬆️ 升级

可由 **v3.7.3 直接升级到 v3.8.0**。

本版不修改：

- SQLite schema
- Resource Protocol v1
- 新猪保底算法与概率上限
- 60 / 30 / 10 烤猪 outcome
- Roast Charge 默认容量与恢复数值
- 永久收藏 authority / EX 等级计算公式

正常透过 AstrBot 插件更新或 GitHub Release ZIP 升级即可。

## v3.7.3 (2026-08-15)

> **这次不加新玩法，专心把两个明显的界面回归收干净。**
>
> v3.7.3 是 v3.7.2 的稳定性 hotfix：修回 AstrBot 主管理入口，并修正 Wiki v3 首页在手机上的裁切问题。

### 🐷 猪圈管理重新成为默认入口

新增 EX 独立 Plugin Pages 后，AstrBot 会按 Page 目录名排序，侧栏又直接打开第一个 Page；原本的 `ex-manager` 因此排在 `pig-manager` 前面，造成点击「今日小猪」时先进 EX 成长管理，看起来像原本的数据总览、猪猪图鉴与本地资源整页消失。

本版已把入口顺序重新固定为：

1. `pig-manager` — 猪圈管理（默认）
2. `pig-manager-ex` — EX 成长管理
3. `pig-manager-ex-public-source` — EX 公共源

原主管理页的数据统计、猪猪管理、本地／云端资源与既有管理功能都没有被删除；这次只是修正 AstrBot 的默认 Page 选择结果。

同时加入回归测试，之后再新增 Plugin Page 时，如果 `pig-manager` 被挤出第一位，CI 会直接失败。

> 如果你曾经手动收藏旧的 `ex-manager` / `ex-public-source` Plugin Page 深链，升级后请改用新的 Page 名称；从 AstrBot 正常 UI 进入不需要额外操作。

### 📱 Wiki v3 手机版不再被切掉右半边

修正首页 Hero 被 intrinsic / min-content 宽度反向撑开、再被 `overflow: hidden` 裁掉的问题。

本版新增最后加载的 mobile containment layer，并针对 900 / 600 / 430px 断点收敛：

- Hero grid 改用 `minmax(0, 1fr)`；
- Hero 内容、console、CTA、徽章与 live strip 补上安全的 `min-width: 0` / `max-width: 100%`；
- kicker、CTA、badge 可以正常换行；
- 小屏幕 Hero padding、标题字号与 CTA 重新收敛；
- 430px 以下 HUD stats 收成单栏。

桌面版 Wiki v3 的原视觉与动画保留不变。

### 🧪 发版验证

合并前的完整整合 revision 已通过：

- Python 3.10 / 3.12 CI
- Piggy Wiki strict build / rendered checks
- Marketplace Package
- AstrBot Market Smoke
- 当前官方 AstrBot plugin load worker

发版 PR 会再对最新 `main` 执行完整门槛；合并后由既有 Release workflow 自动建立 `v3.7.3` tag、ZIP 与 `SHA256SUMS`。

### ⬆️ 升级

可由 **v3.7.2 直接升级**。

本版不修改：

- SQLite schema
- 永久收藏 / EX 成长算法
- 新猪保底概率
- 60 / 30 / 10 烤猪概率
- Roast Charge 核心规则
- Resource Protocol 公开契约

正常透过 AstrBot 插件更新或 GitHub Release ZIP 升级即可。

## v3.7.2 (2026-08-15)

> **Wiki 不再只是站在门外。这次它真的搬进插件里了。**
>
> v3.7.2 是一个「把整座猪圈接起来」的体验收口版：插件帮助、管理面板、玩家 Wiki、手机响应式与公共猪源运维边界全部重新接好。玩法概率没偷偷动，猪还是那些猪——只是现在更知道该去哪里找答案了。

### 📖 插件 ↔ Wiki：正式接线

`/猪猪帮助` 不再只是一张孤零零的帮助图：

- 帮助图底部新增 **今日小猪 Wiki** CTA；
- 发图后再补一条可直接点击的 Wiki URL；
- 帮助图生成失败时，直接给排障入口；
- 帮助缓存版本升级，旧缓存不会继续把新入口藏起来。

管理面板右上角也新增 `📚 文档`：

- 📖 玩家 Wiki
- ⚙️ 管理员手册
- 🎨 投稿指南

真正需要排查时，插件会开始把你送到**对的那一页**：

- 猪源同步失败 / 403 / 校验 / timeout → 直接进「猪源同步排障」；
- 管理页深度分析 / Plugin Page Bridge 加载失败 → 直接进「管理页定向排障」。

两个深链使用固定 anchor，Wiki CI 会检查最终 HTML 真的存在对应位置，避免某天改个中文标题就把插件里的链接炸掉。

一句话：

> **不要再把所有错误都丢给 README。**

### 🎮 Wiki v3：群友先玩，管理员靠后

这一轮重新校准了 Wiki 的主要读者：**普通群友。**

原本的「5 分钟开始养猪」改成 **「30 秒开始养猪」**，把不属于玩家 onboarding 的「安装插件」「重启 AstrBot」拿掉。

现在第一次进 Wiki，只需要知道三件事：

1. `/今日小猪`
2. `/我的猪圈`
3. `/烤群友`、补货、添煤、日报——然后事情开始失控。

安装、迁移、资源同步、备份与运维全部退回管理员区，不再堵在群友第一步前面。

首页也进一步「猪化」：

- Pigsty LIVE HUD
- 玩法跑马灯
- 霓虹 / 玻璃层次
- Roast Charge 能量视觉
- 更明显的卡片 hover depth 与按钮扫光
- OLD → NEW 改成非强制等高的进化结构
- 宽屏 Hero 中文标题改按容器宽度缩放，不再在有右侧 TOC 时被撑成接近直排

手机响应式与 `prefers-reduced-motion` 仍保留，不拿可读性换特效。

### 📱 管理面板：手机上终于不互相打架

管理面板补了一轮平板 / 手机 / 小屏手机响应式收口：

- `900px`：topbar、品牌区与导航可以安全收缩，不再把整页撑出横向滚动；
- `680px`：储存、更新、公共源与 Dialog 操作组重新堆叠，长标签不再挤成奇怪的按钮墙；
- `440px`：图鉴 / PigHub 网格收成单栏，Dialog 与 toast 留在动态视口内；
- coarse-pointer 装置补足 44px 触控目标。

同时新增 browser regression contract，把 900 / 680 / 440 三个断点锁进测试。

### 🔒 公共猪源：插件客户端公开，服务端运维退到私有

本版也完成公共猪源的仓库边界收口。

公开插件仓库**继续保留**：

- 插件侧投稿 / 审核整合与管理 UI；
- Resource Protocol v1 公开契约与资源 builder；
- EX schema / manifest 行为；
- 兼容性基线逻辑与客户端回归测试。

但公共源的**服务端实现、systemd / Nginx 生产配置、线上迁移命令与服务端审核回归**不再留在目前公开插件 tree 中，由服务端运维侧独立维护。

这不是 Git 历史重写；以前已公开的 commit 仍然存在。这次只是把「插件应该公开的协议 / 客户端」和「服务端生产运维面」重新划清边界。

对普通插件使用者没有额外操作要求。

### 🧪 发版门槛

本轮各功能合并前已分别通过：

- Python 3.10 / 3.12 full pytest
- pre-commit
- Marketplace Package
- Piggy Wiki `mkdocs build --strict --clean`
- Wiki rendered HTML / stable deep-link gate
- AstrBot Resource Source（涉及资源边界的变更）
- AstrBot Market Smoke
- 当前官方 AstrBot plugin load worker

v3.7.2 发版 PR 会再对**完整最新 main**跑一轮正式验证，再由仓库既有 Release workflow 自动产出 tag、ZIP 与 `SHA256SUMS`。

### ⬆️ 升级

可由 **v3.7.1 直接升级**。

本版不修改：

- SQLite schema
- 永久收藏 / EX 成长算法
- 新猪保底概率
- 60 / 30 / 10 烤猪概率
- Roast Charge 核心规则
- Resource Protocol 公开契约

正常透过 AstrBot 插件更新或 GitHub Release ZIP 升级即可。

---

**猪圈没有突然多一套数值。**

只是现在：

> 你抽完猪知道去哪看玩法；出错知道去哪排查；管理员拿手机也不必和按钮搏斗；而服务端的后厨门，也终于不再敞在公共插件仓库里。

## v3.7.1 (2026-08-15)

> **猪圈开始有 Wiki 了。**
>
> v3.7.1 是 v3.7.0 之后的稳定性、文档与体验收口版：不重新改玩法概率，而是把繁简指令兼容、管理面板统计准确性，以及两轮「今日小猪 Wiki」正式纳入稳定发布。

### 📖 今日小猪 Wiki 正式入圈

本版加入完整的 MkDocs Material Wiki，文档源直接和插件代码放在同一个仓库、同一套 PR / CI 里维护，不再另外养一份容易漂移的 Wiki。

第一、第二轮 Wiki 已包含：

- 🐷 5 分钟开始养猪
- 🎮 玩家玩法总览
- 📚 永久图鉴、新猪保底、跨日疲劳保底
- 🧪 可互动的 Pity Lab 保底实验室
- ⭐ EX Lv.1–5 成长
- 🔥 60 / 30 / 10 烤群友 outcome 与次日保护
- 🎰 前端假烤架演示
- ⚡ Roast Charge 与群体烤箱补货
- 📰 猪圈日报
- 🎨 做一只自己的小猪／公共猪源投稿
- 🧯 症状式故障排查
- 📖 指令、配置、资源、架构与维护 Reference

Wiki 有繁／简中文搜索词库、Light / Night 猪圈主题、卡片 3D hover、Charge 动效、EX shimmer、首页小猪粒子效果，以及 `prefers-reduced-motion` / 手机降级。

**特效可以骚，正文不能看不清。**

### 🎨 做猪不需要先当运维

创作者指南重新把最简单的真实路线放到第一位：

> **群内 @ 管理员 → 把图片、名称、描述、文案交给他 → 管理员代为新增、试抽、修改、投稿。**

普通群友不需要自己部署 AstrBot、不需要有服务器，也不需要先学 manifest。

只有本来就在管理 RollPig 实例、或想长期维护大量小猪／私人猪源的进阶创作者，才需要使用管理面板、本地 override 与 manifest 流程。

### 🈶 繁简指令与 AstrBot dispatch 修复

包含 v3.7.0 发布后合入的指令兼容修复：

- 新增 `/猪圈日报状态`、`/猪圈日报开启`、`/猪圈日报关闭` compact 指令；
- 同时保留 `/猪圈日报 状态|开启|关闭` 带空格形式；
- 简体、繁体与常见混合字形 alias 一起验证；
- adapter 只转发到既有 Daily Report handler，不复制权限或状态逻辑；
- AstrBot Market Smoke 使用当前官方 `CommandFilter` 验证每个合法输入只命中正确 handler，防止前缀误吞或重复 dispatch。

### 📊 管理面板统计口径校准

包含 v3.7.0 后合入的 Dashboard Accuracy & Motion：

- Overview / Analytics 采 claim-aware logical-user 统计；
- 已证明属于同一人的 legacy fragment 不再重复计用户、抽取与收藏；
- 重叠收藏次数采 `MAX`，避免 migration copy 虚增 EX；
- 移除用推导值拼出的假 sparkline，只保留可证明的历史序列或明确标示的 snapshot；
- AI 文案成功率改为 `ready / (ready + failed)`，不把仍在 generating 的请求当失败；
- 管理面板加入新的 telemetry、hover、halo、trend bar 等沉浸式动效，同样尊重 reduced-motion。

### 🐷 Wiki 文案与规则校准

建 Wiki 的过程也顺手抓出并修正了几个旧文档漂移：

- `ROAST-CHARGES.md` 不再把已经上线的 `/烤箱补货` / `/添煤` 写成「未来 Phase 3B」；
- 补货文档补齐 2 人群特殊门槛、30% / 最少 3 人 / 基础上限 8、每成功一轮 +2、每日默认 2 轮、每人最多 +1 Charge 等现行规则；
- 保底页明确说明百分比是「初始候选重复时的条件式重抽率」，不是无条件新猪概率；
- 60/30/10 页明确区分真正 victim、逃脱、反噬与次日保护；
- 故障排查强调先判断玩法阻挡／配置／资源／storage，再碰数据库。

### 🧪 验证

Wiki 两轮合并前均经：

- `mkdocs build --strict --clean`
- Python 3.10 / 3.12 full pytest
- pre-commit
- Marketplace Package
- AstrBot Market Smoke / official plugin load worker

v3.7.1 发版 PR 会再次对完整最新 `main` 跑同一组发布门槛。

### 升级

可由 **v3.7.0 直接升级**。

本版不修改：

- SQLite schema
- 永久收藏／EX 算法
- 新猪保底概率
- 60 / 30 / 10 烤猪概率
- Resource Protocol

正常透过 AstrBot 插件更新或 GitHub Release ZIP 升级即可。

## v3.7.0 (2026-08-15)

v3.7.0 是 v3.6.5 之后的玩法与架构大型更新。本版把「烤群友」从单一硬冷却升级成可储存 Charge，加入群体协作烤箱补货，同时重做动态帮助、渲染与读取缓存、状态持久化，以及公共猪源审核／浏览体验。

### 🔥 Phase 3：烤箱 Charge

- 普通 `/烤群友` 与建立预约改为按「用户 × 群组」消耗烤箱能量，默认 **2 格**。
- 每格沿用原 `group_roast_cooldown_hours` 作自然恢复周期；`group_roast_max_charges` 可配置 1–5 格。
- SQLite / JSON 共用同一 token-bucket policy，避免两套后端出现玩法差异。
- 旧版 `roast_cooldowns.last_used_at` 以 lazy migration 转成 charge state：仍在旧冷却中的玩家视为已消耗一格，不会因升级被重置，也不会被双重惩罚。
- 预约第一位主厨消耗一格；后续添柴与目标日后触发不重复消耗。
- 后门 bypass、烤猪资格判定与既有 **60 / 30 / 10** outcome policy 保持不变。

### ⛽ 群体烤箱补货

- 新增群体协作补货玩法，让当日活跃群友共同恢复烤箱能源，而不是单纯等待硬冷却。
- 补货按群组／自然日保存状态，支持参与者去重、进度、成功轮次与每日限制。
- 成功补货只恢复有限 Charge，且受最大能量上限约束，不会形成无限烤猪。
- 补货事件接入 Gameplay Event 与猪圈日报，可追踪补货成功与添煤参与。
- SQLite primary write path、JSON 兼容路径与初始化／恢复流程均加入回归测试。

### 🧭 动态帮助系统

- `/猪猪帮助` 升级为依目前功能、配置与指令面动态生成的帮助内容。
- 帮助渲染拆到独立 renderer / feature boundary，避免把命令注册、业务逻辑与 PIL 绘图重新混在一起。
- 新增帮助卡与文字 fallback 测试，确保新功能加入后不再依赖手动维护一张容易过期的静态说明。

### ⚡ 渲染、读取与持久化性能

- 新增猪卡渲染缓存与 renderer performance contracts，降低重复图片合成开销。
- 加入渲染 backpressure，避免高并发下无限制堆积昂贵的 PIL 任务。
- Resource read path 增加缓存，减少相同 catalog / image resolution 的重复查找。
- 新增集中式 state persistence 边界，降低高频玩法状态写入造成的重复 I/O。
- 相关 cache / persistence 均有失效与回归测试，数据权威仍由现有 storage/domain write 边界控制。

### 🐷 公共猪源审核与正式源浏览

- 修复 AstrBot Plugin Page sandbox 下，批准／拒绝依赖原生 `window.confirm` / `window.prompt` 而可能完全无反应的问题；改为页内审核对话框与明确二次确认。
- 公共猪源管理新增正式源图鉴浏览器：支持搜索 ID、名称、描述／完整文案、分页、图片预览与完整数据查看。
- 疑似重复提示可直接跳到现有正式公共猪，缩短人工审核流程。
- 正式源数据经 AstrBot 本地同源代理读取，图片不要求 sandbox 直接跨域访问外部来源。
- 批准／拒绝补上真实 mutation 回归测试，避免 UI 看似成功、实际没有提交审核动作。

### 📰 猪圈日报安全收口

- 群组自动日报的开启／关闭权限进一步收紧为 AstrBot 管理员。
- 固化祭品契约：`daily_report_random_eat_enabled` 默认关闭，且只有定时自动日报流程可触发；手动 `/猪圈日报` 永远只读，不改变玩家祭品状态。
- Charge／补货事件可进入日报聚合，但日报本身不成为玩法 state authority。

### 🧪 验证与兼容性

- 本轮功能在合并前均经 Python 测试、compile、pre-commit 与 AstrBot / Marketplace 既有 CI 契约验证。
- 可由 **v3.6.5 直接升级**。
- Charge 会对旧 roast cooldown 做惰性兼容迁移；不需要用户手工改数据。
- 永久图鉴、EX、保底与既有 60/30/10 烤猪 outcome 语义不因本次更新重新计算。

### 升级建议

正常透过 AstrBot 插件更新或 GitHub Release ZIP 升级即可。若你自行维护公共源审核服务，请同时同步本版对应的 source review 前后端文件，以取得完整审核与浏览修复。

## v3.6.5 (2026-08-15)

### 版本主题：群日报 opt-in、收藏身份安全与公共源审核加固

### 修复

- 猪圈日报自动推送改为 **per-group opt-in**：新群与既有未标记群一律默认关闭；只有群主、群管理员或 AstrBot 管理员使用 `/猪圈日报 开启` 后才会自动推送，并提供 `/猪圈日报 关闭`、`/猪圈日报 状态`。全局 `daily_report_auto_send` 仅保留为 master switch。
- scheduler 只遍历显式启用群，`auto_enabled_since` 阻止新开启群补发更早日期；23:50 + 随机延迟被限制在报告自然日内，不再跨午夜。
- 修正日报「热门猪」误导：当所有猪都只出现一次时，不再任选一只标成最热门，改为明确显示形态分散；若烤猪 storage 总量包含缺少 Gameplay Event 人物明细的旧记录，保留真实总量并标注缺失明细，人物称号只按可追溯事件计算。
- 修复公共源审核图片代理使用错误 GET query API 导致管理页只显示 🐽 fallback；改用 AstrBot `request.query`，并为 review list/image 敏感 GET 加 same-origin + CSRF。
- 公共源审核新增现役 catalog 的正规化名称近似与 64-bit dHash 图片感知相似提示；提示只辅助人工审核，不会自动拒绝合理变体，同 ID／待审完全相同 SHA-256 仍为硬拒绝。

### 数据与身份安全

- 完成 claim-aware Collection Identity Boundary：`CollectionService` 只读取目前 namespaced identity 与已由 `identity_claims` 证明属于同一 logical user 的旧 fragment，不自动合并 sibling Bot instance，也不把其他平台同 raw ID 的数据串入。
- 永久 ownership 可跨安全 fragment 联集；`first_unlocked` 取最早、`last_drawn` 取最晚、同猪 `count` 取 `max` 而不是相加，避免 migration copy 虚增 EX Lv.。
- `duplicate_streak`、`total_draws`、`active_days` 不跨 fragment 算术合并；目前 gameplay state 仍以最高优先级 fragment 为权威，旧数据不会把已失效保底重新带回。

### 公共源安全

- 明确区分协议门槛与身份认证：`User-Agent` / `X-RollPig-*` 可被开源客户端模拟，只作 protocol gate；公开投稿安全依赖内容验证、来源 HMAC 指纹节流、人工审核与服务端管理 token。
- 新增全局待审上限 200，duplicate index 依 canonical `pig.json` revision cache，避免每次刷新重算全 catalog 图片。
- review service systemd sandbox 增加 `PrivateDevices`、`ProtectHome`、`ProtectKernel*`、`ProtectControlGroups`、`LockPersonality`、`MemoryDenyWriteExecute`、`RestrictAddressFamilies`；管理 Bearer token 仍只存在维护者主机，不进插件配置或浏览器。

### 兼容性

- 可由 **v3.6.4 直接升级**；不修改 SQLite schema、玩家抽取权威、EX 算法、保底概率、烤猪概率或 Resource Protocol。
- 本版不包含烤箱 charge/refill 新玩法。
- 公共源审核的服务端 duplicate/security 加固需要维护者主机同步新版 `source_service/app.py` 与 systemd unit；一般插件用户只需正常更新插件。

## v3.6.4 (2026-08-14)

### 版本主题：公共猪源兼容与 QQ 图鉴投递修复

### 修复

- 修复 v3.4.0 将旧 Felis 默认资源源切换到 AstrBot 专用源时，只以内置 99 只小猪建立首版来源造成的内容缩水；固定 v3.4 cut-over 前最后一个 Felis RollPig 快照（199 IDs）作 compatibility floor，官方源必须保持其超集，同 ID 仍以目前 AstrBot canonical 数据与图片为准。
- 新增公共源兼容构建与 live canonical 原子迁移工具；CI 固定旧快照 commit / resource version / pig.json SHA-256，禁止跟随可变 Felis main，并以 `miku-pig`、`wechat-pig`、`duke-pig` 作回归哨兵。
- 修复 QQ/NapCat/NTQQ 已实际送达 `/我的猪圈` 图片，但等待 `NodeIKernelMsgService/sendMsg` 回执超时返回 `retcode=1200` 时，被误报为「图鉴图片生成失败」；此类 ACK timeout 现在视为投递结果不确定，只记 warning、不重试、不发失败提示，避免重复图片。
- `/我的猪圈` 将图片渲染与消息投递错误分离；真正 render error 与真正 send error 使用不同提示，且页码范围改按永久 display catalog 计算。

### 兼容性

- 可由 **v3.6.3 直接升级**；不修改 SQLite schema、玩家 ownership、EX count、保底、烤猪概率或 Resource Protocol 版本。
- PR #68 identity-fragment merge 仍未包含；本版不引入烤箱 charge/refill 等新玩法。

## v3.6.3 (2026-08-14)

### 版本主题：永久收藏与架构稳定性收口

### 修复

- 修复 catalog read boundary 在 `_reload_catalog_layers()` 已改以 `self.pig_list` 接收合并结果后，仍以已移除的 `merged` 变量保存 catalog，导致完整插件初始化可触发 `NameError`；新增持久化契约测试防止回归。
- 修复永久猪圈把「目前 active catalog」错当成永久收藏全集：玩家已解锁、但后来退出现役公共猪源的历史小猪会由 `pig_snapshots` 补入 `/我的猪圈` read model，保留收藏可见性与历史数据；退役小猪不会重新加入每日抽池、随机／搜索 catalog，管理员 tombstone 仍可明确隐藏。
- 修复 `DailyReportMixin.pigsty_daily_report()` 在模块重载／MRO class identity 变化后使用零参 `super()._event_sender_id(event)` 可能触发 `TypeError: super(type, obj)`；改由 live plugin instance `self._event_sender_id(event)` 分派，并避免重复写入日报会话数据。

### 架构

- 完成 command registration boundary：15 个 RollPig 指令 decorator 全部收回 `main.py` 真正 Star 入口，helper/mixin 仅保留业务方法；每个 command 显式 `priority=1000` 并由薄 wrapper 委派，移除 v3.6.2 的 runtime handler rebind / registry 重排 workaround。
- 完成 catalog/resource read boundary：新增纯 `CatalogService`，集中 base/local/tombstone 合并、ID 查找、图鉴排序、页数、随机与搜索；新增 `ResourceReadService` 固定 local override → EX variant → cloud → bundled 图片解析顺位。
- 完成 renderer boundary：单猪卡、永久图鉴、随机／搜索九宫格、本周小猪与料理卡的 PIL 绘制移入 `renderers/`；renderer 不取得 AstrBot/storage/sync 依赖，domain read 仍由插件 orchestration 准备。
- 完成 roast/group interaction boundary：普通烤群友与预约烤猪共用 `RoastService` 的单一 60/30/10 outcome policy；`DailyReportMixin` 改为 outcome event hook，不再复制完整烤猪流程。
- AstrBot Market Smoke 现在对 PR checked-out revision 建干净 snapshot，直接交给官方 validator worker 的 `PluginManager.load()`，避免 PR CI 实际偷验 default branch。

### 兼容性

- 可由 v3.6.0 / v3.6.1 / v3.6.2 直接升级；不修改 SQLite schema、资源协议、烤猪概率、保底或 EX 等级语义。
- PR #68 的 identity-fragment collection merge **未包含在本版**；该修复仍需完成 claim-aware end-to-end 验证，避免跨平台串数据、重算保底或虚增 EX count。

## v3.6.2 (2026-08-14)

### 版本主题：指令派发所有权 Hotfix

### 修复

- 修复 v3.6.0 将 decorated handlers 拆到 `legacy_main.py`／feature mixin 后，AstrBot 仍以函数定义模块记录 `handler_module_path`，而真正 Star 只注册在 `main.py`，造成 `/今日小猪` 等指令可被指令管理器发现、却在 `StarRequestSubStage` 执行时因 `star_map` 找不到 helper module 而被跳过，最后落入其他插件／LLM 的严重回归。
- `main.py` 现在在 feature import 完成后，把本插件 handler metadata 统一重新绑定到真正的 Star 入口，恢复 v3.5.x 时「插件入口与 handler owner 一致」的派发语义；函数本体、存储与数据格式不变。
- RollPig command handler 明确提升至 priority `1000` 并重排 registry；搭配 v3.6.1 已加入的 handler 入口 `stop_event()`，形成「先执行 RollPig 指令，再停止后续通用 AI／消息 handler」的双层隔离。
- AstrBot Market Smoke 新增真实 runtime registry 契约：以 `data.plugins.astrbot_plugin_rollpig_plus.main` 实际导入插件后，必须验证所有 RollPig handler owner 均为 `main`、所有 command priority ≥ 1000，且 `roll_pig` handler 存在；避免未来再次出现「指令列表可见但实际不派发」的回归。

### 兼容性

- 可由 **v3.6.0 / v3.6.1 直接升级**；SQLite／JSON、永久图鉴、本地 override、历史记录、EX 差分、日报与预约烤猪数据均不需要 migration。
- 本版不新增玩法、不修改资源协议与数据 schema，只修正 AstrBot handler registry metadata 与指令执行顺序。

## v3.6.1 (2026-08-14)

### 版本主题：指令隔离与资源自愈 Hotfix

### 修复

- 修复 `猪圈日报` 同时由 `daily_report_feature` 与 `legacy_main` 注册造成 AstrBot 指令冲突；仅保留完整统计海报实现。
- RollPig 聊天指令在匹配后主动停止事件继续传播，避免 `/今日小猪` 等指令完成后仍落入其他插件或 LLM。
- AI 料理／繁体文案优先使用发行包内 `荆南麦圆体.otf`，不再因缺少旧的独立繁体字体而误用 Pillow 默认字体。
- 当历史／本地 PigHub 小猪仍保有可信 `source_url` 但图片文件遗失时，发送前会安全地重新下载、校验并恢复本地图片；失败仍维持既有无图降级。
- 已有版本状态但本地 cloud cache 图片不完整时，插件重启后会提前尝试完整原子重同步，不必等待正常同步周期。

## v3.6.0 (2026-08-14)

### 版本主题：群聊成长、完整日报与发行稳定性

### 新功能

- 猪圈日报升级为可配置统计海报与自动推送系统：加入真实并列称号、平台头像、跨午夜日期锁定、重启补发与可选「今日祭品」；手动查看不触发祭品。

- 新增可配置预约烤猪：明确指定尚未抽猪的目标时，第一位主厨支付普通冷却建立同群当日预约，后续群友可免费添柴；目标本人在同群显示今日小猪后一次性按原 60/30/10 结算。
- 预约默认最多 12 人（可配置 2–20），建立时尊重昨日被烤保护；随机烤与后门不建立预约，添柴不直接提高成功率。
- 预约状态在消息投递前先标记 resolved，避免适配器超时造成重复结算；流程接入 `roast_reservation_created/joined/triggered` 与既有烧烤 outcome Gameplay Event，因此日报可沿用原统计。
- 新增 [`docs/ROAST-RESERVATIONS.md`](docs/ROAST-RESERVATIONS.md) 说明群／日隔离、冷却支付与一次性语义。
- 新增 EX Lv.1–5 稀疏成长差分：同一只小猪可按玩家既有 `count - 1` EX 等级替换图片、描述或完整文案，各字段独立向下继承；EX 5 以上沿用最后有效差分。
- AstrBot Resource Protocol v1 增加可选 `pig_ex_variants.json`／`variant_images`，仍沿用大小、SHA-256、图片解码、128 MiB 预算、staging 与原子切换；旧 v1／私人来源不需要修改。
- 本地小猪 override 仍高于远端／内置 EX 差分；`/明日小猪` 预测不套用玩家已拥有的 EX 成长，避免把收藏状态泄漏到未来结果。
- 群聊本人重复抽取可写入去重的 `ex_level_up` Gameplay Event，为后续日报与成就统计提供数据，不改变收藏权威状态。
- 新增 [`docs/EX-VARIANTS.md`](docs/EX-VARIANTS.md) 说明格式、继承、安全边界与目前尚未包含的管理面板 EX 编辑／投稿范围。


### 修复

- 修复管理面板「投稿公共源」在 sandbox 中依赖原生 `window.confirm` 导致点击无反应；改用页面内二次点击确认并补齐成功／失败反馈与回归测试。
- 修复 v3.5.0 发行包排除 `resource/font/荆南麦圆体.otf` 导致 Linux 中文标题可能回退 DejaVu 显示方框；Release／Marketplace 现在强制打包并在 CI 中断言字体存在。

### 架构

- 新增共用 `gameplay_events.py` Gameplay Event v1 契约；PR #51 的日报事件保持原 JSON 兼容，并改由共用写入／去重／读取／裁剪函数管理。
- `DailyReportMixin` 增加 `_record_gameplay_event()` 作为后续 EX 成长、预约烤猪与烤箱补货的统一事件入口；原 `_record_daily_report_event()` 开关语义保持不变。
- 新增 `docs/ARCHITECTURE.md`，记录渐进式拆分与事件持久化边界。

## v3.5.0 (2026-08-14)

### 版本主题：自己的公共猪源与审核工作流

- 将本地小猪投稿从 PigHub 改为本项目自建的 AstrBot 公共猪源；PigHub 仅保留为管理面板选图来源。
- 投稿会在管理员再次确认后传送 ID、名称、描述、完整文案及标准化图片，不会传送群友、群组、聊天、配置或存储数据。
- 新增独立审核服务、SQLite 队列、重复 ID／图片拦截、来源 HMAC 指纹及 24 小时投稿限速。
- 维护者面板新增待审核卡片、图片预览、批准发布与拒绝功能；普通实例自动隐藏该区域。
- 审核 Token 仅由来源服务与维护者插件后端读取，不进公开配置，也不下发浏览器。
- 批准投稿后先使用正式构建器全量校验，再建立不可变资源版本、备份 canonical catalog 并原子切换 `v1`。
- 发布失败会恢复原 catalog；服务启动时可修复已完成发布但审核状态尚未落库的短暂崩溃窗口。
- 新增 OpenResty、systemd 部署范本与公共源维护文档；正式插件 ZIP 排除服务端源码及部署文件。
- README、资源管理、运维、配置、文档索引与市场描述更新到 v3.5.0。

## v3.4.0 (2026-08-14)

### 版本主题：AstrBot 专用猪源

- 建立 `AstrBot RollPig Resource Protocol v1`，以 `schema_version`、`client`、版本化 User-Agent 及专用请求标头区分 AstrBot 增强版客户端。
- 上线 `https://curryudon.top/astrbot-rollpig/v1/manifest.json`，首版提供完整 99 笔小猪数据与 99 张图片。
- 普通浏览器、错误 Client／Protocol 与 nonebot 客户端请求返回 HTTP 403；正确 AstrBot v1 请求返回 200。
- 新安装默认启用新来源；旧 `pig.felislab.cc` 受限地址会精确迁移，自定义私人来源不会被覆盖。
- 官方来源强制校验 manifest 的协议版本与客户端标识；私人 manifest 保留向下兼容。
- 新增可重现的资源源构建器，拒绝坏数据、缺图、多图、非法 ID、超大或无法解码图片，并生成逐档大小及 SHA-256。
- 新增资源源 CI Artifact、OpenResty 路由范本及完整维护手册，正式部署采不可变版本目录与原子链接切换，支持快速回退。
- 明确说明专用标头是兼容性闸门而非秘密；真正封闭的私人源应另加每实例 Token 或 mTLS。

## v3.3.0 (2026-08-14)

### 版本主题：可视化资源治理

这个版本把小猪素材从「只能新增、编辑、删除」提升为可观察、可恢复、可投稿、可接入私人源的完整管理流程；同时清理失效的默认云源及项目展示信息。

### 新功能

- 管理面板新增「本地资源」工作区，分开展示本地新增、基础源覆盖与删除屏蔽。
- 每笔本地记录会标示是否覆盖基础源、是否使用本地图片，并可直接进入编辑。
- 新增取消屏蔽 API 与管理操作；SQLite 单一权威及旧 SQLite 兼容模式均以事务移除 tombstone。
- 编辑小猪时可下载目前生效的完整原图，供本地重修后重新上传。
- 本地小猪可在管理员明确确认后，依 PigHub 公开网页流程提交名称与图片到人工审核队列。

### 云端与私人源

- 查明旧默认 `pig.felislab.cc` 会对本 AstrBot 插件返回 HTTP 403，原因是来源只授权官方 `nonebot-plugin-rollpig-plus` 客户端。
- 新安装默认关闭资源同步，`resource_manifest_url` 默认留空，避免持续请求已知不兼容来源。
- 既有配置不会被更新程序静默删除；面板会保留错误并给出针对性诊断。
- 面板遇到受限来源的 403 时会标记「来源不可用」，阻止无意义的重复手动同步。
- 完整保留自有 HTTPS manifest、SHA-256、大小、图片像素及原子切换能力，作为私人猪源方案。

### 安全与隐私

- PigHub 投稿只接受本地 override，端点固定且每次需要 CSRF、同源检查与显式确认。
- 投稿只发送小猪名称与图片，不发送描述、文案、用户、群组、聊天或存储数据。
- 远端响应限制为 256 KiB；返回图片地址必须是无账号密码的 HTTPS URL。
- 投稿不做自动重试与审核轮询，避免具有副作用的请求造成重复数据。
- 原图下载限制为已认证管理页、有效小猪 ID、受支持格式及 50 MiB 上限。

### 文档与项目展示

- README 重新设计为正式项目首页，加入版本亮点、能力矩阵、管理工作区、资源分层、安全模型、升级策略与文档导航。
- 移除不能代表本插件真实下载情况的第三方访问量与 Star History 图表。
- 新增 `docs/RESOURCE-MANAGEMENT.md`，完整说明资源层、私人 manifest、PigHub 投稿、安全边界与故障排查。
- 同步更新配置、指令、运维、文档索引、市场 metadata 及发版说明。

### 升级影响

- 从 v3.2.x 可直接升级；SQLite、历史图鉴、本地图片、override 与 tombstone 均保留。
- 没有配置私人源时，插件继续使用内置资源和全部本地改动，抽猪功能不受影响。
- 既有安装若仍保留旧受限 URL，升级后面板会显示诊断；管理员可改填自有 manifest 或保持同步关闭。

### 验证

- Python 3.10／3.12 语法与完整 pytest 回归。
- SQLite tombstone 新增、删除、恢复及兼容文档同步测试。
- 管理页 JavaScript module、DOM ID／引用及资源工作流契约测试。
- README 本地链接、metadata 版本一致性、release archive 与 AstrBot 市场 16 MB 上限检查。

## v3.2.1 (2026-08-12)

### AstrBot 市场分发

- Release 包切换为独立身份 `astrbot_plugin_rollpig_plus-vX.Y.Z.zip`，与 v3.1.4 旧身份桥接通道分离。
- 精简发版字体与开发文件，使正式 ZIP 符合 AstrBot 市场 16 MB 上限。
- 新增市场 metadata、Release 资产名称、SHA-256 及双更新通道契约测试。
- 更新器改读稳定 Releases 列表，只接受版本与 `astrbot_plugin_rollpig_plus` 资产名称精确匹配的包。

## v3.2.0 (2026-08-11)

### 独立插件身份与安全迁移

- 插件市场身份切换为 `casama233/astrbot_plugin_rollpig_plus`，代码目录、配置和数据命名空间与原版彻底分离。
- 首次安装会优先验证 v3.1.4 来源标记；没有标记时仅接受增强版 SQLite/多文件指纹，避免把 MegSopern 原版数据误迁移。
- 旧数据采用 SQLite backup 或逐文件 SHA-256 的 Copy → Verify → Atomic Commit 流程，迁移成功后旧目录仍完整保留。
- 新配置首次创建时只迁移当前 schema 仍支持的旧配置项；未知或废弃字段不会带入。
- 拒绝在旧 `astrbot_plugin_rollpig` 代码/配置命名空间内启动，防止手动 clone 导致两个插件共用配置。
- 检测到旧插件同时启用时给出指令冲突警告，不会擅自停用或删除旧插件。

## v3.1.4 (2026-08-11)

### 插件身份迁移桥接

- 为现有增强版数据目录写入原子化来源标记，供后续 `astrbot_plugin_rollpig_plus` 安全识别，避免误迁移原版插件数据。
- 安全更新器遇到 `3.2.0+` 新插件身份时拒绝原地覆盖，改为提示从 AstrBot 插件市场安装新包并迁移。
- 保持当前插件名、数据目录和配置命名不变，本版本只建立迁移桥，不搬动或删除任何用户数据。

## v3.1.3 (2026-08-11)

### 消息投递修复

- 修复图片消息发送超时后又触发 fallback，导致渲染卡片、原图和文字描述重复发送的问题。
- 发送超时改为「投递状态不确定」：已开始投递的图片不再重试 fallback，临时文件保留 90 秒供慢适配器读取。
- fallback 图片链超时后不再补发第二条纯文本，避免迟到成功的图片链与重试文本并存。

## v3.1.2 (2026-08-05)
### Analytics 字体与可读性修复
- Analytics 基础正文提高到 14px，卡片标题提高到 16px，辅助文字、图例、平台名称和表格内容统一提高到可读范围。
- 日期热力图、收藏覆盖、双周期对比、回访用户、平台构成、上升最快猪猪和运行健康等区块同步调整，不再以 7–9px 作为最终显示字级。
- 提高表格行高、卡片内边距和正文行高，同时保留桌面信息密度。
- 新增 1366px 桌面与 430px 窄屏 Chromium 布局测试，验证最终计算字级与横向溢出。

## v3.1.1 (2026-08-05)
### 管理页按需加载与性能修复
- 管理页默认只运行轻量核心模块，不再自动请求或注入企业增强与 Analytics 整包资源。
- 新增“深度分析”按钮；只有点击后才通过认证桥接加载 Analytics 样式、脚本与聚合数据。
- 删除大体积源码的 `sessionStorage` 缓存、100ms Bridge 轮询、持续 DOM `MutationObserver` 与同步状态自动轮询。
- Analytics 按当前 `.shell` 根节点绑定，旧 SPA 根节点通过 `AbortController` 解除事件，避免重复挂载和重复刷新。
- 新增 jsdom 回归和真实 Chromium 性能测试，覆盖默认零增强请求、单实例挂载、SPA 多次重入、观察器/定时器数量与 JS 堆增长。

## v3.1.0 (2026-08-04)
### 认证桥接企业 UI 与浏览器级回归
- 核心数据总览、猪猪图鉴、同步、SQLite 管理和安全更新继续由轻量主模块独立运行，不等待任何增强资源。
- 新增只读 `ui/assets` 接口，只从插件目录固定白名单读取企业主题、反馈增强和 Analytics 源码，并通过 AstrBot Plugin Page Bridge 携带认证返回；浏览器不再直接请求会 401 的相对子资源。
- 主页面仅内联小型启动器，使用版本化会话缓存、SHA-256 校验、模块独立错误边界、可见诊断与重试；增强层失败不会隐藏或阻断核心视图。
- 恢复 v2.15.0 商业级企业主题与深度 Analytics，并支持 AstrBot 单页容器二次进入时重新挂载。
- 新增 jsdom 浏览器行为测试，覆盖核心视图切换、认证资源注入、资源失败降级、Analytics API 局部失败和 SPA 重挂载。

## v3.0.5 (2026-08-04)
### 紧急恢复附属页面可用性
- 撤回 v3.0.4 将数千行 CSS/JavaScript 内联进管理页的高风险方案，恢复最后已知可正常加载的轻量页面。
- 移除会返回 401 的相对增强资源请求；基础总览、图鉴、同步、SQLite 管理与安全更新继续可用。
- 企业增强主题与深度 Analytics 暂时停用，待通过真实 AstrBot 浏览器集成验证后再恢复。
- 不修改 SQLite 数据、API 数据结构、抽猪规则或其他业务流程。

## v3.0.4 (2026-08-04)
### 管理页受保护资源加载修复
- 修复 AstrBot 通过认证 API 注入插件页面时，相对脚本与样式子资源无法携带授权头而返回 401 的问题。
- 企业主题、交互反馈和深度 Analytics 现在直接内联进主页面，不再请求受保护的 `page/content` 子资源。
- 保留模块化 CSS/JS 源文件作为维护来源，并新增构建一致性测试，防止发布包重新引入外部受保护资源。
- 不修改 Analytics API、SQLite 单一权威、数据结构或业务流程。

## v3.0.3 (2026-08-04)
### Analytics 单页容器重新挂载修复
- 修复 AstrBot 管理后台复用同一个页面窗口时，旧版全局 ready 标志残留，导致新 DOM 没有 `analyticsSuite` 却跳过初始化的问题。
- Analytics 现在以当前 DOM 是否实际挂载为准，并使用版本化启动状态；旧状态或缺失挂载会自动重新初始化。
- 刷新按钮按当前 DOM 元素去重绑定，hashchange 监听全局只注册一次，避免重复进入页面后叠加请求。
- 不修改 Analytics 只读 API、SQLite 单一权威、数据结构或其他管理业务流程。

## v3.0.2 (2026-08-04)
### Analytics 初始化时序修复
- 修复 AstrBot 管理桥接尚未就绪时，深度 Analytics 过早标记为已初始化并永久退出的问题。
- Analytics 现在会以 100ms 间隔、最多 8 秒等待桥接；桥接就绪后才设置完成标记并读取聚合数据。
- 重复注入保持幂等；桥接长期不可用时显示局部错误与“重新连接”，普通总览、图鉴和管理操作不受影响。
- 所有管理页资源缓存键同步提升至 v3.0.2，不修改 SQLite 单一权威、API 契约或业务流程。

## v3.0.1 (2026-08-04)
### 管理页 UI 缓存与恢复证据修复
- 修复从旧版本直接升级到 v3.0.0 后，浏览器可能继续使用旧版 `ui-feedback.js`，导致企业主题与 Analytics 增强层没有加载的问题。
- 管理页入口、企业主题、Analytics 主题、反馈核心与增强脚本统一加入版本化缓存键；今后升级后无需依赖手动强制刷新才能看到新 UI。
- 修复检查损坏 SQLite 时可能由 SQLite 重写原始 `-shm` 旁路文件的问题；替换数据库前会先保存原始 WAL／SHM 恢复证据。
- 不修改 v3 的 SQLite 单一运行时权威、数据迁移事实、业务命令或管理写接口。

## v3.0.0 (2026-08-04)
### SQLite 单一运行时权威
- 规范化 SQLite 表成为唯一运行时权威；每日抽取、吃猪、烤猪、AI 文案、身份映射和后台图鉴热写入不再重建或持久化整份兼容 JSON。
- schema 6 会在完整性、外键与规范化一致性检查通过后晋升既有数据库；旧文档损坏不会覆盖 SQL，规范化表损坏则拒绝晋升并保留恢复数据。
- 新安装在 `auto` 模式直接建立 SQLite；旧 JSON 安装会先完整备份，再导入临时数据库、执行事实级对账与完整性检查后原子切换。
- JSON 兼容文件只在导出、回滚或灾难恢复时从 SQL 按需生成，生成过程不会写回数据库；`storage_backend=json` 保留为显式紧急模式。
- 新增跨进程每日抽取唯一性、事务崩溃回滚、热路径零兼容文档、旧数据自动迁移、晋升拒绝与派生统计修复测试。

## v2.15.0 (2026-08-04)
### 商业级 Analytics 管理后台
- 管理页改为紧凑的企业级 Analytics 工作台，统一明暗主题、状态语义、组件密度、响应式与无障碍体验。
- 新增只读 `analytics/insights` 聚合接口，展示双周期增长、七日回访、二十八日活动热力、图鉴覆盖分布、平台构成、上升猪猪及玩法运行健康。
- 深度分析只返回聚合数字和猪猪 ID／名称，不返回用户 ID、群号或原始聊天记录；读取失败也不会影响原总览、图鉴和维护功能。
- SQLite 直接聚合规范化表；JSON 后端保留兼容统计路径，不改变现有数据结构、写入逻辑或业务流程。

## v2.14.0 (2026-08-04)
### SQL 原生统计与存储可观测性
- 管理面板的总用户、累计抽取、平均解锁、近 14 日趋势与热门小猪改为直接聚合规范化 SQL 表，不再遍历整份 `pig_history` 运行快照。
- schema 5 新增日期／小猪与图鉴反向查询索引，改善大数据量下的趋势和收藏统计性能。
- 存储状态面板显示统计来源、schema、写入权威以及最近一次自动／手动修复的动作、原因和时间。
- 保留 JSON 后端的原有统计回退路径；SQLite 不可用或主动回滚后，管理面板仍可正常工作。
- 增加十万用户与三十万每日记录的 SQL 聚合压力测试及索引、修复元数据回归测试。

## v2.13.1 (2026-08-04)
### 新解锁趋势修复
- 修复 JSON→SQLite 迁移与投影重建把历史抽取的 `was_new_unlock` 全部写成 0，导致管理面板「新解锁」曲线长期贴地的问题。
- schema 4 会根据每位用户图鉴的 `first_unlocked` 日期自动回填历史抽取；被吃掉的记录使用 `original_pig_id` 还原当天真正解锁的小猪。
- 今后的 JSON 投影会在写入 `daily_draws` 时直接计算新解锁标记，不会再次丢失统计。

## v2.13.0 (2026-08-04)
### 每日 AI 生成权与 SQL 启动快照
- 新增 `ai_roast_generation_attempts`，以 `(pig_id, generated_date)` 唯一键保证所有 AstrBot 实例每天每只猪最多实际调用一次模型；生成失败也会记录，当天不重复消耗 Token。
- 当天首次成功生成直接使用新文案；同一天后续烧烤从该猪今天及此前六天的有效文案中随机选择，滚动窗口共七个自然日。
- SQLite 启动时由规范化表重建用户图鉴、每日记录、烤猪状态、AI 缓存、身份映射及本地图鉴层，不再把兼容文档作为运行时启动来源。
- `identity_claims` 与 `identity_aliases` 改为 SQL 主写；兼容 JSON 继续事务同步，仅用于导出、回滚和旧版灾难恢复。
- SQLite 主写数据库检测到兼容文档损坏或过期时，只会由规范化 SQL 反向修复文档；不会再用旧文档覆盖正确数据库。

## v2.12.0 (2026-08-04)
### 烤猪、AI 文案与图鉴后台 SQL 主写
- 烤群友冷却、每日被烤次数与每日后门改为规范化 SQL 表直接事务写入，跨连接唯一性由数据库约束承担。
- 猪圈保护次数改为直接查询 `daily_roast_counts`，聊天命令通过工作线程执行 SQLite I/O，不阻塞事件循环。
- AI 烤猪文案缓存改为 SQL 读取、清理与首写获胜；多进程并发生成时只保留当天第一份已提交文案。
- 管理后台新增、编辑和删除小猪改为 `catalog_overrides`／`catalog_tombstones` 原子事务写入。
- 兼容 JSON 仍在同一事务内同步，用于导出、旧版回滚和灾难恢复；上述热路径不再触发对应投影全表重建。

## v2.11.1 (2026-08-04)
### 被吃惩罚与每日抽取原子性热修复
- 修复 SQL 主写路径在“探测今日状态”阶段提前消费成功惩罚的问题；探测现在只判断失败或返回待选猪状态。
- 成功消费次日惩罚只会与 `daily_draws`、图鉴和统计写入在同一个 `BEGIN IMMEDIATE` 事务中提交。
- 若抽取写入、兼容文档同步或进程在提交前失败，惩罚与所有抽取记录会一起回滚，不会出现“惩罚消失但没有抽到猪”。

## v2.11.0 (2026-08-04)
### SQLite 核心写入事务
- 每日抽猪改为规范化 SQL 表的直接事务写入；`PRIMARY KEY(draw_date, user_id)` 现在真正承担跨连接并发唯一性。
- 次日被吃惩罚的检查、消费与失败锁定和每日抽取放在同一个 `BEGIN IMMEDIATE` 事务边界内。
- 吃群友的当天替换、原猪保存、次日惩罚和事件记录改为一次提交或全部回滚。
- 兼容文档仍在同一事务中同步，供 JSON 导出、旧版回滚和灾难恢复使用，但热写入不再触发历史／烤猪投影全表删除重建。
- JSON 后端继续保留旧逻辑；已迁移的 v2.10 数据库无需再次手动迁移即可使用 SQL 主写路径。

## v2.10.1 (2026-08-04)
### 管理面板确认框与迁移反馈热修复
- 修复 AstrBot Plugin Page 的 iframe sandbox 阻止原生 `window.confirm()`，导致“迁移 SQLite”等按钮点击后无请求、无日志、无前端反馈的问题。
- 迁移、重建索引、回滚 JSON、安装更新和 AI 覆盖文案改用页面内确认对话框；继续沿用原有 CSRF、互斥锁和操作耗时反馈。
- SQLite 迁移在开始执行及安全失败时写入明确日志，方便区分“前端未发请求”和“后端迁移失败”。

## v2.10.0 (2026-08-04)
### SQLite 查询路径与投影修复
- 新增 schema migration v2：身份补充 legacy/创建时间索引，群成员关系拆为 `daily_draw_groups`，避免继续查询 `group_ids_json`。
- SQLite 的用户图鉴、每日结果、群成员和被吃名单改为直接 SQL 查询；JSON 后端仍保留原有兼容读取。
- 修复 `transaction()` 只有 Python 锁而没有数据库事务的问题，现在使用独立连接与 `BEGIN IMMEDIATE`，异常必定回滚并关闭连接。
- 数据库验证新增文档与投影逐表计数对账；启动时可自动重建仅投影损坏的数据库，管理面板也新增手动“重建索引”。
- 抽取保底与烤／吃特殊形态规则移入 `services/`，继续缩小 `main.py` 的业务职责。
- 本版仍保留兼容文档作为写入权威层；直接 SQL 写入与 SQLite 默认启用留到 v3.0，避免在未完成增量事务前贸然切换。

## v2.9.3 (2026-08-04)
### 管理面板操作反馈与待重启保护
- 修复安全更新后页面文件已替换、但 AstrBot 尚未重启时，新页面请求旧后端路由并只显示“未找到该路由”的问题；现在会明确提示页面／运行时版本不一致并要求重启。
- 新增醒目的“等待重启”横幅；待重启期间禁用迁移、验证、重建、导出、回滚、同步与更新按钮。
- 管理操作显示独立按钮状态、执行阶段、已等待时间与耗时；v2.10 新增的投影重建也纳入同一反馈和互斥机制。

## v2.9.2 (2026-08-04)
### 特殊形态判定与文案
- 修复 `/吃群友` 检查发动者时沿用目标视角，导致发动者抽到猪排却错误提示“对方今天是猪排”的问题。
- 分离发动者、烧烤目标与进食目标的资格规则：人类和“吃掉了”仍不可参与；猪排、猪油等熟食不能主动行动或重复烧烤，但现在可以被正常吃掉。
- 机械猪等普通特殊猪不会被误判为熟食；吃群友成功文案会显示实际目标名称，熟食目标使用“开袋即食”文案。

## v2.9.1 (2026-08-04)
### 安全更新热修复
- 修复 SHA-256 校验误调用不存在的 `hashlib.compare_digest`，改用标准库 `hmac.compare_digest`；带 `SHA256SUMS` 的稳定版更新不再报属性错误。
- 新增回归测试，防止更新器再次引用错误模块。

## v2.9.0 (2026-08-03)
### SQLite 存储与可回滚迁移
- 新增 `SQLiteStorage` 与 `StorageManager`；默认 `auto` 只在数据库存在且完整时启用 SQLite，旧安装继续安全使用 JSON。
- 迁移流程先备份七份关键 JSON，临时建库、刷新正交投影、逐文件 SHA-256 对账并执行 SQLite 完整性与外键检查，全部通过后才原子切换。
- 新增 `schema_migrations`、兼容文档表及每日抽取、用户图鉴／统计、猪快照、被吃惩罚／事件、冷却、每日烤猪、后门、AI 文案、图鉴覆盖／删除投影表。
- 管理面板新增存储状态、迁移、验证、JSON ZIP 导出和安全回滚；所有写操作沿用同源与 CSRF 校验，不接受自定义文件路径。
- SQLite 使用 WAL、外键、`synchronous=NORMAL` 和可配置写锁等待；云资源与 PigHub 缓存继续使用 JSON，不纳入关键事务数据库。

## v2.8.0 (2026-08-03)
### 存储架构与安全更新
- 新增 `StorageBackend` 抽象与兼容旧数据格式的 `JSONStorage` 后端；现有命令继续读取原 JSON，损坏恢复、批量落盘和回滚集中到统一持久化层，为 SQLite 迁移预留接口。
- 猪圈管理面板新增官方稳定版检查与安全更新按钮；来源固定为 `casama233/astrbot_plugin_rollpig`，拒绝任意 URL、分支和预发布版本。
- 更新包执行 HTTPS／仓库身份、大小、文件数、解压体积、路径穿越、符号链接、异常压缩比、metadata 与 Python 语法检查；Release 提供 SHA-256 时强制核对，未提供时要求二次确认。
- 替换代码前自动备份插件目录，失败恢复旧文件；AstrBot 插件数据与配置不在替换范围，安装完成后只提示手动重启，不自动控制宿主进程。

## v2.7.0 (2026-08-03)
### 管理面板视觉升级
- 管理面板重构为「数据总览」与「猪猪图鉴」两个独立分页，并使用 URL 锚点保存当前分页，支持浏览器前进／返回。
- 六项核心指标改为数字递增与微型趋势线；14 日趋势升级为动态面积折线图，支持逐日悬停查看使用人数、抽取次数及新解锁。
- 平均收藏率改为动态环形进度图，热门小猪改为流畅进场的横向排行；图表缩放只依据实际展示序列，避免累计抽取量压扁趋势线。
- 新增柔和光晕、玻璃层次、卡片分段进场、图鉴悬停与弹窗弹性转场，并完整支持系统深色模式及“减少动态效果”。
- 新增／编辑小猪表单加入「选择图片 → 补全资料 → 检查发布」实时流程指示，现有 PigHub、AI 文案和云同步功能保持兼容。

## v2.6.0 (2026-08-03)
### 跨平台兼容
- 身份键加入 AstrBot 适配器实例 ID，避免同一类型的多个 QQ／Discord 等机器人共享猪圈、冷却与惩罚；旧 `v2|平台|...` 和更早的裸 ID 会按实例懒认领，不会直接清空既有图鉴。
- Telegram 记录 username 与数字用户 ID 的双向别名，`@username`、回复消息、随机点名和数字 ID 可以指向同一份今日小猪记录。
- 出站点名按平台编码：OneBot、Discord、飞书和 WhatsApp 使用标准 At；Telegram 使用 username 或 `tg://user?id=`；Slack 与 QQ 官方使用平台原生文本 mention。
- 增加 OneBot 原始消息段与 WhatsApp `mentionedJids` 后备解析，适配器未生成标准 At 段时仍能识别目标。
- WhatsApp 优先使用 PN／手机号并保留无法解析的 LID JID，降低第三方适配器或 LID 缓存缺失时认错用户的风险。
- 过滤 `@全体成员`、`@everyone` 与空 Reply 的默认用户 `0`，避免把广播或无效引用当作普通群友。

## v2.5.2 (2026-08-03)
### 修复
- 修复 QQ／aiocqhttp 等平台发送 `@` 时误把内部 `v2|...` 身份键作为用户 ID 的问题；发送消息段和文本回退前会还原为平台原生用户 ID。

## v2.5.1 (2026-08-03)
### 修复
- 允许导入小于 256×256 的本地或 PigHub 图片；统一规格化时会按比例放大并保存为 512×512 PNG，不再因低分辨率直接拒绝。

## v2.5.0 (2026-08-03)
### 管理面板优化
- AI 草稿生成增加可选的画面／创作引导词，管理员可补充图片中的动作、服饰、颜色和想要的梗，帮助模型避免只看名称和文件名产生误解。
- 生成过程中在表单内显示阶段进度与动态状态，完成或失败后自动收起，不再只有全局转圈等待。

## v2.4.0 (2026-08-03)
### 稳定性与安全
- 修复并发抽取可能令当日缓存与永久图鉴不一致的问题；相关 JSON 采用预写、备份与失败回滚的批量提交。
- `@他人` 现在只读取对方已有结果，不再替对方抽取，也不能借此绕过次日惩罚。
- 新增平台命名空间与旧 ID 认领记录：既有数据由首次使用的平台继续继承，其他平台的同号用户保持隔离。
- JSON 损坏时保留 `.corrupt-*` 副本并优先从 `.bak` 恢复，避免静默覆盖原始数据。
- AI 文案按小猪分片加锁并加入可配置超时，避免单个模型请求阻塞全部生成。
- 管理页写接口增加同源与 CSRF 校验；统计计算和缩略图处理移出事件循环，缩略图改为压缩 PNG。
- 云同步限制重定向主机、拒绝私网解析、限制图片尺寸，并在任务完成时立即落盘以降低峰值内存。
- 新增 IANA 时区配置，修复图片句柄、裁剪、长文案溢出及管理员 ID 比较不一致。

### 工程
- 版本更新至 2.4.0，文档最低 AstrBot 版本与元数据统一为 4.24.2。
- 移除未使用的 Jinja2 依赖，新增身份/IP 辅助模块、回归测试与 GitHub Actions CI。

### 管理面板优化
- AI 小猪草稿的描述改为严格 3-8 个汉字，一语道破小猪特质。
- AI 完整文案改为 40-120 字的简短单段，强化梗感、风趣感与哲学意味，并增加后端长度兜底。

## v2.3.0 (2026-08-03)
### 管理面板优化
- 移除聊天指令 `/同步小猪资源` 及其繁简体／刷新别名；公共资源同步统一从管理面板操作。
- 保留管理面板同步按钮、状态提示与后端同步 API，不影响自动同步配置。

## v2.2.0 (2026-08-03)
### 管理面板优化
- PigHub 选图后可一键调用当前 AstrBot AI 模型，参考小猪名称与现有图鉴文案生成描述和完整文案草稿；生成结果仍可继续手动修改。
- 新增／编辑小猪弹窗不再因点击外部遮罩关闭，避免误触丢失尚未保存的内容。

## v2.1.0 (2026-08-02)
### 兼容性修复
- 兼容 WhatsApp Baileys 的 LID JID（如 `123…@lid`）与适配器规范后的手机号 ID：@ 提及、引用回复、随机玩法和发送 @ 均会统一到同一用户。
- 兼容升级前已经写入的 LID 数字历史键；检测到旧记录时沿用原键，不会因切换到手机号映射而重复解锁或丢失今日结果。
- WhatsApp 群组 ID（`…@g.us`）继续使用适配器的稳定群 ID，烤猪冷却、保护、吃群友与猪圈日报不会因 JID 后缀变化而串组。
- WhatsApp 未安装或映射暂不可用时自动保持原有跨平台 ID 解析，不影响 QQ、Discord、Telegram、Slack、飞书等适配器。

## v2.0.3 (2026-08-02)
### 优化
- 从 PigHub 选图后自动生成稳定唯一 ID，并将 PigHub 标题带入名称字段；描述和完整文案继续由管理员确认填写。
- PigHub 来源确认后禁用本地文件输入与「本地上传」按钮，避免同一次保存同时提交两套图片来源；后端也会拒绝混合来源请求。

## v2.0.2 (2026-08-02)
### 修复
- 修复管理面板近 14 日趋势图现在显示全部 14 个日期刻度；此前为防止重叠只显示每隔一天的刻度，容易误以为只有 8 天数据。

## v2.0.1 (2026-08-02)
### 修复
- 周报现在会保留成员当天原本抽到的小猪；若之后被吃掉，会在该日卡片右上角标注「被吃掉了」，不会把周报内容替换成特殊形态。
- AI 烤猪文案统一使用随插件附带的「汉仪勇字小熊猫繁」字体，以覆盖繁体及罕见字形；字体无法加载时仍会安全回退常规字体。

## v2.0.0 (2026-08-02)
### 新增
- 新增 `/吃群友 @某人` 与 `/随机吃群友`：默认成功率 15%，成功会令目标、失败会令发起者成为当天的「吃掉了」；两种结果都会在次日首次抽猪时按默认 20% 概率失败，失败后锁定至当天结束。
- 吃群友同样遵守特殊形态资格与次日保护；随机吃群友会自动排除受保护、已吃掉及其他不可行动成员。
- 新增 `/猪圈日报`／`/豬圈日報`，展示当前群的抽猪人数、被吃人数，并从当日被吃成员中随机点名「可怜被吃」。
- 新增吃群友开关、成功率与次日失败率配置，均可在插件配置页调整。

## v1.9.0 (2026-08-02)
### 新增与修复
- 新增群聊被烤保护：同一成员当天在同一群实际被烤达到阈值（默认 3 次）后，次日自动获得保护；普通烧烤会在消耗冷却前拦截，后门强制模式可突破。逃脱不计数，反噬计入实际被反噬者。
- 特殊形态补齐：`猪油` 与猪排按熟食形态处理；`人类`、`吃掉了`、熟食形态与保护状态均有独立提示。`吃掉了` 作为独立特殊形态，不能继续参与任何正常烧烤流程。
- 新增 `enable_roast_protection` 与 `roast_protection_threshold` 配置项，可关闭保护或在 1-20 次之间调整阈值。

## v1.8.3 (2026-08-02)
### 优化
- AI 烤猪文案按「小猪 ID + 日期」全局限流：每只猪每天至多调用一次模型，文案持久化保留最近 7 天；同日再次烤该猪会随机复用这 7 天内的已有文案。
- `/我的猪圈` 调整为已解锁小猪优先展示，未解锁小猪顺延至后续页面；两个区间内部仍保留管理员维护的图鉴排序。

## v1.8.2 (2026-08-02)
### 优化
- AI 烤猪文案改为机灵、梗感与轻度黑色幽默风格：调侃范围限定于虚构小猪、猪圈与抽卡命运，并增加反转要求与标题前缀清洗；不涉及真实用户或现实暴力细节。

## v1.8.1 (2026-08-02)
### 修复
- 统一提及目标解析：优先识别 AstrBot 标准 `At` 段，补充 Discord 原生 `mentions`、`<@用户ID>` 格式和常见引用消息发送者字段；手动输入支持 Discord、Slack、飞书等非纯数字用户 ID。
- 修复开启 `at_view_pig` 后 `/今日小猪 @某人` 仅因 @ 不属于 `message_str` 而无法查看对方结果的问题。
- 所有群聊提及发送统一走标准 `Comp.At`；适配器不支持时仅降级为带用户 ID 的文本，生成的今日小猪图片和随机烤群友流程不再被 @ 段发送失败中断。

## v1.8.0 (2026-08-02)
### 新增
- 完整补齐烤猪玩法：`/今日烤猪` 会拦截人类、熟食形态与已吃掉的小猪；可选启用当前 AstrBot 模型生成料理文案，模型不可用时自动回退本地模板。
- 新增 `/烤群友 @某人`，支持 @ 或回复目标消息；按 60% 成功、30% 逃脱、10% 反噬判定，并以「群聊 + 发起者」为单位冷却 8 小时（可配置）。
- 新增 `/随机烤群友`，仅从当天在当前群聊抽过小猪且符合资格的成员中随机选择。
- 新增后门口令：`/打点后厨`、`/偷换烤架`、`/贿赂主厨`、`/加急生火` 每人每天一次；AstrBot 超级管理员可用 `/强行点火` 无限制强制成功。后门仅绕过概率与冷却，不绕过目标资格。
- 帮助图片卡新增完整烧烤玩法说明；繁简指令与口令均可使用。

## v1.7.1 (2026-08-02)
### 修复
- 帮助图片卡改用简体中文，并固定使用插件内置字体渲染；避免部分 AstrBot 容器缺少完整 CJK 系统字体时出现繁体缺字或异常字距。

## v1.7.0 (2026-08-02)
### 修复与性能
- 修复 PigHub 选图器缩略图在 AstrBot 沙箱 iframe 内直接跨域加载而破图的问题；网格现由插件服务端返回 RGBA Canvas 像素，不再输出外部 `<img>` 请求。
- PigHub 索引保留内存与磁盘 12 小时缓存；缩略图采用按 URL 的内存（72 张）与磁盘（7 天）缓存，网格最多 3 路并发且同一图片请求会合并，降低对 PigHub 的重复压力。
- 已加载的缩略图会直接复用为选择后的表单预览；只有最终保存时才下载原图并转换为 512×512 PNG。

## v1.6.9 (2026-08-02)
### 修复
- 修复管理面板趋势折线的 X 坐标计算优先级错误：最后数日的数据点不再被绘制到 SVG 范围外并被裁切，已有用户／解锁数据会正常显示。

### 元数据
- 显示名称改为「今日小豬 · 增強版」，描述明确为独立维护 fork；内部插件 ID `astrbot_plugin_rollpig` 保持不变，以保留既有配置、图鉴、历史数据和管理页路径。

## v1.6.8 (2026-08-02)
### 优化
- `/猪猪帮助`／`/豬豬幫助` 改为发送日夜自适应的帮助图片卡片，替代冗长纯文本；卡片保留全部指令、参数示例、@ 他人开关状态及管理员功能说明。

## v1.6.7 (2026-08-02)
### 新增
- 新增 `/猪猪帮助`／`/豬豬幫助` 指令，集中说明全部聊天指令、页码与搜索参数、料理卡、图鉴，以及管理员同步与管理面板功能。
- 帮助会根据 `at_view_pig` 当前配置明确提示是否可用 `/今日小豬 @某人` 查看他人的今日小猪。

## v1.6.6 (2026-08-02)
### 新增
- 机器人发送的今日小猪、图鉴、随机／搜索结果、周报与烤猪图片新增日夜主题：默认在 19:00-06:59 自动切换为低亮度夜间配色；可通过 `image_theme` 配置固定为 `light` 或 `dark`。

## v1.6.5 (2026-08-02)
### 修复
- 管理图鉴缩略图改为 192×192 RGBA Canvas 像素，完整保留 PNG 透明度和边缘细节；不再将 128px RGB 缩略图放大，卡片预览与编辑页显示一致。

## v1.6.4 (2026-08-02)
### 修复
- 修复统计趋势 SVG 的溢出绘制：图表与 SVG 现在会裁切至卡片范围，零值趋势线不会横跨到热门小猪图表或页面外。

## v1.6.3 (2026-08-02)
### 修复
- 兼容 PigHub 当前的 `/images/` 图片地址（同时保留 `/data/`），图库不再因安全白名单过严而显示为空。
- PigHub 索引读取限制为单入口 12 秒，并在管理页超过 20 秒时明确显示失败原因，不再无限停留在“打开后加载”。
- 云资源默认绕过系统代理直连；已修复失效代理导致 `pig.felislab.cc` TLS 连接超时、一直没有“上次成功”的问题。需要代理的部署可在配置中显式开启。
- 云资源面板新增上次尝试、进行中、成功、未完成与失败的常驻状态说明；同步轮询异常也会显示给管理员。

## v1.6.2 (2026-08-02)
### 修复
- 彻底移除管理图鉴对 `data:`／`blob:` 图片 URL 的依赖，后端改为提供 RGB 缩略像素并由前端 Canvas 直接绘制，兼容 AstrBot 的沙箱 iframe。
- 编辑弹窗沿用 Canvas 显示当前图片；本地上传通过 `createImageBitmap` 直接预览，不再创建 Blob URL。
- PigHub 选图新增服务端安全预览接口，避免跨域或鉴权策略导致预览破图。

## v1.6.1 (2026-08-02)
### 修复
- 修复管理页缩略图在 AstrBot 受限 iframe 中显示为破图与小白条的问题，改用 Blob URL 与固定比例容器。
- 修复首次同步接近两百张云端图片时容易触发 `httpx.ReadTimeout` 的问题。
- 云同步改为后台任务，Dashboard 请求无需等待整包下载完成。
- 图片下载改为 4 路并发、至少 45 秒读取窗口与最多 3 次退避重试。
- 网络异常现在显示可读原因；旧缓存、本地图鉴覆盖与删除屏蔽继续保留。

## v1.6.0 (2026-08-02)
### 新增
- 新增公有小猪云资源同步，兼容 rollpig-plus 的版本化 manifest、尺寸与 SHA-256 校验。
- 新增“云端／内置基础层 → 本地管理覆盖层 → 删除屏蔽层”的图鉴合并策略。
- 管理面板新增云资源状态、手动同步以及 `/同步小猪资源` 管理员指令。
- 新增 PigHub 图片挑选器，可搜索／分页／随机浏览图片，再手动填写名称、描述与文案。

### 安全与稳定性
- 云资源先下载到暂存目录，全部校验成功后才原子替换；失败继续使用旧缓存或内置资源。
- PigHub 图片由服务端从受信任的 `pighub.top/data/` 下载，统一校验并转为 512×512 PNG。
- 旧版整份本地图鉴会自动迁移为覆盖层与删除屏蔽，不丢失管理员已有修改。

## v1.5.0 (2026-08-02)
### 新增
- 新增昨日小猪、明日预测、本周小猪周报。
- 新增本地随机小猪与多字段找猪功能。
- 新增重复抽取 EX Lv.、本命猪与连续重复渐进保底。
- 新增纯本地今日烤猪料理卡，不依赖外部 AI 服务。
- 永久历史按日期保存实际抽取结果，为周报和昨日查询提供数据。

### 优化
- 调整我的猪圈卡片与页脚间距，并丰富成长摘要。

## v1.4.0 (2026-08-02)
### 新增
- `/今日小猪` 同时兼容繁体、简体指令与常用别名。
- 新增 `/我的猪圈 [页码]` 永久解锁图鉴，兼容 `/我的豬圈`。
- 新增 AstrBot Plugin Page 管理面板，支持小猪素材的一条龙新增、编辑和删除。
- 上传图片自动校验、居中裁切并转换为 512×512 PNG。
- 新增使用人数、抽取次数、平均解锁率、趋势与热门小猪统计。

## v1.3.0 (2026-07-25)
### 新增
- 新增多款小猪形象素材，丰富随机抽取结果池。
