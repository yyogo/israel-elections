// Optional browser smoke test for dist/index.html. See tests/README.md.
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('playwright-core'); }
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const url = pathToFileURL(path.resolve(__dirname, '../dist/index.html')).href;

(async () => {
  const options = { headless: true };
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) options.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const browser = await playwright.chromium.launch(options);
  const errors = [];
  const open = async (query, viewport = { width: 1440, height: 1000 }) => {
    const page = await browser.newPage({ viewport });
    page.on('pageerror', e => errors.push(e.message));
    // Charts must not depend on the network; remote logos are allowed to fail.
    await page.route('https://**/*', r => r.abort());
    await page.goto(url + query, { waitUntil: 'load' });
    await page.waitForTimeout(200);
    return page;
  };
  try {
    // Clusters, Hebrew, desktop.
    let page = await open('');
    assert.equal(await page.getAttribute('html', 'dir'), 'rtl');
    assert.equal(await page.locator('#group-donut svg').count(), 1);
    const segments = await page.locator('#cluster-chart .segment').count();
    assert.ok(segments > 150, `segments: ${segments}`);
    await page.locator('#cluster-legend [data-party="0"]').hover();
    assert.ok((await page.locator('#national-reference').textContent()).includes('20.52%'));
    assert.ok((await page.locator('#selection-banner').textContent()).includes('הליכוד'));
    await page.locator('#cluster-legend [data-bloc="0"]').click();
    await page.locator('h1').hover();
    assert.ok((await page.locator('#selection-banner').textContent()).includes('גוש נתניהו'));
    await page.locator('#cluster-year [data-value="2022"]').click();
    assert.ok((await page.locator('#clusters-lead').textContent()).includes('4,764,742'));
    await page.selectOption('#group-select', 'national');
    assert.ok((await page.locator('#group-summary').textContent()).includes('4,764,742'));
    await page.close();

    // Trends, English.
    page = await open('?lang=en#trends');
    assert.equal(await page.getAttribute('html', 'dir'), 'ltr');
    assert.ok(await page.locator('#sankey .flow').count() > 5);
    await page.locator('#flow-level [data-value="list"]').click();
    assert.ok(await page.locator('#sankey .flow').count() > 20);
    assert.equal(await page.locator('#sankey-caveat').isVisible(), true);
    assert.equal(await page.locator('#scatter canvas').count() > 0, true);
    await page.close();

    // Localities, phone width.
    page = await open('#settlements', { width: 390, height: 900 });
    await page.fill('#settlement-search', 'חיפה');
    await page.locator('#settlement-results button').first().click();
    assert.ok((await page.locator('#settlement-detail h3').textContent()).includes('חיפה'));
    await page.close();

    assert.deepEqual(errors, []);
    console.log('Browser smoke test passed.');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
