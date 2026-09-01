# Bundled lineage 手写 EX 文案层

本页记录非 Felis 小猪逐步脱离 deterministic generic EX baseline 的维护边界。

## 为什么单独做这一层

当前运行时会先为 active catalog 中每只小猪生成 deterministic EX1–EX5 安全基线。它保证任何 bundled、cloud-only、未来新增或管理员本地内容都有完整 EX 展示，但通用的「开始养熟／熟客上线／招牌常驻」等阶段句并不适合作为长期最终文案。

因此仓库使用 `resource/bundled_ex_copy*.json` 保存本项目重新创作的逐猪、逐级 text-only EX 文案。首两批集中在 `resource/bundled_ex_copy.json`，后续批次拆成同 provenance 分片；loader 会按文件名顺序合并，并对重复 ID 直接 fail-closed。这样逐批维护时无需反复整体替换已经很长的 authoring 文件，也降低误覆盖历史手写内容的风险。

它和 Felis 34 项的 `resource/felis_direct_ex_copy.json` 是两条不同 provenance 边界。

## Provenance 边界

每个 `bundled_ex_copy*.json` 必须满足：

- `provenance.scope = bundled-lineage-text-only`；
- `quarantined_ex_used = false`；
- 只能引用当前 `resource/pig.json` 中存在的 ID；
- 每只已手写小猪必须完整提供 EX1–EX5；
- 每级只允许 `description` 与 `analysis`，不允许 `image`；
- 五级短描述和完整文案都必须逐级不同；
- 不同分片不得重复定义同一个 pig ID。

2026-08-19 provenance remediation 隔离的历史 authored `resource/pig_ex_variants.json` 与 `resource/ex_curated/` **不会因为本计划恢复**。新的手写层从现行 base 名称、描述、analysis、实际图片与可核验的角色／网络语境重新创作，不把旧隔离 corpus 当素材来源。

## Active catalog 口径

不要把仓库 bundled catalog 数量直接等同于历史生产 public source 的 allow-list 数量。

历史 provenance 记录曾审计出 204 个 production canonical records，其中 157 allow、47 quarantine；但当前公开仓库并不保存那份生产 allow-list 的完整 canonical ID 清单。因此本手写层采取更窄、可证明的策略：

1. authoring 只接受 `resource/pig.json` 已有 lineage ID；
2. runtime 只对当前 active catalog 中同 ID 的项目生效；
3. cloud-only、未来新增或尚未完成 lineage review 的 ID 继续使用 deterministic baseline；
4. 如果以后取得新的可审计 active ID 来源，再单独扩展 authoring scope，而不是猜测历史 157 项。

## 长期目标：公共猪源全量重修

当前 Phase 只处理仓库中能够逐项核对图片与 base 文案的 99 个 bundled lineage ID；长期目标则是把**当前公共猪源实际发布的每只猪**都按同一标准重新审查和重写。

公共猪源阶段不会直接沿用历史「157 allow」这个数量当清单，也不会把下载得到的图片自动视为可再分发或可改写。正式扩展前必须先取得可审计的当前 manifest／catalog，并为每个公共源 ID 同时确认：

1. 当前实际图片与 base `name / description / analysis`；
2. item-level provenance 与再分发／改写边界；
3. 是否已有 bundled 或 Felis authoring，避免重复定义；
4. 原文涉及的作品、网络、饮食或典故是否能查证；
5. 未能确认出处时，只写画面与现有文本能够支持的内容。

公共源新增 ID 会采用独立、可追踪的 authoring 边界接入，而不是塞进 `bundled-lineage-text-only` 冒充 bundled 内容。

## Runtime 优先级

EX 展示文案按以下方向叠加：

1. deterministic generic baseline；
2. 当前来源中合法的 cloud／bundled variant；
3. `bundled-lineage-text-only` 项目手写层；
4. Felis 34 项独立 `felis-direct-text-only` 手写层；
5. 管理员 local override 保持最高优先级。

因此开始手写非 Felis 文案不会破坏未完成小猪的安全兜底，也不会让 bundled layer 越权覆盖 Felis 隔离层或管理员本地编辑。

## 当前进度

已完成 **99 / 99 个 bundled lineage ID × 5 级 = 495 组**独立 EX 文案。当前 `resource/pig.json` 中不再有 bundled ID 依赖 generic baseline 作为最终展示文案；deterministic baseline 继续只为 cloud-only、未来新增和非 bundled lineage 的 active ID 提供安全兜底。

### Phase 1

- `human`
- `pig`
- `zhuge-liang`
- `zombie-pig`
- `skeleton-pig`
- `explosive-pig`
- `magic-pig`
- `mechanical-pig`

### Phase 2

- `little-red-pig`
- `streamer-pig`
- `repeater-pig`
- `early-class-pig`
- `pigsleep`
- `error-404-pig`
- `apple-pig`
- `android-pig`

Phase 2 对「种草／直播榜一／群聊复读／早八人」等网络语境先做实际用法核对，再回到 base 小猪笑点写 EX1–EX5；手机系的 `apple-pig` 与 `android-pig` 则分别沿极简高价／生态绑定和开发者选项／刷机折腾两套角色逻辑发展，不写阵营口号。

### Phase 3

- `leek-pig`
- `lemon-pig`
- `teammate-pig`
- `goblin-pig`
- `protagonist-pig`
- `pig-die`
- `watermelon-pig`
- `spider-pig`

Phase 3 在写作前直接核对当前 Resource Source 中对应 PNG 与 `resource/pig.json` base 语义，并补查「割韭菜／我酸了／吃瓜群众／哥布林模式」等实际网络语境。文案仍以图中物理笑点为主：韭菜猪围绕「被割又长」、柠檬猪围绕嘴硬式羡慕、猪队友围绕游戏团灭、猪布林围绕退社交式邋遢宅居、猪角围绕自带聚光灯的主角病、猪骰围绕六面随机决策、西瓜猪把「吃瓜群众」反转成「瓜吃群众」、蜘蛛则把八条腿和软件 Bug／Issue 生态绑定。

### Phase 4

- `landmine-pig`
- `big-lazy-pig`
- `pig-turtle`
- `fishing-pig`
- `stuck-pig`
- `abstract-pig`
- `computer-pig`
- `study-pig`

Phase 4 同样先直接查看当前 Resource Source 的实际 PNG。`landmine-pig` 的黑发发夹与成箱粉色功能饮料对应地雷系／滴泪系视觉语境，但文案不把穿搭风格等同于真实心理状态，只写造型、饮料、凌晨群聊和「没事」反差；`big-lazy-pig` 沿「躺平」的少卷／休息语境发展；`fishing-pig` 同时利用网络「摸鱼」的上班偷闲含义和图中脚踩真鱼的字面笑点。其余五只以图像物理笑点为主：猪龟缩壳躲事、卡猪和门框物理冲突、抽象猪低多边形建模、计算猪老式 CRT／慢算力、学习猪读《猪肉烹饪大全》后越学越怕。

### Phase 5

- `bandage-pig`
- `homebody-pig`
- `roasted-pig`
- `bacon`
- `coder-pig`
- `delivery-pig`
- `dirty-pig`
- `clean-pig`

Phase 5 继续以实际 PNG 为主。`bandage-pig` 把网络「绷不住了」和全身绷带的物理「绷不住」叠成双关；`homebody-pig` 写舒适宅家而不重复猪布林的脏乱退社交；`roasted-pig` 与 `bacon` 分别沿整猪上火和条状下锅做「熟／煎熬」字面化；`coder-pig` 刻意避开 Felis `coding-pig` 的屎山／warning 路线，改写本地正常、清缓存、测试不现线上必现、周五发版；`delivery-pig` 玩快递箱易碎／此面朝上与箱中活猪；`dirty-pig` 和 `clean-pig` 则用泥膜原厂漆与浴缸小黄鸭做互相对照的猪圈卫生两极。

### Phase 6

- `pig-stamp`
- `pig-human`
- `demon-pig`
- `heaven-pig`
- `pig-ball`
- `cyberpunk-pig`
- `piggy-bank`
- `world-ruler-pig`

Phase 6 继续围绕可见造型和字面反差创作：`pig-stamp` 把头顶印章发展成猪圈审批窗口；`pig-human` 用西装人身与猪脸处理身份字段冲突；`demon-pig` 与 `heaven-pig` 分别写恶作剧供应商和飞升后仍抢红包／打卡；`pig-ball` 把「滚」变成会被物理执行的命令；`cyberpunk-pig` 以 RGB、固件、散热与低电量拆解赛博外壳；`piggy-bank` 围绕只进不出的强制储蓄；`world-ruler-pig` 则用坐地球、喝奶瓶与午睡制造幼年统治者反差。

### Phase 7（塔菲语义纠偏）

- `taffy-pig`

`taffy-pig` 的实际图片是粉发、护目镜与光环的永雏塔菲造型，base 文案也直接使用「关注永猪塔菲谢谢喵」。本阶段据此回到大陆 V 圈的「永厨塔菲／永远喜欢塔菲」应援语境，并使用「关注塔菲谢谢喵」「雏草姬」「塔不灭」等已核对的塔菲社群用语；不再把这只猪的核心笑点误写成 1885 年发明家、侦探或时光机设定。

### Phase 8

- `black-pig`
- `wild-boar`
- `black-white-pig`
- `pork-skewer`
- `doll-pig`
- `soul-pig`
- `crystal-pig`
- `snow-pig`

Phase 8 先逐只查看实际图片，再回读现行 base 文案并查证可能的外部语境：

- `black-pig` 只沿全黑猪身、粉鼻与暗黑模式发展，保留 base「卤过头」的视觉笑点，不把毛色写成人格判断；
- `wild-boar` 结合画面中的鬃毛、獠牙，以及野猪会拱土觅食的行为；「猪突猛进」按“不顾四周、猛烈直冲”的原义使用，不假装成特定动漫角色；
- `black-white-pig` 虽容易让人联想到 San-X 的 Monokuro Boo，但实际素材是单只左右分色猪，不是官方黑白双猪造型，因此只写黑白拼装、熊猫／奶牛认亲与相机测光；
- `pork-skewer` 同时使用竹签上的字面「串」和网络「串子／反串／带节奏」含义，最终明确“只带孜然，不带节奏”；
- `doll-pig` 的 base 写作 `fufu小猪`，但实际图像是带针脚、补丁与 Hand Made 标签的普通手作布偶；考虑到「ふわぷち／fufu」也可能特指既有玩偶品牌或社群叫法，正文不擅自认领任何 IP；
- `soul-pig` 只围绕半透明绿色猪影、幽灵尾巴与“没吃完的饲料”执念发展；
- `crystal-pig` 使用晶面折射和展品感，并准确区分抗刮的硬度与抗碎裂的韧性；
- `snow-pig` 的图片是纯白猪而不是雪人，因此只写白色轮廓、雪地保护色和相机白平衡，不硬加融化、胡萝卜或雪人设定。

### Phase 9

- `pig-cat`
- `rainbow-pig`
- `pig-bun`
- `taxi-pig`
- `pig-souffle`
- `chained_crown_pig`
- `vangogh_pig`
- `tangyuan_pig`

Phase 9 同样先检查仓库实际图片与现行 base 文案，再处理名称可能隐藏的谐音、作品或食物机制：

- `pig-cat` 的橘猫条纹、尖耳、胡须与猪鼻、卷尾同时存在，因此沿「猪咪」双物种冲突发展，不把它认成某个具体猫角色；
- `rainbow-pig` 保留 base 的正式全名「斯图亚特·彩虹猪」和“大色猪”双关；没有找到足以确认既有角色 IP 的证据，所以只写七色渐变、色相与饱和度，也不因彩虹配色擅自加入其他身份象征；
- `pig-bun` 的图像明确是带收口褶的蒸包造型，但看不出具体馅料，因此只写蒸笼、热气、软皮与内馅，不指定猪肉包或其他口味；
- `taxi-pig` 直接使用「出租车／出猪车」谐音，并围绕黄色车身、TAXI 灯牌、方向盘、起步价、计价器与深夜最后一单展开；
- `pig-souffle` 实际是顶有奶油和两颗蓝莓的厚松饼式猪芙蕾；文案按打发蛋白形成网络包住气泡、受热膨胀及离锅后逐渐回落的机制递进；
- `chained_crown_pig` 把 base「欲戴王冠，必承其重」和画面中的王冠、手铐、脚链做物理化处理；不把这句中文流行表达错误标成莎士比亚原句，莎士比亚文本中的相关句子实际是 `Uneasy lies the head that wears a crown`；
- `vangogh_pig` 以《星月夜》蓝黄对比、翻卷旋涡、短笔触和厚涂感为核心；图片左右耳完整，因此只轻点一次耳朵典故，不拿艺术家的精神痛苦当笑料；
- `tangyuan_pig` 延续「黑芝麻／黑猪麻」换字谐音，并使用图中白汤圆、勺上黑芝麻馅与汤圆所承载的团圆语境，不额外发明品牌或地区口味。

### Phase 10

- `mc_porkchop`
- `pig_god`
- `tank_pig`
- `lao_zhu_li`
- `invisible_pig`
- `buddha-pig`
- `frozen-pig`

Phase 10 对游戏数值、图片透明层、宗教用物和可能带攻击性的网络衍生梗做了额外边界检查：

- `mc_porkchop` 的实际图像就是《我的世界》风格熟猪排；当前数据中 `cooked_porkchop` 恢复 8 点饥饿、提供 12.8 点饱和度并可堆叠 64，因此五级沿像素图标、四个鸡腿、隐藏饱和度、整组堆叠和生存背包主食展开；
- `pig_god` 的图像能确认白袍、翅膀、光环、闭眼和星星法杖，但看不到 base 所写的祥云，也没有可靠的既有神话／角色来源，因此只写猪圈求智慧、考试、抽卡与“神不代写”；
- `tank_pig` 保留图片正中央的「按 F 进入」载具交互、履带、X 眼和无炮塔猪头；网络上这句另有攻击他人体型的侮辱性衍生，本项目明确不采用，只保留画面中的字面驾驶语义；
- `lao_zhu_li` 使用白胡子和「资历／猪历」谐音发展版本史老前辈；虽然网络上可找到复用同一猪图的网站，也没有证据证明当前素材与该网站功能存在 authoring 关系，因此不写题库、刷题或考试答案；
- `invisible_pig` 的原图不是只剩一个鼻子，而是躯干和四腿被 alpha 通道隐藏，粉耳、黑眼与粉鼻仍可见；文案据此使用图层、透明通道、坐标与碰撞箱；
- `buddha-pig` 的画面是金色合十双手和一圈猪头念珠，核心双关为「佛珠／佛猪」「施主／施猪」；念珠只按持念计数与收摄注意的用途写，避免以贬损词汇处理宗教修习；
- `frozen-pig` 明确是带雪花、冰霜与 X 眼的猪形冰块，五级只写物理低温、待机和解冻进度，不继续沿用可能被理解为操作建议的“微波解冻”。

### Phase 11

- `pearl-pig`
- `apple-of-eye-pig`
- `chocolate-pig`
- `jewelry-pig`
- `juliet-pig`
- `char-siu`
- `pork-floss`
- `suckling-pig`

Phase 11 集中处理珠／猪、粤语音译、文学角色和真实食物工序，同时纠正多处 base analysis 对图片的误读：

- `pearl-pig` 的实际图片不是“小猪顶着一颗珍珠”，而是珠光猪本身躺在打开的贝壳里；文案以「珍珠／珍猪」谐音、贝壳、虹彩和珠母质层叠形成光泽发展，并把真假鉴定落到物种栏冲突；
- `apple-of-eye-pig` 直接把「掌上明珠」换成「掌上明猪」，图中两只黄色手掌也确实托住整只猪；成语按“极受珍爱的人或物”使用，不强行限定性别；
- `chocolate-pig` 以粤语「朱古力＝巧克力」为词根改成「猪古力」，并使用深棕高光与四蹄下方的融化滴落，不写成让真实小猪进食巧克力；
- `jewelry-pig` 不是单纯从耳朵到尾巴挂首饰：粉色猪身本身由宝石棱面组成，另戴黄色粉边王冠和白色珠链，因此沿「珠宝／猪宝」、切面、整体保价和移动展柜展开；
- `juliet-pig` 的图片没有阳台，只有红蝴蝶结和嘴衔玫瑰；文案使用「朱丽叶／猪丽叶」谐音、《罗密欧与朱丽叶》中名字与玫瑰的讨论、蒙太古／凯普莱特家族冲突，并回避复述悲剧中的具体自伤方式；
- `char-siu` 保留粤语家长金句「生块叉烧好过生你」，也核对《食神》中的黯然销魂饭本质是叉烧煎蛋饭；画面则以红褐蜜汁、焦边和整只叉烧猪为锚点，不和脆皮烤乳猪混写；
- `pork-floss` 按肉先煮至纤维松散、顺纹拆丝、调味炒干并搓松起绒的工序发展，再落到面包、粥和饭团等具体使用场景，把 base 的励志句改成真正可见的肉丝团；
- `suckling-pig` 的红苹果实际放在猪背上，而非嘴里；文案使用白盘、绿叶、整猪棕亮表面，以及粤式烤乳猪常见的脆皮水、风干与烤制工序，但不写具体幼龄数字来消费“年纪轻轻”的字面残酷。

### Phase 12

- `everest-pig`
- `burger-pig`
- `chef-pig`
- `prison-break-pig`
- `pig-skin-milk`
- `lard-pig`
- `mini-pig`
- `oreo-pig`
- `salmon-sushi-pig`

Phase 12 处理山峰高程、图片尺寸、品牌恶搞和多种食物工序，并继续纠正 base 文案对实际图片的误读：

- `everest-pig` 的猪身本身就是有冰棱切面的雪峰，粉耳、粉鼻、卷尾和红黄蓝绿方格围巾嵌在山体中；文案使用中尼共同公布的珠峰最新雪面高程 8848.86 米，但不添加图片没有的登山者、旗帜或遇难叙事；
- `burger-pig` 保留 base「生活给我施压，我给自己加片芝士」，并严格按画面中的上下圆面包、绿色生菜、黄色芝士、粉色夹层和作为主层的猪脸发展，不猜测看不出的具体肉饼种类；
- `chef-pig` 的图像只有厨师帽、小桌、花边碗与搅拌／试味餐具，看不到刀具，因此保留「猪厨」「食材眼熟」的职业双关，同时移除旧 analysis 的「刀工精湛」视觉断言；
- `prison-break-pig` 实际是小猪从红屋顶、蓝窗户的小屋敞门走出，不是铁栏监狱；文案回到「出租屋／出猪屋」「不住了／不猪了」的双层换字，并以退租、押金和搬家收束；
- `pig-skin-milk` 明确是「双皮奶／猪皮奶」换字，图片为猪脸大碗和三块猪形奶冻；工序按煮奶放凉形成第一层奶皮、戳皮倒奶、加入蛋清和糖调匀过滤、回碗炖制形成第二层推进，并明确真正猪皮为零；
- `lard-pig` 使用花纹搪瓷碗、白色猪油和带光环飘出的半透明猪魂；炼制过程只写脂肪温和融出、油渣分离、过滤，以及热油淡黄、冷却后转为乳白半固体，不加入营养或健康结论；
- `mini-pig` 不是泛称可爱小猪：当前 240×240 透明画布中的非透明外接框只有 36×32 像素，面积约占整张画布 2%；五级据此写留白、缩放、点名困难和「今日小猪」冠名权；
- `oreo-pig` 的蓝色字样明确写作「猪利猪」「经典猪味」，图像借用两片黑色巧克力饼干夹奶油及扭、舔、泡的熟悉仪式；文案按猪圈品牌恶搞处理，并明确不是官方联名；
- `salmon-sushi-pig` 是整只橙红、带奶白鱼纹的小猪趴在可见米粒的饭块上；握寿司按醋饭上放配料的结构写，保留「三文鱼／三文猪」换字和酱油／孜然冲突，不把整猪误写成一片现切鱼。

### Phase 13

- `bamboo-pig`
- `curator-pig`
- `upper-class-pig`
- `alien-pig`
- `tiramisu-pig`
- `antibacterial-pig`
- `pigskin-pig`
- `muscle-pig`
- `elephant-pig`
- `hanging-pig`

Phase 13 完成最后 10 个 bundled lineage ID，并对谐音、职业潮语、食品词源、广告功效、安全吊运和两处严重图片误读做了最终核对：

- `bamboo-pig` 的实际造型是褐色笋壳包裹的猪身、嫩绿笋尖、粉色五官和金色光环；文案由「猪笋」进入「夺笋啊／多损啊」及「山上的笋都被你夺完了」，始终以真实竹笋造型为物理锚点；
- `curator-pig` 可见白衬衫、细领结、棕色围裙和腰后蝴蝶结，故使用「主理人／猪理人」以及品牌调性、选品和空间打理；EX5 轻点网络对主理人「主打不理人」的调侃，但不把职业本义偷换成单纯高冷；
- `upper-class-pig` 只能确认黑色正式礼服、白衬衫、红领结和卷尾，无法从图片验证资产或家世；因此保留 base 的「请叫我先生」，把「老钱」写成未核验传闻，也不虚构刀叉、酒杯或特定燕尾服剪裁；
- `alien-pig` 只有荧光黄绿色猪身、蓝色猪鼻／色块和黑色旋涡眼，没有飞碟、天线或可识别的既有角色元素；文案保留「来自猪星」但将外星身份标为待核，不硬套任何 IP；
- `tiramisu-pig` 按经典提拉米苏的咖啡浸手指饼、马斯卡彭奶油与可可层次推进，并使用意大利语 `tirami su`「把我拉起来」的词义；图上的香蕉和莓果只作为当前图片摆盘，不冒充经典配方；
- `antibacterial-pig` 的包装确有盾牌、泡沫和 99.9%，但没有对象、条件或检测报告；文案把数字限定为包装美术与「去除不开心」荒诞梗，不作真实抑菌、医疗或疾病预防功效宣称；
- `pigskin-pig` 是扁平灰粉猪皮轮廓、毛边、竖起卷尾和黄色光环；新版把「耗尽了」处理为低功耗、勿扰和休息，不用死亡、自伤或尸体语境消费疲惫；
- `muscle-pig` 可见夸张二头肌、胸肩、腹部、大腿、猪头和细小卷尾；文案保留「问就是练的」与第一百组深蹲的猪圈夸张，同时明确数字不是训练处方；
- `elephant-pig` 实际没有象皮、大耳或真正象鼻，只有普通粉猪把两段大葱插进鼻孔；因此 base 名称与文案同步修正为「装象猪／猪鼻插葱，装相」，完整回到「猪鼻子插大葱——装象（装相）」歇后语；
- `hanging-pig` 的深棕吊带实际绕在躯干前段而非颈部；base 同步改名「吊运猪」，五级按检查吊具、稳定重心、清空悬吊载荷下方、禁止骑乘摇晃和四蹄安全落地展开，明确不是自伤场景。

Bundled lineage **99/99** 至此完成；后续维护只在图片、base 语义或已核验出处发生变化时修订本层。下一阶段转向当前公共猪源独有项，继续使用独立、逐项可审计的 provenance 边界。
