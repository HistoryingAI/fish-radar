// 测速：从你自己这台电脑（大陆线路，不挂代理）测网站能不能开、要多久
// 双击 测速.bat 就会跑到这个。参数可以给网址，不给就自动找。
const https = require('https');
const fs = require('fs');
const path = require('path');

const HERE = __dirname;

// 从 index.html 的 canonical 抓出「现在的正式网址」
function canonical() {
  try {
    const html = fs.readFileSync(path.join(HERE, 'index.html'), 'utf8');
    const m = html.match(/rel="canonical"\s+href="([^"]+)"/);
    return m ? m[1] : null;
  } catch (e) {
    return null;
  }
}

// 中文一個字佔兩格，padEnd 只算一個，所以要自己補
function pad(s, width) {
  let w = 0;
  for (const ch of String(s)) w += (ch.charCodeAt(0) > 0x2e7f) ? 2 : 1;
  return String(s) + ' '.repeat(Math.max(1, width - w));
}

function probe(url) {
  return new Promise((resolve) => {
    let u;
    try { u = new URL(url); } catch (e) { return resolve({ url, err: '网址写得不对' }); }
    const t0 = Date.now();
    const req = https.request({
      host: u.hostname, path: u.pathname + u.search, method: 'GET', timeout: 15000,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36' }
    }, (res) => {
      const ttfb = Date.now() - t0;
      let n = 0;
      res.on('data', (c) => { n += c.length; if (n > 400000) res.destroy(); });
      res.on('end', () => resolve({ url, status: res.statusCode, ttfb, size: n,
        server: (res.headers.server || '-'), cf: (res.headers['cf-ray'] || '-').split('-').pop() }));
      res.on('error', () => resolve({ url, status: res.statusCode, ttfb, size: n,
        server: (res.headers.server || '-'), cf: (res.headers['cf-ray'] || '-').split('-').pop() }));
    });
    req.on('timeout', () => { req.destroy(new Error('15 秒没回应')); });
    req.on('error', (e) => resolve({ url, err: (e.code || e.message) + ' (' + (Date.now() - t0) + 'ms)' }));
    req.end();
  });
}

(async () => {
  const c = canonical();
  const list = [];
  list.push(['百度（对照，一定通）', 'https://www.baidu.com/']);
  if (c && c.startsWith('http')) list.push(['你的正式网址', c]);
  else list.push(['你的正式网址', '（index.html 里的 canonical 还是相对路径，跑一次 换网址.bat）']);
  list.push(['旧地址（Vercel）', 'https://fish-radar-two.vercel.app/']);

  const extra = process.argv.slice(2);
  extra.forEach((u) => list.push(['你指定的', u]));

  console.log('');
  console.log('  直接从这台电脑连出去，不走代理。手机上请关 Wi-Fi 用 4G 再试一次。');
  console.log('');

  for (const [label, url] of list) {
    if (!url.startsWith('http')) {
      console.log('  ' + pad(label, 22) + '  ' + url);
      continue;
    }
    const r = await probe(url);
    let verdict;
    if (r.err) {
      verdict = '❌ 打不开：' + r.err;
    } else if (r.status >= 300 && r.status < 400) {
      verdict = '↪ 跳转 ' + r.status + '，' + r.ttfb + 'ms';
    } else if (r.status === 200) {
      const sec = (r.ttfb / 1000).toFixed(2);
      const mark = r.ttfb < 800 ? '✅' : (r.ttfb < 2500 ? '⚠️' : '🐢');
      verdict = mark + ' ' + r.status + '，' + sec + ' 秒' +
        (r.server !== '-' ? '，' + r.server : '') +
        (r.cf !== '-' && r.cf !== 'cf-ray' ? '（' + r.cf + '）' : '');
    } else {
      verdict = '⚠️ HTTP ' + r.status + '，' + r.ttfb + 'ms';
    }
    console.log('  ' + pad(label, 22) + '  ' + verdict);
  }

  console.log('');
  console.log('  ✅ 小于 0.8 秒 = 很好   ⚠️ 0.8~2.5 秒 = 能开但慢   🐢 超过 2.5 秒 = 用户会等   ❌ = 打不开');
  console.log('');
})();
