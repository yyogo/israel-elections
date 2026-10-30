const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const options={headless:true};
 if(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) options.executablePath=process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
 const browser=await chromium.launch(options);
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Prove that the charts have no network dependency. Remote logo fallbacks are expected.
  await page.route('https://**/*',r=>r.abort());
  await page.goto(pathToFileURL(path.resolve(__dirname,'../dist/index.html')).href,{waitUntil:'domcontentloaded'});
  assert.equal(await page.locator('#mini-chart svg').count(),1);
  await page.locator('[data-party="0"]').hover();
  assert.equal(await page.locator('.segment:not(.dim)').count(),12);
  assert.ok((await page.locator('#national-reference').textContent()).includes('20.52%'));
  assert.equal(await page.locator('#tooltip').count(),0);
  assert.equal(await page.evaluate(()=>miniChart.getOption().tooltip[0].show),false);
  await page.locator('[data-bloc="0"]').click();await page.locator('h1').hover();
  assert.equal(await page.locator('.segment:not(.dim)').count(),60);
  await page.locator('[data-axis-group="11"]').click();assert.equal(await page.evaluate(()=>lastPieGroup),'10');
  assert.equal(await page.evaluate(()=>miniChart.getOption().series[0].data.reduce((a,d)=>a+d.value,0)),4551);
  await page.locator('#expand-pie').click();await page.waitForTimeout(150);
  assert.equal(await page.locator('#large-chart svg').count(),1);
  await page.locator('#expand-pie').click();await page.locator('#reset').click();
  for(const width of [390,320,768]) {
   await page.setViewportSize({width,height:844});await page.waitForTimeout(150);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
   if(width<620) {
    const gaps=await page.evaluate(()=>coords.slice(1).map((c,i)=>({id:c.g.id,gap:c.y-coords[i].y-coords[i].h})));
    for(const {id,gap} of gaps)assert.ok(Math.abs(gap-(['1','10'].includes(id)?12:0))<.001);
    const labels=await page.locator('#chart .bar-label').evaluateAll(a=>a.map(e=>e.getBoundingClientRect().toJSON()));
    for(let i=1;i<labels.length;i++)assert.ok(labels[i].top>=labels[i-1].bottom);
   }
  }
  assert.deepEqual(errors,[]);console.log('Browser smoke test passed.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
