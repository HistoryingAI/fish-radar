// 肥鱼雷达 · 渲染测试
// =====================
// 不联网、不开浏览器：用一个极简的假 DOM 把 index.html 里的脚本跑一遍。
// 检查四件事：首屏 20 条、▶ 加载更多、简繁切换、深浅色切换。
//
// 跑法：node test_render.js

const fs = require("fs");
const path = require("path");

const here = __dirname;
const html = fs.readFileSync(path.join(here, "index.html"), "utf8");
const inline = [...html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).pop();

const fails = [];
const ok = m => console.log("  [OK]   " + m);
const bad = m => { console.log("  [FAIL] " + m); fails.push(m); };
const count = (s, n) => String(s).split(n).length - 1;

// 页面默认「近 7 天」，所以画出来的条数是 7 天内的条数，不是全部。
// 不写死数字：帖子会随时间滑出窗口，每天算出来的都不一样。
function expectedVisible(posts) {
  const cutoff = Date.now() / 1000 - 7 * 86400;
  return posts.filter(p => !p.published_ts || p.published_ts >= cutoff).length;
}

function makeEl(id) {
  const e = {
    id, innerHTML: "", textContent: "", title: "", style: {}, dataset: {},
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    querySelectorAll() { return []; }, closest() { return null; },
    insertBefore() {}, appendChild() {}, removeChild() {}, click() {},
    focus() {}, blur() {}, value: "", className: "",
    onclick: null, onload: null, onerror: null, nodeType: 1, childNodes: [],
    _h: {},
    addEventListener(type, fn) { (e._h[type] = e._h[type] || []).push(fn); },
    fire(type, ev) { (e._h[type] || []).forEach(fn => fn.call(e, ev)); },
    setAttribute(k, v) { e["_attr_" + k] = v; },
    getAttribute(k) { return e["_attr_" + k]; },
  };
  return e;
}

const ids = ["notice", "chars", "plats", "when", "rel", "csv", "loadhint",
             "stats", "flow", "mask", "modal", "stamp", "window", "took",
             "closeX", "closeB", "langBtn", "themeBtn", "promo",
             "q", "qbox", "qclear", "sort", "stale"];
const store = {};
ids.forEach(i => { store[i] = makeEl(i); });

const body = makeEl("body");
const documentElement = makeEl("html");

const document = {
  title: "肥魚雷達 · FISH RADAR — AI 娘二創全網熱帖聚合",
  body,
  documentElement,
  getElementById: id => store[id] || (store[id] = makeEl(id)),
  querySelector: sel => (sel === ".wrap" ? makeEl("wrap") : makeEl("q")),
  addEventListener() {},
  createElement(tag) {
    const el = makeEl(tag);
    if (tag === "script") {
      let _src = "";
      Object.defineProperty(el, "src", {
        get: () => _src,
        set(v) {
          _src = v;
          setTimeout(() => {
            try {
              new Function(fs.readFileSync(path.join(here, v), "utf8"))();
              el.onload && el.onload();
            } catch (e) { el.onerror && el.onerror(e); }
          }, 0);
        },
      });
    }
    return el;
  },
};

global.document = document;
global.window = global;
global.alert = () => {};
global.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
global.URL = { createObjectURL: () => "blob:x", revokeObjectURL() {} };
global.Blob = function () {};

// ---------- 首屏 ----------
console.log("\n一、首屏（posts_top.js，只有 30 条数据）");
new Function(fs.readFileSync(path.join(here, "data", "i18n.js"), "utf8"))();
new Function(fs.readFileSync(path.join(here, "promos.js"), "utf8"))();
new Function(fs.readFileSync(path.join(here, "data", "posts_top.js"), "utf8"))();
const total = global.FISH_RADAR_TOP.meta.total;
ok(`数据 ${global.FISH_RADAR_TOP.posts.length} 条，meta 说总共 ${total} 条`);

try { new Function(inline)(); ok("脚本执行没有抛错"); }
catch (e) { bad("脚本抛错：" + e.message); console.log(e.stack.split("\n").slice(0, 5).join("\n")); process.exit(1); }

const cards1 = count(store.flow.innerHTML, 'class="card"');
// 首屏 30 条里，未必都在 7 天窗口内（数据放久了会滑出去），所以要按实际算
const topVisible = expectedVisible(global.FISH_RADAR_TOP.posts);
const expect1 = Math.min(20, topVisible);
if (cards1 === expect1) ok(`首屏只画 ${cards1} 条（不是全塞）`);
else bad(`首屏卡片数 ${cards1}，应该是 ${expect1}`);

if (/載入更多/.test(store.flow.innerHTML)) ok("底部有「▶ 載入更多」");
else bad("没有「▶ 載入更多」按钮");

const m1 = store.flow.innerHTML.match(/已顯示 (\d+) \/ (\d+) 條/);
if (m1 && m1[1] === "20") ok(`进度显示正确：已顯示 ${m1[1]} / ${m1[2]} 條`);
else bad("进度显示不对：" + (m1 ? m1[0] : "没找到"));

// ---------- 平台只剩 B 站（2026-10-27 的決定） ----------
console.log("\n一之二、平台只剩 B 站");
const platHtml = store.plats.innerHTML;
if (/B 站/.test(platHtml) && !/小紅書|推特|小黑盒|GitHub/.test(platHtml)) {
  ok("平台欄只剩 B 站");
} else {
  bad("平台欄還有別的平台：" + platHtml.replace(/\s+/g, " ").slice(0, 120));
}
if (/data-p="bilibili"/.test(platHtml) && !/未接入|dead/.test(platHtml)) {
  ok("沒有灰掉的「未接入」按鈕");
} else {
  bad("还留着未接入的灰按鈕");
}

const statHtml = store.stats.innerHTML;
if (/強相關/.test(statHtml) && !/GitHub/.test(statHtml)) {
  ok("統計卡改成強／弱相關拆分（不再有平台分欄）");
} else {
  bad("統計卡不對：" + statHtml.replace(/\s+/g, " ").slice(0, 160));
}
if (!/分平台榜/.test(html)) ok("分平台榜已移除");
else bad("还留着分平台榜");

// ---------- 点「加载更多」 ----------
// 注意：这一刻全量还没载入，手上只有首屏 30 条，所以点一次就到顶了。
console.log("\n二、▶ 載入更多（此时只有首屏 30 条）");
store.flow.fire("click", { target: { closest: s => (s === "#moreBtn" ? {} : null) } });
const cards2 = count(store.flow.innerHTML, 'class="card"');
const expect2cards = Math.min(40, topVisible);
if (cards2 === expect2cards) ok(`点一次补到 ${cards2} 条（手上的量就这么多）`);
else bad(`点一次后是 ${cards2} 条，应该是 ${expect2cards}`);

if (new RegExp("已顯示全部 " + topVisible + " 條").test(store.flow.innerHTML)) {
  ok(`进度显示「已顯示全部 ${topVisible} 條」，按钮消失`);
} else {
  bad("到底了但提示不对");
}

// ---------- 切简体 ----------
console.log("\n三、简繁切换");
store.langBtn.fire("click");
if (/强相关/.test(store.flow.innerHTML) || /相关/.test(store.flow.innerHTML)) ok("卡片标签已转简体（強相關 → 强相关）");
else bad("切换后卡片标签还是繁体");
if (/开启原帖/.test(store.flow.innerHTML)) ok("按钮文字已转简体（開啟原帖 → 开启原帖）");
else bad("按钮文字没转");
if (store.langBtn.textContent === "简") ok("按钮自己显示「简」");
else bad("切换按钮文字不对：" + store.langBtn.textContent);

// 简体模式下标题应该用原标题（数据本来就是简体）
if (/鲸鱼娘|大肥鱼|智能|人类/.test(store.flow.innerHTML)) ok("简体模式下标题正常");
else bad("简体模式下标题异常");

// ---------- 切回繁体 ----------
store.langBtn.fire("click");
if (/強相關|相關/.test(store.flow.innerHTML)) ok("切回繁体正常（强相关 → 強相關）");
else bad("切回繁体失败");
if (store.langBtn.textContent === "繁") ok("按钮恢复「繁」");
else bad("按钮没恢复：" + store.langBtn.textContent);

// ---------- 深浅色 ----------
console.log("\n四、深浅色切换");
store.themeBtn.fire("click");
if (body.getAttribute("data-theme") === "light") ok("切到浅色（body[data-theme=light]）");
else bad("浅色没生效：" + body.getAttribute("data-theme"));
if (store.themeBtn.textContent === "🌙") ok("按钮变成 🌙");
else bad("主题按钮文字不对：" + store.themeBtn.textContent);
store.themeBtn.fire("click");
if (body.getAttribute("data-theme") === "dark") ok("切回深色");
else bad("切回深色失败");

// ---------- 补载 ----------
setTimeout(() => {
  console.log("\n五、异步补载（posts_rest.js）");
  const cards3 = count(store.flow.innerHTML, 'class="card"');
  if (cards3 === 40) ok("补载后仍保持 40 条（不会突然全铺开）");
  else bad(`补载后变成 ${cards3} 条，应该还是 40`);

  const m3 = store.flow.innerHTML.match(/已顯示 (\d+) \/ (\d+) 條/);
  // 不写死数字：帖子会随时间滑出 7 天窗口，每天跑出来的总数都不一样
  const expTotal = expectedVisible(
    global.FISH_RADAR_TOP.posts.concat(global.FISH_RADAR_REST.posts));
  if (m3 && Number(m3[2]) === expTotal) ok(`总数更新为 ${m3[2]} 条（近 7 天，实时算的）`);
  else bad(`总数不对：${m3 ? m3[2] : "没找到"}，应该是 ${expTotal}`);

  if (/已載入全部/.test(store.loadhint.innerHTML)) ok("加载提示已切到「已载入全部」");
  else bad("加载提示没更新");

  // 全量来了之后再点一次，应该 40 → 60
  console.log("\n六、全量到位后再点「載入更多」");
  const before = count(store.flow.innerHTML, 'class="card"');
  store.flow.fire("click", { target: { closest: s => (s === "#moreBtn" ? {} : null) } });
  const after = count(store.flow.innerHTML, 'class="card"');
  if (after === before + 20) ok(`${before} → ${after}（一次加 20 条）`);
  else bad(`点击后 ${before} → ${after}，应该 +20`);

  // ---------- 推广位 ----------
console.log("\n七、推广位（外链广告位）");
const promoHtml = store.promo.innerHTML;
if (/class="promo"/.test(promoHtml)) ok("推广卡片渲染出来了");
else bad("推广卡片没有渲染");

if (/target="_blank"/.test(promoHtml)) ok('新开分页（target="_blank"）');
else bad("没有 target=_blank，点下去会把本站顶掉");

if (/rel="noopener noreferrer nofollow"/.test(promoHtml)) ok("rel 带 noopener / noreferrer / nofollow");
else bad("rel 不完整");

if (/https:\/\/www\.bilibili\.com\/opus\//.test(promoHtml)) ok("链接指向 B 站活动页");
else bad("链接不对");

if (/外部連結/.test(promoHtml) && /前往 B 站官方活動頁/.test(promoHtml)) ok("有「外部連結」标识和明确按钮文字");
else bad("缺少外链标识");

if (/src="assets\/[^"]+"/.test(promoHtml)) ok("用了本地图（assets/），不是外链别人的图床");
else bad("图片路径不对，应该是 assets/ 下的本地图");

if (!/<iframe/i.test(html)) ok("全程没有 iframe");
else bad("出现了 iframe");

// ---------- 搜索 ----------
console.log("\n八、搜索框");
function totalOf(h) {
  // 两种形态：「已顯示 20 / 281 條」和「已顯示全部 7 條」
  const m = String(h).match(/\/\s*(\d+)\s*條/) || String(h).match(/全部\s*(\d+)\s*條/);
  return m ? Number(m[1]) : null;
}
function idsOf(h) {
  return [...String(h).matchAll(/data-id="([^"]+)"/g)].map(m => m[1]);
}

const allPosts = global.FISH_RADAR_TOP.posts.concat(global.FISH_RADAR_REST.posts);
const inWindow = allPosts.filter(p => {
  const cut = Date.now() / 1000 - 7 * 86400;
  return !p.published_ts || p.published_ts >= cut;
});

store.q.value = "大肥魚";
store.q.fire("input", { target: store.q });
const t1 = totalOf(store.flow.innerHTML);
const expectFish = inWindow.filter(p =>
  ((p.title || "") + (p.title_t || "") + (p.author || "") + (p.found_by || "") + (p.summary || "")).includes("大肥魚")
).length;
if (t1 === expectFish) ok(`搜「大肥魚」得到 ${t1} 条（和手算一致）`);
else bad(`搜「大肥魚」得到 ${t1} 条，手算是 ${expectFish}`);

store.q.value = "大肥魚 鯨";
store.q.fire("input", { target: store.q });
const t2 = totalOf(store.flow.innerHTML);
const expect2 = inWindow.filter(p => {
  const hay = (p.title || "") + (p.title_t || "") + (p.author || "") + (p.found_by || "") + (p.summary || "");
  return ["大肥魚", "鯨"].every(t => hay.includes(t));
}).length;
if (t2 === expect2) ok(`多关键词按 AND 收窄：${t1} → ${t2} 条（和手算一致）`);
else bad(`多关键词结果 ${t2}，手算是 ${expect2}`);

store.q.value = "zzzzzz";
store.q.fire("input", { target: store.q });
if (/找不到東西/.test(store.flow.innerHTML) && /清空全部篩選/.test(store.flow.innerHTML)) {
  ok("搜不到时给了具体文案和一个「清空全部筛选」按钮");
} else {
  bad("空状态文案不对");
}

store.qclear.fire("click");
if (totalOf(store.flow.innerHTML) === inWindow.length) ok("清空搜索后恢复全部");
else bad("清空搜索后数量不对");

// ---------- 排序 ----------
console.log("\n九、排序");
const byHeat = inWindow.slice().sort((a, b) => (b.heat || 0) - (a.heat || 0)).slice(0, 20).map(p => p.id);
if (JSON.stringify(idsOf(store.flow.innerHTML)) === JSON.stringify(byHeat)) ok("默认按热度排（前 20 条顺序对得上）");
else bad("默认排序不对");

store.sort.fire("click", { target: { closest: s => (s === "[data-s]" ? { dataset: { s: "new" } } : null) } });
const byNew = inWindow.slice().sort((a, b) => (b.published_ts || 0) - (a.published_ts || 0)).slice(0, 20).map(p => p.id);
if (JSON.stringify(idsOf(store.flow.innerHTML)) === JSON.stringify(byNew)) ok("切「最新」：按发布时间重排");
else bad("「最新」排序不对");

store.sort.fire("click", { target: { closest: s => (s === "[data-s]" ? { dataset: { s: "delta" } } : null) } });
const byDelta = inWindow.slice().sort((a, b) => {
  const da = (a.hot_delta === null || a.hot_delta === undefined) ? Infinity : a.hot_delta;
  const db = (b.hot_delta === null || b.hot_delta === undefined) ? Infinity : b.hot_delta;
  if (da !== db) return db - da;
  return (b.heat || 0) - (a.heat || 0);
}).slice(0, 20).map(p => p.id);
if (JSON.stringify(idsOf(store.flow.innerHTML)) === JSON.stringify(byDelta)) ok("切「涨幅」：NEW 排最前，其余按增量");
else bad("「涨幅」排序不对");

// ---------- 数据过旧提醒 ----------
console.log("\n十、数据过旧提醒");
const ageH = (Date.now() - new Date(global.FISH_RADAR_TOP.meta.generated_at).getTime()) / 3600000;
if (ageH < 24) {
  ok(`数据只有 ${ageH.toFixed(1)} 小时，不提醒（符合预期）`);
} else if (/小時前|天前/.test(store.stale.innerHTML) && store.stale.style.display === "block") {
  ok(`数据已 ${ageH.toFixed(0)} 小时，顶部弹出提醒`);
} else {
  bad("数据已过期但没有提醒：" + store.stale.innerHTML.slice(0, 50));
}
if (/class="src"/.test(store.flow.innerHTML)) ok("卡片上有「这条从哪来」的来源小标");
else bad("卡片缺少来源小标");

console.log("\n" + "=".repeat(52));
  if (fails.length) { console.log(`不通过：${fails.length} 项失败`); process.exit(1); }
  console.log("全部通过");
}, 260);
