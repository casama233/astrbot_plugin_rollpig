from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"
BOOTSTRAP = ROOT / "pages" / "pig-manager" / "ui-bootstrap.js"
ANALYTICS = ROOT / "pages" / "pig-manager" / "ui-analytics.js"
ANALYTICS_CSS = ROOT / "pages" / "pig-manager" / "analytics-theme.css"
TEST_ASSET = ROOT / "tests" / "test_ui_asset_delivery.py"
TEST_CACHE = ROOT / "tests" / "test_ui_cache_busting.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, got {count}")
    return updated


VERSION = "3.2.0"

# ---------------------------------------------------------------------------
# Lazy analytics bundle: precise labels + high-end microinteraction layer.
# ---------------------------------------------------------------------------
bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
bootstrap = replace_once(
    bootstrap,
    "  const VERSION = '3.1.2';",
    f"  const VERSION = '{VERSION}';",
    "bootstrap version",
)
BOOTSTRAP.write_text(bootstrap, encoding="utf-8")

analytics = ANALYTICS.read_text(encoding="utf-8")
analytics = replace_once(
    analytics,
    "  const VERSION = '3.1.2';",
    f"  const VERSION = '{VERSION}';",
    "analytics version",
)
analytics = replace_once(
    analytics,
    "  const number = new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 1});\n",
    "  const number = new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 1});\n"
    "  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;\n"
    "  const finePointer = window.matchMedia?.('(pointer: fine)')?.matches ?? false;\n",
    "analytics motion capability",
)
analytics = analytics.replace("label: '7 日回访率'", "label: '上期→本期回访率'")
analytics = analytics.replace(
    "note: `新增/回流 ${format(retention.new_current_users)} 人`",
    "note: `本期独有活跃 ${format(retention.new_current_users)} 人`",
)
analytics = analytics.replace(
    "['累计抽取', current.draws, previous.draws]",
    "['周期抽取', current.draws, previous.draws]",
)
analytics = analytics.replace(
    "${cardHead('Audience', '回访与新增用户')}",
    "${cardHead('Audience', '回访与周期独有活跃')}",
)
analytics = analytics.replace(
    '<span>7 日回访率</span>', '<span>上期→本期回访率</span>'
)
analytics = analytics.replace(
    '<div><dt>本期新增/回流</dt><dd>${format(retention.new_current_users)}</dd></div>',
    '<div><dt>本期独有活跃</dt><dd>${format(retention.new_current_users)}</dd></div>',
)
analytics = analytics.replace("'平台用户构成'", "'平台身份构成'")

old_ai = '''    const totalAi = Number(ai.ready || 0) + Number(ai.failed || 0) + Number(ai.generating || 0);\n    const success = totalAi ? Number(ai.ready || 0) / totalAi * 100 : 0;\n'''
new_ai = '''    const completedAi = Number(ai.ready || 0) + Number(ai.failed || 0);\n    const success = completedAi ? Number(ai.ready || 0) / completedAi * 100 : 0;\n'''
analytics = replace_once(analytics, old_ai, new_ai, "AI completed denominator")
analytics = replace_once(
    analytics,
    '''        <div><span>AI 失败</span><strong>${format(ai.failed)}</strong></div>\n      </div>\n      <div class="ai-health"><div><span>AI 文案成功率</span><b>${percent(success)}</b></div><i><em style="width:${Math.max(0, Math.min(100, success)).toFixed(2)}%"></em></i></div>`;\n''',
    '''        <div><span>AI 失败</span><strong>${format(ai.failed)}</strong></div>\n      </div>\n      <div class="ai-health"><div><span>AI 文案成功率 · 已完成样本</span><b>${percent(success)}</b></div><i><em style="width:${Math.max(0, Math.min(100, success)).toFixed(2)}%"></em></i><small>生成中 ${format(ai.generating)} 次，不计入成功率分母</small></div>`;\n''',
    "AI denominator disclosure",
)
analytics = analytics.replace(
    "data.source === 'normalized-sql' ? 'SQL 实时聚合' : 'JSON 兼容统计'",
    "data.source === 'normalized-sql' ? 'SQL 事实聚合' : 'JSON 兼容统计'",
)

motion_helper = r'''
  function installAnalyticsMotion() {
    if (reducedMotion || !finePointer) return;
    document.querySelectorAll('#analyticsSuite .analytics-card, #analyticsSuite .analytics-kpi').forEach(card => {
      if (card.dataset.motionBound === '1') return;
      card.dataset.motionBound = '1';
      let frame = 0;
      card.addEventListener('pointermove', event => {
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          const rect = card.getBoundingClientRect();
          const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
          const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
          card.style.setProperty('--spot-x', `${x}px`);
          card.style.setProperty('--spot-y', `${y}px`);
          const tiltX = ((y / Math.max(1, rect.height)) - .5) * -2.2;
          const tiltY = ((x / Math.max(1, rect.width)) - .5) * 2.2;
          card.style.setProperty('--tilt-x', `${tiltX.toFixed(2)}deg`);
          card.style.setProperty('--tilt-y', `${tiltY.toFixed(2)}deg`);
        });
      }, {passive: true, signal: abortController.signal});
      card.addEventListener('pointerleave', () => {
        card.style.setProperty('--tilt-x', '0deg');
        card.style.setProperty('--tilt-y', '0deg');
      }, {passive: true, signal: abortController.signal});
    });
  }
'''
analytics = replace_once(
    analytics,
    "\n  function render(data) {\n",
    motion_helper + "\n  function render(data) {\n",
    "analytics motion helper",
)
analytics = replace_once(
    analytics,
    "    renderOperations(data);\n    const source = document.getElementById('analyticsSource');\n",
    "    renderOperations(data);\n    installAnalyticsMotion();\n    const source = document.getElementById('analyticsSource');\n",
    "analytics motion install",
)
ANALYTICS.write_text(analytics, encoding="utf-8")

css = ANALYTICS_CSS.read_text(encoding="utf-8")
immersive_css = r'''

/* v3.2.0 spectral telemetry — visual only; values remain server facts. */
.analytics-suite {
  position: relative;
  isolation: isolate;
  background:
    radial-gradient(circle at 10% -12%, color-mix(in srgb, var(--pink) 15%, transparent), transparent 34rem),
    radial-gradient(circle at 92% 4%, color-mix(in srgb, var(--analytics-cyan) 12%, transparent), transparent 30rem),
    linear-gradient(145deg, color-mix(in srgb, var(--surface) 97%, transparent), color-mix(in srgb, var(--surface-strong) 96%, var(--pink-soft)));
  box-shadow:
    0 24px 70px color-mix(in srgb, var(--pink) 7%, transparent),
    var(--shadow-soft);
}

.analytics-suite::before {
  inset: 0;
  background-image:
    linear-gradient(color-mix(in srgb, var(--analytics-grid) 58%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--analytics-grid) 58%, transparent) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(to bottom, rgba(0,0,0,.7), transparent 72%);
  opacity: .34;
  z-index: -2;
}

.analytics-suite::after {
  content: "";
  position: absolute;
  z-index: -1;
  width: 420px;
  height: 420px;
  right: -230px;
  top: -230px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--analytics-purple) 28%, transparent);
  box-shadow:
    0 0 0 46px color-mix(in srgb, var(--analytics-purple) 3%, transparent),
    0 0 90px color-mix(in srgb, var(--analytics-cyan) 10%, transparent);
  animation: analyticsOrbit 18s linear infinite;
}

.analytics-live i {
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--green) 12%, transparent),
    0 0 16px color-mix(in srgb, var(--green) 42%, transparent);
  animation: analyticsBeacon 2.4s ease-in-out infinite;
}

.analytics-kpi,
.analytics-card {
  --spot-x: 50%;
  --spot-y: 50%;
  --tilt-x: 0deg;
  --tilt-y: 0deg;
  position: relative;
  isolation: isolate;
  transform: perspective(900px) rotateX(var(--tilt-x)) rotateY(var(--tilt-y));
  transform-style: preserve-3d;
  transition:
    transform .22s var(--ease),
    border-color .22s var(--ease),
    box-shadow .22s var(--ease);
}

.analytics-kpi::before,
.analytics-card::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  border-radius: inherit;
  background: radial-gradient(
    240px circle at var(--spot-x) var(--spot-y),
    color-mix(in srgb, var(--analytics-cyan) 13%, transparent),
    color-mix(in srgb, var(--pink) 5%, transparent) 34%,
    transparent 70%
  );
  opacity: 0;
  transition: opacity .2s var(--ease);
}

.analytics-kpi:hover::before,
.analytics-card:hover::before { opacity: 1; }

.analytics-kpi:hover,
.analytics-card:hover {
  border-color: color-mix(in srgb, var(--analytics-cyan) 30%, var(--line));
  box-shadow:
    0 15px 34px rgba(18, 24, 40, .08),
    0 0 0 1px color-mix(in srgb, var(--analytics-purple) 8%, transparent);
}

.analytics-kpi {
  animation: analyticsCardReveal .55s both var(--ease);
}
.analytics-kpi:nth-child(2) { animation-delay: 45ms; }
.analytics-kpi:nth-child(3) { animation-delay: 90ms; }
.analytics-kpi:nth-child(4) { animation-delay: 135ms; }

.analytics-card { animation: analyticsCardReveal .62s both var(--ease); }
.analytics-card:nth-child(2) { animation-delay: 55ms; }
.analytics-card:nth-child(3) { animation-delay: 95ms; }
.analytics-card:nth-child(4) { animation-delay: 135ms; }
.analytics-card:nth-child(5) { animation-delay: 175ms; }
.analytics-card:nth-child(6) { animation-delay: 215ms; }
.analytics-card:nth-child(7) { animation-delay: 255ms; }

.analytics-kpi__row strong,
.retention-ring strong,
.operations-grid strong {
  text-shadow: 0 0 24px color-mix(in srgb, var(--pink) 13%, transparent);
}

.activity-cell i {
  box-shadow: inset 0 0 14px color-mix(in srgb, var(--pink) calc(var(--intensity) * 22%), transparent);
  animation: analyticsHeatReveal .4s both var(--ease);
}
.activity-cell:nth-child(4n + 2) i { animation-delay: 35ms; }
.activity-cell:nth-child(4n + 3) i { animation-delay: 70ms; }
.activity-cell:nth-child(4n + 4) i { animation-delay: 105ms; }

.retention-ring {
  position: relative;
  filter: drop-shadow(0 8px 20px color-mix(in srgb, var(--pink) 15%, transparent));
}
.retention-ring::after {
  content: "";
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--analytics-cyan) 24%, transparent);
  border-top-color: color-mix(in srgb, var(--analytics-cyan) 68%, transparent);
  animation: analyticsSpin 6s linear infinite;
}

.compare-bars i:first-child,
.platform-row em,
.ai-health em {
  position: relative;
  overflow: hidden;
}
.compare-bars i:first-child::after,
.platform-row em::after,
.ai-health em::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-130%);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.48), transparent);
  animation: analyticsSweep 3.2s ease-in-out infinite;
}

.rising-table__row {
  transition: transform .18s var(--ease), background .18s var(--ease), border-color .18s var(--ease);
}
.rising-table__row:hover {
  transform: translateX(4px);
  background: color-mix(in srgb, var(--analytics-cyan) 5%, var(--surface-strong));
}

.ai-health small {
  display: block;
  margin-top: 7px;
  color: var(--muted);
  font-size: 11px;
}

@keyframes analyticsCardReveal {
  from { opacity: 0; transform: perspective(900px) translateY(14px) scale(.985); filter: blur(4px); }
  to { opacity: 1; transform: perspective(900px) translateY(0) scale(1); filter: blur(0); }
}
@keyframes analyticsHeatReveal { from { opacity: .15; transform: scale(.72); } to { opacity: 1; transform: scale(1); } }
@keyframes analyticsBeacon { 50% { opacity: .58; transform: scale(.78); } }
@keyframes analyticsOrbit { to { transform: rotate(360deg); } }
@keyframes analyticsSpin { to { transform: rotate(360deg); } }
@keyframes analyticsSweep { 55%, 100% { transform: translateX(150%); } }

@media (prefers-reduced-motion: reduce) {
  .analytics-suite::after,
  .analytics-live i,
  .analytics-kpi,
  .analytics-card,
  .activity-cell i,
  .retention-ring::after,
  .compare-bars i:first-child::after,
  .platform-row em::after,
  .ai-health em::after {
    animation: none !important;
  }
  .analytics-kpi,
  .analytics-card,
  .rising-table__row,
  .activity-cell i {
    transform: none !important;
    transition-duration: .01ms !important;
  }
}
'''
if "/* v3.2.0 spectral telemetry" not in css:
    css += immersive_css
ANALYTICS_CSS.write_text(css, encoding="utf-8")


# ---------------------------------------------------------------------------
# Core dashboard: truthful visual grammar + richer motion.
# ---------------------------------------------------------------------------
page = PAGE.read_text(encoding="utf-8")
page = page.replace("Pig Intelligence · Live", "Pig Intelligence · Local Snapshot")
page = page.replace(
    "把抽取、活跃与收藏变成会呼吸的数据。所有趋势均来自本地统计，不上传群友资料。",
    "把抽取、活跃与收藏变成会呼吸的数据。每次刷新都按本地事实重算，不上传群友资料。",
)
page = replace_once(
    page,
    '<div class="panel-desc" id="heroInsight">正在整理今日猪圈动态…</div></div>',
    '<div class="panel-desc" id="heroInsight">正在整理今日猪圈动态…</div><div class="overview-scope" id="overviewScope">正在确认统计口径…</div></div>',
    "overview scope pill",
)
page = replace_once(
    page,
    '<span><i class="dot" style="background:var(--pink)"></i>使用人数</span><span><i class="dot" style="background:var(--violet)"></i>新解锁</span>',
    '<span><i class="dot" style="background:var(--pink)"></i>使用人数</span><span><i class="dot" style="background:var(--blue)"></i>抽取次数</span><span><i class="dot" style="background:var(--violet)"></i>新解锁</span>',
    "trend legend draws",
)

trend_function = r'''function renderTrend(data){
  const root=$('trendChart'),w=840,h=300,padX=42,padY=34;
  if(!data.length){root.innerHTML='<div class="empty">暂无历史趋势数据</div>';return}
  const users=data.map(x=>Number(x.users)||0),draws=data.map(x=>Number(x.draws)||0),unlocks=data.map(x=>Number(x.new_unlocks)||0);
  const max=Math.max(1,...users,...draws,...unlocks),userLine=linePath(users,w,h,padX,max),unlockLine=linePath(unlocks,w,h,padX,max),base=h-padY,userArea=`${userLine} L ${w-padX} ${base} L ${padX} ${base} Z`,step=(w-padX*2)/Math.max(1,data.length-1),barWidth=Math.max(8,Math.min(24,step*.34));
  let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="近十四日使用人数、抽取次数与新解锁趋势"><defs><linearGradient id="trendArea" x1="0" y1="0" x2="0" y2="1"><stop stop-color="var(--pink)" stop-opacity=".38"/><stop offset="1" stop-color="var(--pink)" stop-opacity="0"/></linearGradient><linearGradient id="drawBars" x1="0" y1="0" x2="0" y2="1"><stop stop-color="var(--blue)" stop-opacity=".42"/><stop offset="1" stop-color="var(--blue)" stop-opacity=".08"/></linearGradient></defs>`;
  for(let i=0;i<5;i++){const y=padY+i*(h-padY*2)/4;svg+=`<line class="gridline" x1="${padX}" y1="${y}" x2="${w-padX}" y2="${y}"/><text class="chart-label" x="5" y="${y+4}">${Math.round(max*(1-i/4))}</text>`}
  data.forEach((entry,i)=>{const px=padX+i*(w-padX*2)/Math.max(1,data.length-1),value=draws[i],barHeight=value/max*(h-padY*2);svg+=`<rect class="chart-draw-bar" x="${px-barWidth/2}" y="${base-barHeight}" width="${barWidth}" height="${barHeight}" rx="${Math.min(6,barWidth/2)}" fill="url(#drawBars)" style="--delay:${i*28}ms"/>`});
  svg+=`<path class="chart-area" d="${userArea}" fill="url(#trendArea)"/><path class="chart-path" d="${userLine}" stroke="var(--pink)" stroke-width="4"/><path class="chart-path" d="${unlockLine}" stroke="var(--violet)" stroke-width="3"/>`;
  data.forEach((x,i)=>{const px=padX+i*(w-padX*2)/Math.max(1,data.length-1);svg+=`<text class="chart-label" text-anchor="middle" x="${px}" y="${h-7}">${esc(x.date)}</text>`});
  root.innerHTML=svg+'</svg><div class="chart-tooltip" id="trendTip"></div>';animateSvgPaths(root);bindTrendPointer(root,data,{w,h,padX,padY,max})
}'''
page = replace_regex_once(
    page,
    r"function renderTrend\(data\)\{.*?(?=\nfunction bindTrendPointer)",
    trend_function,
    "truthful trend chart",
)

metric_helpers = r'''function renderMetricSignal(id,label,progress=null){const root=$(id);if(!root)return;root.classList.add('metric-snapshot-viz');const hasProgress=Number.isFinite(progress),safe=hasProgress?Math.max(0,Math.min(100,Number(progress))):0;root.innerHTML=`<div class="metric-signal" aria-hidden="true"><i></i><i></i><i></i><em ${hasProgress?`style="--progress:${safe}%"`:''}></em></div><span>${esc(label)}</span>`}
function renderMetricVisuals(data){const trend=data.trend||[],users=trend.map(x=>Number(x.users)||0),draws=trend.map(x=>Number(x.draws)||0),metrics=data.metrics||{},totalDraws=Math.max(0,Number(metrics.total_draws)||0),windowDraws=draws.reduce((a,b)=>a+b,0);let running=Math.max(0,totalDraws-windowDraws);const cumulative=draws.map(value=>running+=value),rate=Math.max(0,Math.min(100,Number(metrics.average_unlock_rate)||0));renderMetricSignal('vUsers','逻辑用户快照');renderSpark('vDraws',cumulative,2);renderSpark('vToday',users,3);renderMetricSignal('vPigs','当前可抽取');renderMetricSignal('vAverage','当前覆盖',rate);renderMetricSignal('vRate','当前比例',rate)}
function installImmersiveMotion(){if(reduceMotion||!window.matchMedia?.('(pointer:fine)')?.matches)return;document.querySelectorAll('#view-overview .hero,#view-overview .metric,#view-overview .panel').forEach(card=>{if(card.dataset.motionBound==='1')return;card.dataset.motionBound='1';let frame=0;card.addEventListener('pointermove',event=>{if(frame)cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const rect=card.getBoundingClientRect(),x=Math.max(0,Math.min(rect.width,event.clientX-rect.left)),y=Math.max(0,Math.min(rect.height,event.clientY-rect.top));card.style.setProperty('--mx',`${x}px`);card.style.setProperty('--my',`${y}px`);if(card.classList.contains('metric')){card.style.setProperty('--rx',`${(((y/Math.max(1,rect.height))-.5)*-3).toFixed(2)}deg`);card.style.setProperty('--ry',`${(((x/Math.max(1,rect.width))-.5)*3).toFixed(2)}deg`)}})} ,{passive:true});card.addEventListener('pointerleave',()=>{card.style.setProperty('--rx','0deg');card.style.setProperty('--ry','0deg')},{passive:true})})}'''
page = replace_regex_once(
    page,
    r"function renderMetricVisuals\(data\)\{.*?\}\nasync function loadOverview",
    metric_helpers + "\nasync function loadOverview",
    "truthful metric visuals",
)

old_load = "$('heroInsight').textContent=m.today_users?`今天已有 ${m.today_users} 位群友踏进猪圈。数据正在实时生长。`:'今天的猪圈还很安静，等待第一位群友抽取。';"
new_load = "$('heroInsight').textContent=m.today_users?`今天已有 ${m.today_users} 位群友踏进猪圈。本地事实快照已更新。`:'今天的猪圈还很安静；本地事实快照已更新。';const meta=d.meta||{},source=meta.source==='normalized-sql'?'SQL 规范化事实':'JSON 兼容事实';$('overviewScope').textContent=`${source} · Claim-aware 身份 · ${Number(meta.trend_days||14)} 日窗口 · ${meta.as_of||'当前'}`;"
page = replace_once(page, old_load, new_load, "overview snapshot wording")
page = replace_once(
    page,
    "renderMetricVisuals(d);renderTrend(d.trend||[]);renderBars(d.top_pigs||[])}",
    "renderMetricVisuals(d);renderTrend(d.trend||[]);renderBars(d.top_pigs||[]);installImmersiveMotion()}",
    "install core motion",
)

core_css = r'''

/* v3.2.0 immersive overview — motion never carries exclusive meaning. */
#view-overview .hero,
#view-overview .metric,
#view-overview .panel {
  --mx: 50%;
  --my: 50%;
  --rx: 0deg;
  --ry: 0deg;
  isolation: isolate;
}

#view-overview .hero {
  background:
    radial-gradient(520px circle at var(--mx) var(--my), color-mix(in srgb, var(--pink) 12%, transparent), transparent 62%),
    radial-gradient(circle at 88% -18%, color-mix(in srgb, var(--violet) 18%, transparent), transparent 26rem),
    linear-gradient(112deg, color-mix(in srgb, var(--surface-strong) 96%, transparent), color-mix(in srgb, var(--pink-soft) 52%, var(--surface-strong)));
  box-shadow:
    0 28px 70px color-mix(in srgb, var(--pink) 7%, transparent),
    var(--shadow-soft);
}

#view-overview .hero-copy::after {
  content: "";
  display: block;
  width: min(340px, 48vw);
  height: 1px;
  margin-top: 19px;
  background: linear-gradient(90deg, var(--pink), var(--violet), transparent);
  box-shadow: 0 0 18px color-mix(in srgb, var(--pink) 34%, transparent);
  transform-origin: left;
  animation: overviewDataBeam 3.8s ease-in-out infinite;
}

.overview-scope {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 26px;
  margin-top: 11px;
  padding: 5px 9px;
  border: 1px solid color-mix(in srgb, var(--green) 24%, var(--line));
  border-radius: 999px;
  background: color-mix(in srgb, var(--green) 5%, var(--surface-strong));
  color: var(--muted);
  font: 600 9.5px/1.25 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: normal;
}
.overview-scope::before {
  content: "";
  width: 6px;
  height: 6px;
  margin-right: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 12px color-mix(in srgb, var(--green) 62%, transparent);
  animation: overviewBeacon 2.2s ease-in-out infinite;
}

#view-overview .metric {
  transform: perspective(760px) rotateX(var(--rx)) rotateY(var(--ry));
  transform-style: preserve-3d;
  background:
    radial-gradient(180px circle at var(--mx) var(--my), color-mix(in srgb, var(--tone, var(--pink)) 10%, transparent), transparent 72%),
    var(--surface);
  overflow: hidden;
  transition: transform .2s var(--ease), border-color .2s var(--ease), box-shadow .2s var(--ease);
}
#view-overview .metric::before {
  content: "";
  position: absolute;
  inset: -1px;
  z-index: -1;
  border-radius: inherit;
  background: conic-gradient(from 180deg at 50% 50%, transparent 0 34%, color-mix(in srgb, var(--tone, var(--pink)) 30%, transparent) 44%, transparent 54% 100%);
  opacity: 0;
  animation: overviewSpectral 7s linear infinite;
  transition: opacity .22s var(--ease);
}
#view-overview .metric:hover::before { opacity: .6; }
#view-overview .metric:hover {
  box-shadow:
    0 18px 34px rgba(20, 28, 44, .10),
    0 0 26px color-mix(in srgb, var(--tone, var(--pink)) 9%, transparent);
}
#view-overview .metric .value { transform: translateZ(22px); }
#view-overview .metric .metric-top { transform: translateZ(12px); }

.metric-snapshot-viz {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
}
.metric-snapshot-viz > span {
  color: var(--muted);
  font: 600 8px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: nowrap;
}
.metric-signal {
  position: relative;
  display: flex;
  align-items: end;
  gap: 3px;
  width: 54px;
  height: 24px;
}
.metric-signal i {
  width: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tone, var(--pink)) 48%, var(--line));
  box-shadow: 0 0 9px color-mix(in srgb, var(--tone, var(--pink)) 20%, transparent);
}
.metric-signal i:nth-child(1) { height: 38%; }
.metric-signal i:nth-child(2) { height: 72%; }
.metric-signal i:nth-child(3) { height: 52%; }
.metric-signal em {
  position: absolute;
  right: 0;
  bottom: 1px;
  width: 30px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--tone, var(--pink)) var(--progress, 42%), var(--line) 0);
}

.chart-draw-bar {
  transform-box: fill-box;
  transform-origin: center bottom;
  animation: overviewBarRise .65s var(--spring) both;
  animation-delay: var(--delay, 0ms);
}
#trendChart svg { filter: drop-shadow(0 10px 20px color-mix(in srgb, var(--pink) 5%, transparent)); }
.chart-path { filter: drop-shadow(0 0 6px color-mix(in srgb, currentColor 30%, transparent)); }
.chart-point { filter: drop-shadow(0 0 7px currentColor); }

#view-overview .ring::after {
  content: "";
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--violet) 22%, transparent);
  border-top-color: color-mix(in srgb, var(--pink) 72%, transparent);
  animation: overviewRingOrbit 7s linear infinite;
  pointer-events: none;
}

@keyframes overviewDataBeam { 0%,100% { transform: scaleX(.28); opacity: .38; } 50% { transform: scaleX(1); opacity: 1; } }
@keyframes overviewBeacon { 50% { opacity: .48; transform: scale(.72); } }
@keyframes overviewSpectral { to { transform: rotate(360deg); } }
@keyframes overviewBarRise { from { transform: scaleY(.05); opacity: .15; } to { transform: scaleY(1); opacity: 1; } }
@keyframes overviewRingOrbit { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  #view-overview .hero-copy::after,
  .overview-scope::before,
  #view-overview .metric::before,
  .chart-draw-bar,
  #view-overview .ring::after {
    animation: none !important;
  }
  #view-overview .metric,
  #view-overview .metric:hover,
  #view-overview .panel,
  #view-overview .hero {
    transform: none !important;
    transition-duration: .01ms !important;
  }
}
'''
if "/* v3.2.0 immersive overview" not in page:
    page = replace_once(page, "</style>", core_css + "\n</style>", "append overview CSS")

# Inline bootstrap must remain byte-for-byte equivalent to its source.
page = re.sub(
    r'<script data-rollpig-bootstrap="3\.1\.2">.*?</script>',
    f'<script data-rollpig-bootstrap="{VERSION}">{bootstrap}</script>',
    page,
    count=1,
    flags=re.S,
)
PAGE.write_text(page, encoding="utf-8")

# Version contracts.
test_asset = TEST_ASSET.read_text(encoding="utf-8")
test_asset = test_asset.replace(
    "data-rollpig-bootstrap=\"3.1.2\"",
    f"data-rollpig-bootstrap=\"{VERSION}\"",
)
TEST_ASSET.write_text(test_asset, encoding="utf-8")

test_cache = TEST_CACHE.read_text(encoding="utf-8")
test_cache = replace_once(
    test_cache,
    'VERSION = "3.1.2"',
    f'VERSION = "{VERSION}"',
    "cache version contract",
)
TEST_CACHE.write_text(test_cache, encoding="utf-8")
