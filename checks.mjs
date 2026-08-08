import { chromium } from 'playwright';
import { execFileSync } from 'child_process';
import fs from 'fs'; import crypto from 'crypto';
const CACHE='/tmp/urlcache';
function curlFetch(url){const h=crypto.createHash('md5').update(url).digest('hex');const bodyF=`${CACHE}/${h}.bin`,headF=`${CACHE}/${h}.hdr`;
if(!fs.existsSync(bodyF)){try{execFileSync('curl',['-sL','--compressed','--max-time','20','-D',headF,'-o',bodyF,url],{timeout:25000});}catch{return null;}}
if(!fs.existsSync(bodyF))return null;let ct='application/octet-stream';try{const m=fs.readFileSync(headF,'utf8').match(/content-type:\s*([^\r\n]+)/i);if(m)ct=m[1].trim();}catch{}
return{body:fs.readFileSync(bodyF),contentType:ct};}
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const path of ['/','/search','/makelaars']) {
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 } });
  await ctx.route('**/*', async r=>{const u=r.request().url();if(u.startsWith('http://localhost')||u.startsWith('data:'))return r.continue();const res=curlFetch(u);return res?r.fulfill({status:200,contentType:res.contentType,body:res.body,headers:{'access-control-allow-origin':'*'}}):r.abort();});
  const p = await ctx.newPage();
  await p.goto('http://localhost:4321'+path,{waitUntil:'load',timeout:45000}).catch(()=>{});
  await p.waitForTimeout(4000);
  const r = await p.evaluate(() => {
    const doc = document.documentElement;
    const overflowX = doc.scrollWidth > doc.clientWidth ? (doc.scrollWidth - doc.clientWidth) : 0;
    // vind elementen die buiten beeld steken
    let culprits = [];
    if (overflowX > 0) {
      for (const el of document.querySelectorAll('*')) {
        const rect = el.getBoundingClientRect();
        if (rect.right > doc.clientWidth + 4 && rect.width < doc.scrollWidth) {
          culprits.push(el.tagName + '.' + String(el.className).slice(0,50));
          if (culprits.length >= 5) break;
        }
      }
    }
    // touch targets < 40px
    let smallTargets = 0;
    for (const el of document.querySelectorAll('a,button')) {
      const r2 = el.getBoundingClientRect();
      if (r2.width > 0 && r2.height > 0 && (r2.height < 40 || r2.width < 40) && r2.height < 44) smallTargets++;
    }
    return { overflowX, culprits, smallTargets, title: document.title };
  });
  console.log(path, JSON.stringify(r));
  await ctx.close();
}
await b.close();
