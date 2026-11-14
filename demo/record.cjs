// Records the demo video: drives the live site against NEAR mainnet, with on-screen captions.
// Used by .github/workflows/demo-video.yml; also runs locally:
//   python3 -m http.server 8000 --directory site &
//   node demo/record.cjs http://127.0.0.1:8000/
// Output: demo-video/raw.webm plus PNG screenshots of each step.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL_ = process.argv[2] || 'http://127.0.0.1:8000/';
const OUT = path.resolve('demo-video');
fs.mkdirSync(OUT, { recursive: true });

function pickAccount() {
  // A real account from this run's mainnet snapshot: prefer one that enrolled a PQ key, then any
  // mixed or PQ-only account in the sample, else a well-known account.
  try {
    const r = JSON.parse(fs.readFileSync('site/data/latest/report.json', 'utf8'));
    const pools = [((r.cohorts || {}).pq_enrollers || {}).accounts || [], r.accounts || []];
    for (const pool of pools) {
      for (const want of ['INCOMPLETE_WEAKEST_LINK', 'COMPLETE']) {
        const hit = pool.find((a) => a.state === want);
        if (hit) return hit.account_id;
      }
    }
  } catch (e) { /* no snapshot */ }
  return 'near';
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: OUT, size: { width: 1280, height: 720 } } });
  const page = await context.newPage();
  const caption = async (text) => {
    await page.evaluate((t) => {
      let el = document.getElementById('demo-caption');
      if (!el) {
        el = document.createElement('div');
        el.id = 'demo-caption';
        el.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99;max-width:1000px;' +
          'background:rgba(4,10,22,.94);color:#e7edf9;border:1px solid #7de1cf;border-radius:12px;padding:14px 22px;' +
          'font:600 22px/1.35 Inter,system-ui,sans-serif;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,.5)';
        document.body.appendChild(el);
      }
      el.textContent = t;
    }, text);
  };
  const shot = (name) => page.screenshot({ path: path.join(OUT, name + '.png') });
  const pause = (ms) => page.waitForTimeout(ms);
  const scrollTo = async (sel, offset = -80) => {
    await page.evaluate(([s, o]) => { const el = document.querySelector(s); window.scrollTo({ top: el.getBoundingClientRect().top + scrollY + o, behavior: 'smooth' }); }, [sel, offset]);
    await pause(900);
  };

  await page.goto(URL_);
  await pause(800);
  await caption('NEAR now supports post-quantum ML-DSA-65 keys. But adding one does not remove the classical key.');
  await pause(4500);
  await shot('01-hero');

  const account = pickAccount();
  await scrollTo('#check');
  await caption('Check any account: its access keys, read live from NEAR mainnet at one pinned block.');
  await pause(1500);
  await page.fill('#acct', '');
  await page.type('#acct', account, { delay: 70 });
  await page.click('#check-btn');
  await page.waitForSelector('#check-out .result', { timeout: 60000 });
  if (await page.locator('#check-out .error').count()) throw new Error('Account check showed an RPC error');
  await pause(800);
  await scrollTo('#check-out', -140);
  const state = await page.$eval('#check-out', (el) => (el.querySelector('.result') || {}).dataset ? el.querySelector('.result').dataset.state : 'error');
  const say = {
    INCOMPLETE_WEAKEST_LINK: account + ' has a post-quantum key, and its classical full-access key is still live.',
    COMPLETE: account + ' has PQ-only full access at this observed block; no classical full-access key was observed.',
    CLASSICAL_ONLY: account + ' has no post-quantum key yet: classical full access only.',
  }[state] || 'Result for ' + account + ', with the block it was read at.';
  await caption(say);
  await pause(5000);
  await shot('02-check');

  await scrollTo('#sample');
  await caption('Live sample: every account that signed a transaction in the last 10 blocks, drawn by a seed equal to the block hash.');
  await page.fill('#win', '10');
  await page.fill('#size', '50');
  await pause(1500);
  await page.click('#sample-btn');
  await pause(2500);
  await shot('03-sample-running');
  await page.waitForSelector('#sample-out .result', { timeout: 180000 });
  if (await page.locator('#sample-progress .error, #sample-out .error').count()) throw new Error('Live sample showed an RPC error');
  const report = await page.locator('#sample-out').innerText();
  if (!/block|sample|account/i.test(report)) throw new Error('Sample result missing meaningful metadata');
  await pause(600);
  await scrollTo('#sample-out', -120);
  await caption('A naive count reports accounts "with a PQ key". Residual also counts which still hold classical full access.');
  await pause(5500);
  await shot('04-sample-result');
  await page.evaluate(() => window.scrollBy({ top: 520, behavior: 'smooth' }));
  await caption('Every sampled account, plus any that enrolled an ML-DSA-65 key in the window. Unknowns stay in the totals.');
  await pause(4500);
  await shot('05-sample-accounts');

  await scrollTo('#snapshot');
  const hasSnap = await page.$('#snap-out .result');
  await caption(hasSnap ? 'Daily snapshot: a 200-account mainnet sample run by GitHub Actions, published with raw data and digests.'
    : 'Daily snapshot: a 200-account mainnet sample, published here by the repository\'s GitHub Actions workflow.');
  await pause(5000);
  await shot('06-snapshot');

  await scrollTo('#how');
  await caption('Read-only, open source, reproducible. github.com/agentzeta/residual-near  #NEARHackathon');
  await pause(4500);
  await shot('07-close');

  const video = page.video();
  await context.close();
  await browser.close();
  fs.renameSync(await video.path(), path.join(OUT, 'raw.webm'));
  console.log('wrote', path.join(OUT, 'raw.webm'));
})().catch((e) => { console.error(e); process.exit(1); });
