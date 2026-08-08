import { chromium } from 'playwright';
import { execFileSync } from 'child_process';
import fs from 'fs';
import crypto from 'crypto';

const CACHE = '/tmp/urlcache';
fs.mkdirSync(CACHE, { recursive: true });

function curlFetch(url) {
  const h = crypto.createHash('md5').update(url).digest('hex');
  const bodyF = `${CACHE}/${h}.bin`, headF = `${CACHE}/${h}.hdr`;
  if (!fs.existsSync(bodyF)) {
    try {
      execFileSync('curl', ['-sL', '--compressed', '--max-time', '20', '-D', headF, '-o', bodyF, url], { timeout: 25000 });
    } catch { return null; }
  }
  if (!fs.existsSync(bodyF)) return null;
  let ct = 'application/octet-stream';
  try {
    const hdr = fs.readFileSync(headF, 'utf8');
    const m = hdr.match(/content-type:\s*([^\r\n]+)/i);
    if (m) ct = m[1].trim();
  } catch {}
  return { body: fs.readFileSync(bodyF), contentType: ct };
}

export async function launchPatched() {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  return b;
}

export async function patchContext(ctx) {
  await ctx.route('**/*', async route => {
    const url = route.request().url();
    if (url.startsWith('http://localhost') || url.startsWith('data:')) return route.continue();
    const res = curlFetch(url);
    if (res) return route.fulfill({ status: 200, contentType: res.contentType, body: res.body, headers: { 'access-control-allow-origin': '*' } });
    return route.abort();
  });
}

const b = await launchPatched();
const pages = [['staging','/']];
for (const [w] of [[1440]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: w<500?812:900 } });
  await patchContext(ctx);
  await ctx.addInitScript(() => {
    // forceer whileInView: elke geobserveerde node is meteen zichtbaar
    window.IntersectionObserver = class {
      constructor(cb) { this.cb = cb; }
      observe(el) { this.cb([{ isIntersecting: true, target: el, intersectionRatio: 1 }], this); }
      unobserve() {} disconnect() {} takeRecords() { return []; }
    };
  });
  const p = await ctx.newPage();
  for (const [name, path] of pages) {
    await p.goto('https://staging.kaskorsou.pages.dev'+path, { waitUntil: 'load', timeout: 45000 }).catch(()=>{});
    await p.waitForTimeout(4000);
    // scroll door de hele pagina zodat whileInView-animaties triggeren
    await p.evaluate(async () => {
      const h = document.body.scrollHeight;
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
      window.scrollTo(0, 0);
    }).catch(()=>{});
    await p.waitForTimeout(2500);
    await p.screenshot({ path: `/tmp/audit_${name}_${w}.png`, fullPage: name!=='search' }).catch(async e => {
      console.log('fullpage fail', name, w, e.message.slice(0,80));
      await p.screenshot({ path: `/tmp/audit_${name}_${w}.png` }).catch(()=>{});
    });
  }
  await ctx.close();
}
await b.close();
console.log('done');
