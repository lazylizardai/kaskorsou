import { chromium } from 'playwright';
import { execFileSync } from 'child_process';
import fs from 'fs';
import crypto from 'crypto';

const CACHE = '/tmp/urlcache';
fs.mkdirSync(CACHE, { recursive: true });

function curlFetch(url, headers = {}) {
  const keyExtra = ['apikey', 'authorization'].map(h => headers[h] || '').join('|');
  const h = crypto.createHash('md5').update(url + '::' + keyExtra).digest('hex');
  const bodyF = `${CACHE}/${h}.bin`, headF = `${CACHE}/${h}.hdr`;
  if (!fs.existsSync(bodyF)) {
    const args = ['-sL', '--compressed', '--max-time', '20', '-D', headF, '-o', bodyF];
    for (const [k, v] of Object.entries(headers)) {
      if (['apikey', 'authorization', 'accept', 'accept-profile', 'content-profile'].includes(k)) args.push('-H', `${k}: ${v}`);
    }
    args.push(url);
    try { execFileSync('curl', args, { timeout: 25000 }); } catch { return null; }
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
  return chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
}

export async function patchContext(ctx) {
  await ctx.route('**/*', async route => {
    const url = route.request().url();
    if (url.startsWith('http://localhost') || url.startsWith('data:')) return route.continue();
    const res = curlFetch(url, route.request().headers());
    if (res) return route.fulfill({ status: 200, contentType: res.contentType, body: res.body, headers: { 'access-control-allow-origin': '*' } });
    return route.abort();
  });
}

const WAIT = Number(process.argv[2] || 16000);
const b = await launchPatched();
for (const [w, h] of [[1440, 900], [375, 812]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  await patchContext(ctx);
  const p = await ctx.newPage();
  await p.addInitScript(() => { window.__KK_TILE_MAIN = true; });
  p.on('console', m => { if (m.type() === 'error') console.log(`[${w}] console error:`, m.text().slice(0, 160)); });
  p.on('pageerror', e => console.log(`[${w}] pageerror:`, String(e).slice(0, 200)));
  await p.goto('http://localhost:4321/kaart', { waitUntil: 'load', timeout: 45000 }).catch(e => console.log('goto fail', e.message));
  await p.waitForTimeout(WAIT);
  await p.screenshot({ path: `/tmp/kaart_${w}.png` });
  console.log(`saved /tmp/kaart_${w}.png`);
  // Popup-check: klik op een gouden pin als die er is
  const pin = p.locator('.kk3d-pin').first();
  if (await pin.count() > 0) {
    await pin.click({ force: true }).catch(() => {});
    await p.waitForTimeout(4000);
    await p.screenshot({ path: `/tmp/kaart_${w}_popup.png` });
    console.log(`saved /tmp/kaart_${w}_popup.png`);
  } else {
    console.log(`[${w}] no 3D-tour pins found`);
  }
  await ctx.close();
}
await b.close();
console.log('done');
