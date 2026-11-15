import {after, before, test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright-core';

const site = path.resolve(process.env.WIKI_SITE_DIR || 'site');
let server, browser, origin;

before(async () => {
  await readFile(path.join(site, 'index.html'));
  server = createServer(async (req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(site, `.${pathname}${pathname.endsWith('/') ? 'index.html' : ''}`);
    if (!file.startsWith(`${site}${path.sep}`)) { res.writeHead(403).end(); return; }
    try {
      const content = await readFile(file);
      const mime = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml'};
      res.writeHead(200, {'Content-Type': mime[path.extname(file)] || 'application/octet-stream'}).end(content);
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
});
after(async () => {
  await browser?.close();
  if (server) await new Promise(resolve => server.close(resolve));
});

for (const width of [320, 390, 768, 1024, 1440]) {
  test(`dashboard fits ${width}px and its task links work`, async () => {
    const page = await browser.newPage({viewport: {width, height: 1000}, reducedMotion: 'reduce'});
    page.setDefaultTimeout(5000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await page.locator('.pig-copy[data-ready="1"]').first().waitFor();
    const tasks = page.locator('.pig-task');
    assert.equal(await tasks.count(), 6);
    const tops = await tasks.evaluateAll(nodes => nodes.map(node => Math.round(node.getBoundingClientRect().top)));
    if (width >= 1024) assert.equal(tops[0], tops[2], 'three task columns on desktop');
    else if (width >= 768) assert.equal(tops[0], tops[1], 'two task columns on tablet');
    else assert.ok(tops[1] > tops[0], 'one task column on phones');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    for (const button of await page.locator('.pig-copy').all()) {
      const rect = await button.boundingBox();
      assert.ok(rect.width >= 44 && rect.height >= 44);
    }
    for (const href of await page.locator('.pig-task').evaluateAll(nodes => nodes.map(node => node.href))) {
      assert.equal((await page.request.get(href)).status(), 200, href);
    }
    if (process.env.WIKI_SCREENSHOTS && [390, 1440].includes(width)) {
      await mkdir(process.env.WIKI_SCREENSHOTS, {recursive: true});
      await page.screenshot({path: path.join(process.env.WIKI_SCREENSHOTS, `wiki-${width}.png`), fullPage: true});
    }
    assert.deepEqual(errors, []);
    await page.close();
  });
}

test('keyboard copy uses the clipboard and explains a denied request', async () => {
  const context = await browser.newContext({permissions: ['clipboard-read', 'clipboard-write']});
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  await page.goto(origin);
  const button = page.getByRole('button', {name: '複製 /今日小豬', exact: true});
  await button.focus();
  await page.keyboard.press('Enter');
  await page.getByRole('status').filter({hasText: '已複製 /今日小豬'}).waitFor();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), '/今日小豬');
  await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new Error('denied'); }; });
  await page.getByRole('button', {name: '複製 /我的豬圈', exact: true}).click();
  await page.getByRole('status').filter({hasText: '請選取並複製這條指令：/我的豬圈'}).waitFor();
  await context.close();
});

test('mobile drawer remains usable and returning home restores copy actions', async () => {
  const page = await browser.newPage({viewport: {width: 390, height: 844}});
  page.setDefaultTimeout(5000);
  await page.goto(origin);
  await page.locator('.md-header__button[for="__drawer"]').click();
  await page.locator('.md-nav--primary label.md-nav__link').filter({hasText: '玩家指南'}).first().click();
  await page.locator('.md-nav--primary').getByRole('link', {name: '30 秒開始', exact: true}).click();
  await page.waitForURL('**/getting-started/');
  await page.getByRole('heading', {name: '⚡ 30 秒開始養豬', exact: true}).waitFor();
  await page.locator('.md-header__button[for="__drawer"]').click();
  await page.locator('.md-nav--primary .md-nav__title[for="__nav_2"]').click();
  await page.locator('.md-nav--primary').getByRole('link', {name: '首頁', exact: true}).click();
  await page.locator('.pig-copy[data-ready="1"]').first().waitFor();
  await page.close();
});

test('search finds the Discord troubleshooting page', async () => {
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  await page.goto(origin);
  await page.locator('.md-search__input').fill('Discord');
  await page.locator('.md-search-result__list a').filter({hasText: 'Discord 輸入'}).first().waitFor();
  await page.close();
});

test('article components fit phones and the interactive examples still respond', async () => {
  const page = await browser.newPage({viewport: {width: 320, height: 900}});
  page.setDefaultTimeout(5000);
  for (const route of ['getting-started/', 'gameplay/', 'gameplay/collection-pity/', 'gameplay/ex-growth/', 'gameplay/roast-outcomes/', 'gameplay/roast-charge/', 'gameplay/daily-report/', 'creators/', 'troubleshooting/']) {
    await page.goto(`${origin}/${route}`);
    await page.waitForFunction(() => [...document.querySelectorAll('.md-typeset table')].every(table => table.closest('.md-typeset__scrollwrap')));
    const overflow = await page.evaluate(() => ({
      width: innerWidth, scroll: document.documentElement.scrollWidth,

    }));
    assert.ok(overflow.scroll <= overflow.width, `${route}: ${JSON.stringify(overflow)}`);
  }
  await page.goto(`${origin}/gameplay/collection-pity/`);
  await page.locator('[data-pity-lab][data-ready="1"]').waitFor();
  for (const input of await page.locator('[data-pity-lab] input').all()) {
    await input.evaluate(node => { node.value = '8'; node.dispatchEvent(new Event('input', {bubbles: true})); });
  }
  assert.equal(await page.locator('[data-pity-total]').textContent(), '80%');
  await page.goto(`${origin}/gameplay/roast-outcomes/`);
  await page.locator('[data-roast-fire]').click();
  assert.equal(await page.locator('[data-roast-history] > span').count(), 1);
  await page.close();
});
