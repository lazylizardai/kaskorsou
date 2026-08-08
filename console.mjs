import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', proxy: { server: 'http://127.0.0.1:37637', bypass: 'localhost,127.0.0.1' }, args: ['--ignore-certificate-errors'] });
const p = await (await b.newContext()).newPage();
p.on('console', m => { if (m.type()==='error'||m.type()==='warning') console.log(m.type(), m.text().slice(0,200)); });
p.on('requestfailed', r => console.log('FAILED', r.url().slice(0,120), r.failure()?.errorText));
await p.goto('http://localhost:4321/', { waitUntil: 'networkidle' }).catch(()=>{});
await p.waitForTimeout(5000);
await b.close();
