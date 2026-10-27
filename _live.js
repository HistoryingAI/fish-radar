const https = require('https');
const dns = require('dns');

const p = (fn, name) => new Promise((r) => {
  let done = false;
  const t = setTimeout(() => { if (!done) { done = true; r('TIMEOUT'); } }, 8000);
  fn(name, (e, v) => { if (done) return; done = true; clearTimeout(t); r(e ? 'ERR ' + e.code : v); });
});

function get(host, path) {
  return new Promise((r) => {
    const t0 = Date.now();
    const q = https.request({ host, path, timeout: 20000,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0' } }, (res) => {
      let n = 0, b = '';
      res.on('data', (c) => { n += c.length; if (b.length < 300000) b += c.toString('utf8'); if (n > 6e6) res.destroy(); });
      res.on('end', () => r({ code: res.statusCode, ms: Date.now() - t0, size: n, b,
        cf: (res.headers['cf-ray'] || '-').split('-').pop(),
        cache: res.headers['cache-control'] || '-',
        loc: res.headers.location || '-' }));
    });
    q.on('timeout', () => { q.destroy(); r({ err: 'timeout' }); });
    q.on('error', (e) => r({ err: e.code || e.message }));
    q.end();
  });
}

(async () => {
  console.log('=== 1. 域名解析 ===');
  console.log('  A     : ' + (await p(dns.resolve4, 'fishradar.vip')));
  console.log('  www A : ' + (await p(dns.resolve4, 'www.fishradar.vip')));

  console.log('\n=== 2. 打开看看 ===');
  for (const [h, path] of [['fishradar.vip', '/'], ['www.fishradar.vip', '/'], ['fishradar.vip', '/data/posts_top.js']]) {
    const r = await get(h, path);
    if (r.err) { console.log('  ' + (h + path).padEnd(34) + '❌ ' + r.err); continue; }
    const title = (r.b.match(/<title[^>]*>([^<]*)</i) || [, ''])[1].trim().slice(0, 40);
    console.log('  ' + (h + path).padEnd(34) + r.code + '  ' + (r.ms / 1000).toFixed(2) + 's  ' +
      (r.size / 1024).toFixed(1) + 'KB  ' + r.cf + '  ' + title);
  }

  console.log('\n=== 3. 分享卡地址（og:image / canonical）===');
  const home = await get('fishradar.vip', '/?z=' + Date.now());
  const og = (home.b.match(/property="og:image"\s+content="([^"]+)"/) || [, '?'])[1];
  const can = (home.b.match(/rel="canonical" href="([^"]+)"/) || [, '?'])[1];
  console.log('  og:image  : ' + og);
  console.log('  canonical : ' + can);
  console.log('  ' + (og.includes('fishradar.vip') ? '✅ 已经是新域名' : '⚠️ 还是旧地址，要双击 换网址.bat'));

  console.log('\n=== 4. 源码还挡着吗（带随机参数）===');
  for (const path of ['/collect.py', '/config.json', '/data/posts.json']) {
    const r = await get('fishradar.vip', path + '?z=' + Date.now());
    const isHome = !r.err && r.code === 200 && /肥魚雷達|肥鱼雷达/.test(r.b);
    console.log('  ' + path.padEnd(22) + (isHome ? '✅ 回首頁' : r.err ? '❌ ' + r.err : '⚠️ ' + r.code));
  }
})();
