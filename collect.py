# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 采集脚本
====================

只做一件事：去 GitHub 和 B 站的公开接口，把「AI 娘」相关的帖子抓回来，
筛掉硬核技术贴，按平台各自的热度排好，存成三个文件：

    data/posts.json   —— 给程序看的原始数据
    data/posts.js     —— 给网页看的（双击 index.html 也能读，不需要服务器）
    data/meta.json    —— 这次抓取的体检报告（每个平台抓到几条、有没有失败）

用法：
    python collect.py            正常抓一次（约 3~4 分钟，~52 个请求）
    python collect.py --days 7   只要最近 7 天的

    python collect.py --chunk 10 --chunk-pause 180
        额度模式：每打满 10 个请求就主动停 180 秒，等 B 站的新窗口。
        慢 4 倍，但零 412——将来要逐条抓详情时用这一档。

不需要安装任何第三方库，Python 3.8 以上自带的功能就够了。
（这一点很重要：GitHub Actions 的免费机器上也能直接跑，不用 pip install。）
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import fsutil          # 同目錄的小工具：原子寫，見 fsutil.py

# Windows 控制台默认是 GBK，打印中文会炸，这里强制切成 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

TZ = timezone(timedelta(hours=8))          # 北京时间
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()

# GitHub 允许填一个 token 来提高额度（每小时 60 次 → 5000 次）。
# 本地不填也能跑，只是次数少一点。
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


class RateLimited(Exception):
    """对方的风控把我们拦下来了（B 站典型表现是 HTTP 412）。"""
    pass


# --------------------------------------------------------------------------
# 0. B 站節奏：額度模式
# --------------------------------------------------------------------------
#
# 三天實測得到的結論：B 站限制的是「一段時間內放行多少次」，
# 不是「每秒幾次」。所以把間隔從 3 秒拉到 9 秒，該 412 還是 412
# （9 秒一條、跑到第 11 條就撞的記錄，就是這麼來的）。
#
# 真正有用的兩種檔位：
#   正常档（chunk = 0）：只按 delay 慢慢打。
#       我們一次只發 ~52 個請求，實測 200 秒跑完、零 412，夠用。
#   額度档（chunk = 10, pause = 180）：打滿 10 個就主動停 3 分鐘，
#       假裝是新的窗口再來。慢 4 倍（約 2 條/分鐘），但換來零 412。
#       將來若要逐條抓詳情（拿投幣率），必須用這一檔。
#
# 412 本身是幾十秒到幾分鐘的瞬時風控，不是封號；但被擋之後
# 立刻重試只會讓門關得更久，所以 http_get 那邊是直接拋錯、不重試。

_bili_requests = 0
_bili_pace = {"delay": 3.0, "chunk": 0, "pause": 180.0}

# 412 的缓冲：撞到一次不立刻让整轮挂掉，停一会儿等新窗口，重试这「一个」请求。
# 上限 2 次——再多就说明 IP 确实被盯上了，继续磨只会把门关得更久，直接停手。
SOFT_412 = {"on": False, "pause": 120.0, "used": 0, "cap": 2}


def set_bili_pace(cfg, chunk=None, pause=None):
    """開始抓之前定好這一輪的節奏。chunk=0 表示不分段。"""
    global _bili_requests, _bili_pace
    _bili_requests = 0
    delay = cfg.get("bilibili_delay", 3.0)
    raw_chunk = chunk if chunk is not None else cfg.get("bilibili_chunk", 0)
    raw_pause = pause if pause is not None else cfg.get("bilibili_chunk_pause", 180)
    try:
        chunk_n = max(0, int(raw_chunk or 0))
    except (TypeError, ValueError):
        chunk_n = 0
    try:
        pause_s = max(1.0, float(raw_pause or 180))
    except (TypeError, ValueError):
        pause_s = 180.0
    try:
        delay_s = max(0.0, float(delay or 0))
    except (TypeError, ValueError):
        delay_s = 3.0
    _bili_pace = {"delay": delay_s, "chunk": chunk_n, "pause": pause_s}
    return dict(_bili_pace)


def bili_wait():
    """每個 B 站請求之後叫一次。額度模式下打滿一批就主動關門等新窗口。"""
    global _bili_requests
    _bili_requests += 1
    chunk = _bili_pace["chunk"]
    if chunk and _bili_requests % chunk == 0:
        pause = _bili_pace["pause"]
        print("  · 已發 %d 個請求，按額度模式停 %.0f 秒等新窗口（不是卡住，別關窗口）"
              % (_bili_requests, pause))
        time.sleep(pause)
    else:
        time.sleep(_bili_pace["delay"])


# --------------------------------------------------------------------------
# 一、最基础的网络工具
# --------------------------------------------------------------------------

def http_get(url, headers=None, timeout=25, retries=2):
    """发一个 GET 请求，失败自动重试。返回 (状态码, 文本)。"""
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if headers:
        h.update(headers)
    last = None
    soft_done = False
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 412:
                # 412 是风控，不是网络抖动。但「等一个新窗口再试一次」有效，
                # 「立刻重试」无效——所以这里停 SOFT_412["pause"] 秒，不是 0 秒。
                if (not soft_done and SOFT_412["on"] and attempt < retries
                        and SOFT_412["used"] < SOFT_412["cap"]):
                    soft_done = True
                    SOFT_412["used"] += 1
                    pause = SOFT_412["pause"]
                    print("  · 412：停 %.0f 秒等新窗口，再試這一個請求（本次第 %d/%d 次）"
                          % (pause, SOFT_412["used"], SOFT_412["cap"]))
                    time.sleep(pause)
                    continue
                raise RateLimited("HTTP 412 风控")
            last = "HTTP %s" % e.code
            if e.code in (403, 429):           # 限流，等一下再试
                time.sleep(2 + attempt * 2)
                continue
            break
        except Exception as e:
            last = repr(e)
            time.sleep(1.5 + attempt)
    raise RuntimeError(last or "unknown error")


def strip_tags(s):
    """B 站搜索结果里标题带 <em class="keyword"> 高亮标签，去掉。"""
    s = re.sub(r"<[^>]+>", "", s or "")
    return (s.replace("&amp;", "&").replace("&quot;", '"')
             .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))


def to_iso(ts):
    """把 unix 时间戳转成北京时间字符串。"""
    try:
        return datetime.fromtimestamp(int(ts), TZ).isoformat(timespec="seconds")
    except Exception:
        return None


# --------------------------------------------------------------------------
# 二、B 站：搜索接口
# --------------------------------------------------------------------------

def bilibili_cookie():
    """
    B 站会看 cookie 来决定给不给你数据。先去要一个匿名的 buvid3，
    再把它带在后面的请求里，成功率会高很多。拿不到也不影响，继续跑。
    """
    try:
        _, body = http_get("https://api.bilibili.com/x/frontend/finger/spi",
                           {"Referer": "https://www.bilibili.com/"})
        d = json.loads(body).get("data") or {}
        if d.get("b_3"):
            return "buvid3=%s; buvid4=%s" % (d.get("b_3", ""), d.get("b_4", ""))
    except Exception as e:
        print("  ! 拿 B 站 cookie 失败（不影响继续）：%s" % e)
    return ""


def bilibili_search(keyword, cookie, order="click", page=1):
    """
    搜 B 站视频。order 可以是：
        click    = 按播放量（找“热门”）
        pubdate  = 按发布时间（找“今天刚发的”）
        totalrank= 综合
    返回视频列表，失败返回空列表。
    """
    q = urllib.parse.quote(keyword)
    url = ("https://api.bilibili.com/x/web-interface/search/type"
           "?search_type=video&page=%d&order=%s&keyword=%s" % (page, order, q))
    headers = {"Referer": "https://search.bilibili.com/", "Cookie": cookie}
    try:
        _, body = http_get(url, headers)
        j = json.loads(body)
    except RateLimited:
        raise                      # 交给上层决定「整輪收手」
    except Exception as e:
        print("  ! B站搜索失败 [%s]：%s" % (keyword, e))
        return []

    if j.get("code") != 0:
        print("  ! B站返回 code=%s (%s) 关键词=%s" % (j.get("code"), j.get("message"), keyword))
        return []
    return ((j.get("data") or {}).get("result") or [])


# --------------------------------------------------------------------------
# 三、GitHub：仓库搜索
# --------------------------------------------------------------------------

def github_search(query, per_page=20):
    """搜 GitHub 仓库，按最近更新排序。返回列表，失败返回空。"""
    url = ("https://api.github.com/search/repositories?q=%s"
           "&sort=updated&order=desc&per_page=%d"
           % (urllib.parse.quote(query), per_page))
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + GITHUB_TOKEN
    try:
        _, body = http_get(url, headers)
        j = json.loads(body)
    except Exception as e:
        print("  ! GitHub 搜索失败 [%s]：%s" % (query, e))
        return []

    if "items" not in j:
        print("  ! GitHub 返回异常 [%s]：%s" % (query, str(j)[:120]))
        return []
    return j["items"]


# --------------------------------------------------------------------------
# 四、过滤：这是整个工具最「有脑子」的一步
# --------------------------------------------------------------------------

def norm(s):
    return (s or "").lower()


def match_character(text, ch):
    """这段文字有没有提到这个角色？返回命中的词，没命中返回 None。"""
    t = norm(text)
    for alias in ch["match"]:
        if norm(alias) in t:
            return alias
    # 兜底：搜索关键词去掉「娘」之后的词根，比如 deepseek娘 → deepseek
    for q in ch.get("queries", []):
        base = q.replace("娘", "").strip()
        if len(base) >= 3 and norm(base) in t:
            return base
    return None


def filter_post(title, desc, ch, cfg):
    """
    返回 (是否保留, 相关度)。

    规则：
      1. 必须提到角色，否则跟这个角色无关，丢掉。
      2. 出现「二创类」词 → 强相关，保留。
      3. 出现「技术类」词又没有二创词 → 判定为科技新闻，丢掉。
      4. 都不沾 → 弱相关，保留但打上标记，网页上可以只显示强相关。

    技术词分两档（2026-10-25 加）：
      tech_words      —— 硬词。「评测」「跑分」「显存」这种，一出现基本就是技术帖。
      tech_soft_words —— 软词。「部署」「安装」「配置」「训练」既是技术词，
                         也是普通动词——「在家里部署了一只大肥鱼」是搞笑短剧，
                         不是部署教程。软词要凑够两个才算数。
    """
    text = norm(title) + " " + norm(desc)
    if not match_character(text, ch):
        return False, None

    creative = any(norm(w) in text for w in cfg["creative_words"])
    if creative:
        return True, "strong"

    hard = any(norm(w) in text for w in cfg.get("tech_words", []))
    soft_n = sum(1 for w in cfg.get("tech_soft_words", []) if norm(w) in text)
    if hard or soft_n >= 2:
        return False, None

    return True, "weak"


# --------------------------------------------------------------------------
# 五、把两个平台的数据抓成统一格式
# --------------------------------------------------------------------------

def bilibili_related(bvid, cookie):
    """
    从一条视频扩散出它的「相关推荐」（一般 40 条）。
    这是关键词搜索补不了的洞：那些标题里根本不写角色名的视频
    （比如「人类把一整个B站账号交给了AI」），只能靠这条关系网拽出来。
    """
    url = "https://api.bilibili.com/x/web-interface/archive/related?bvid=" + bvid
    try:
        _, body = http_get(url, {"Referer": "https://www.bilibili.com/video/" + bvid,
                                 "Cookie": cookie, "Origin": "https://www.bilibili.com"})
        j = json.loads(body)
    except RateLimited:
        raise
    except Exception as e:
        print("    ! 相关视频失败 %s：%s" % (bvid, e))
        return []
    if j.get("code") != 0:
        return []
    return j.get("data") or []


def norm_video(v):
    """搜索接口和相关接口返回的结构不一样，这里抹平成统一的。"""
    st = v.get("stat") or {}
    return {
        "bvid": v.get("bvid"),
        "title": strip_tags(v.get("title", "")),
        "desc": strip_tags(v.get("desc") or v.get("description") or ""),
        "author": v.get("author") or (v.get("owner") or {}).get("name") or "",
        # 标签是 UP 主自己填的，经常比标题更能说明这是谁的二创。
        # 《完啦完啦！用户彻底怒了！》标题里一个人名都没有，标签里写着「大肥鱼」。
        "tags": strip_tags(v.get("tag") or ""),
        "play": int(v.get("play") or st.get("view") or 0),
        "pubdate": int(v.get("pubdate") or 0),
        "pic": v.get("pic") or "",
        "danmaku": int(v.get("video_review") or 0),
        "favorites": int(v.get("favorites") or st.get("favorite") or 0),
    }


def bilibili_detail(bvid, cookie):
    """
    按 BV 号取一条视频的详情。
    注意用的是 view/detail 这个接口，而不是常见的 view —— 实测前者不容易被 412。
    """
    url = "https://api.bilibili.com/x/web-interface/view/detail?bvid=" + bvid
    try:
        _, body = http_get(url, {"Referer": "https://www.bilibili.com/video/" + bvid,
                                 "Cookie": cookie, "Origin": "https://www.bilibili.com"})
        j = json.loads(body)
    except RateLimited:
        raise
    except Exception as e:
        print("    ! 取详情失败 %s：%s" % (bvid, e))
        return None
    if j.get("code") != 0:
        print("    ! 详情返回 code=%s (%s)" % (j.get("code"), j.get("message")))
        return None
    return (j.get("data") or {}).get("View")


def load_seeds():
    """
    读 seeds.txt 里人工指定的视频。
    为什么需要它：有些视频标题里一个角色名都没有
    （「人类把一整个B站账号交给了AI」），关键词搜索永远够不着，
    相关推荐也未必连得上，只能靠人指定。
    """
    path = os.path.join(HERE, "seeds.txt")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.search(r"(BV[0-9A-Za-z]{10})", line)
            if m and m.group(1) not in out:
                out.append(m.group(1))
    return out


def collect_bilibili(cfg, days, status):
    """
    B 站采集分两轮：
      第一轮  关键词搜索（七拐八弯地找）
      第二轮  从已抓到的视频顺着「相关推荐」往外爬（顺藤摸瓜）

    只靠第一轮会漏掉大量标题不写角色名的视频，这次实测就漏了两条几十万播放的。
    """
    cookie = bilibili_cookie()
    cutoff = time.time() - days * 86400
    out, seen = [], set()
    blocked = False

    def absorb(videos, ch_hint, source, force=False, ignore_age=False, classic=False):
        """把一批视频过筛、去重、转成帖子。返回这一批收了几条。

        force=True 是给 seeds.txt 用的：人工指定的内容无条件收，
        哪怕它标题里没有角色名（那就归类到「其他」）。

        ignore_age=True 是给「經典」用的：不看发布时间。B 站按播放排序的
        搜索结果是「历史最热」，那些 400 万播放的片子大多早就滑出 7 天窗口了，
        不收就永远看不到它们——但也不该混进「近期熱帖」里，所以标 classic。
        """
        kept = 0
        for raw in videos:
            v = norm_video(raw)
            bv = v["bvid"]
            if not bv or bv in seen:
                continue
            if not force and not ignore_age and v["pubdate"] and v["pubdate"] < cutoff:
                continue                      # 太旧，不是「近期热帖」
            # 标题 + 简介 + UP 主名 + 标签，一起看。
            # UP 主名本身就是身份标签，比如「Claude大小姐在运营」，
            # 视频标题里一个角色词都没有，但作者名写死了。
            text = v["title"] + " " + v["desc"] + " " + v["author"] + " " + v.get("tags", "")

            if ch_hint:
                good, level = filter_post(text, "", ch_hint, cfg)
                ch = ch_hint if good else None
            else:
                ch, level = None, None
                # 先看 UP 主名，再看正文。
                # 因为「Gemini哈基米在运营」发的视频，标题里可能通篇在聊大肥鱼，
                # 这时候账号身份比标题里随口提的名字更可信。
                for cand in cfg["characters"]:
                    if match_character(v["author"], cand):
                        good, lv = filter_post(text, "", cand, cfg)
                        if good:
                            ch, level = cand, lv
                            break
                if not ch:
                    for cand in cfg["characters"]:
                        good, lv = filter_post(text, "", cand, cfg)
                        if good:
                            ch, level = cand, lv
                            break
            if not ch:
                if not force:
                    continue
                # 人工指定的内容，认不出是哪个角色也照收，归到「其他」
                ch = {"id": "other"}
                level = "weak"

            seen.add(bv)
            post = {
                "id": "bilibili:" + bv,
                "platform": "bilibili",
                "character": ch["id"],
                "title": v["title"].strip(),
                "summary": v["desc"].strip()[:140],
                "author": v["author"],
                "url": "https://www.bilibili.com/video/" + bv,
                "cover": ("https:" + v["pic"]) if v["pic"].startswith("//") else v["pic"],
                "published": to_iso(v["pubdate"]),
                "published_ts": v["pubdate"],
                "heat": v["play"],
                "heat_label": fmt_wan(v["play"]) + " 播放",
                "metrics": {
                    "播放": v["play"],
                    "弹幕": v["danmaku"],
                    "收藏": v["favorites"],
                },
                "match": level,
                "found_by": source,
                "pinned": force,
                "first_seen": datetime.now(TZ).isoformat(timespec="seconds"),
                "last_seen": datetime.now(TZ).isoformat(timespec="seconds"),
            }
            if classic:
                post["classic"] = True
            out.append(post)
            kept += 1
        return kept

    # ---------------- 第零轮：人工指定的种子 ----------------
    seeds = load_seeds()
    if seeds:
        print("  → 手動種子 %d 條（seeds.txt），先無條件收進來" % len(seeds))
        got = 0
        for bv in seeds:
            try:
                d = bilibili_detail(bv, cookie)
            except RateLimited as e:
                print("  ! 取種子詳情被風控（%s），這輪跳過種子。" % e)
                blocked = True
                break
            if d:
                got += absorb([d], None, "手動指定", force=True)
            bili_wait()
        print("    種子收進 %d 條（累计 %d）" % (got, len(out)))

    # ---------------- 第一轮：关键词搜索 ----------------
    tasks = []
    for ch in cfg["characters"]:
        for kw in ch["queries"]:
            for order in ("click", "pubdate"):
                tasks.append((ch, kw, order))
    # 全局词：不属于某个角色，谁匹配上算谁的
    for kw in cfg.get("global_queries", []):
        tasks.append((None, kw, "click"))

    classic_n = int(cfg.get("classic_per_query", 3) or 0)
    classic_total = 0

    for ch, kw, order in tasks:
        try:
            vids = bilibili_search(kw, cookie, order=order)
        except RateLimited as e:
            print("  ! 被 B 站风控拦下（%s）。停手，不再硬撞，本轮 B 站数据不完整。" % e)
            blocked = True
            break
        kept = absorb(vids, ch, "搜尋：" + kw)
        # 按播放排序的结果里，排最前的往往是几个月前的爆款，早滑出窗口了。
        # 顺手把它们各留 top N 条当「經典」——不额外发请求，只是不丢掉已经拿到的。
        if order == "click" and classic_n:
            top = sorted(vids, key=lambda r: -norm_video(r)["play"])[:classic_n]
            classic_total += absorb(top, ch, "搜尋：" + kw, ignore_age=True, classic=True)
        print("  B站 %-12s order=%-8s 收到 %d 条（累计 %d）" % (kw, order, kept, len(out)))
        bili_wait()   # 節奏由 set_bili_pace 決定：正常是間隔，額度模式是打一批停一段

    if classic_total:
        print("  ★ 經典（歷史最熱，不受 7 天窗口限制）：%d 條" % classic_total)

    # ---------------- 第二轮：顺着相关推荐往外爬 ----------------
    if not blocked and out:
        by_heat = sorted(out, key=lambda p: -int(p.get("heat") or 0))
        by_time = sorted(out, key=lambda p: -int(p.get("published_ts") or 0))
        seed_ids = []
        n_rel = int(cfg.get("bilibili_related_seeds", 13))
        for p in by_heat[:max(1, n_rel - 3)] + by_time[:3]:   # 最热的若干条 + 最新的 3 条
            bv = p["url"].rsplit("/", 1)[-1]
            if bv not in seed_ids:
                seed_ids.append(bv)

        print("  → 从 %d 条种子视频往外扩散『相关推荐』" % len(seed_ids))
        gained = 0
        for i, bv in enumerate(seed_ids, 1):
            try:
                rel = bilibili_related(bv, cookie)
            except RateLimited as e:
                print("  ! 相关推荐也被风控（%s），停止扩散，保留已抓到的。" % e)
                blocked = True
                break
            got = absorb(rel, None, "相關：" + bv)
            gained += got
            if got:
                print("     [%d/%d] %s → 新增 %d 条（累计 %d）"
                      % (i, len(seed_ids), bv, got, len(out)))
            bili_wait()
        print("  → 扩散结束，多抓到 %d 条关键词搜不到的" % gained)

    # ---------------- 第三轮：按 UP 主名再搜一次 ----------------
    # 实测发现 B 站的视频搜索连 UP 主名字一起认。
    # 而「Claude大小姐在运营」「ChatGPT龙娘在运营」这类账号，
    # 名字本身就是身份标签，视频标题却经常一个角色词都不带。
    if not blocked and out:
        author_hits = {}
        for p in out:
            a = (p.get("author") or "").strip()
            if not a:
                continue
            if any(match_character(a, ch) for ch in cfg["characters"]):
                author_hits[a] = author_hits.get(a, 0) + 1
        authors = []
        # 手動盯的 UP 主排最前面：用戶點名要看的創作者，不管名字裡有沒有角色詞，
        # 每輪都去掃一遍。星落落_oi、冬冰、ZipZipPipe 這種就是。
        watch = [a.strip() for a in cfg.get("bilibili_author_watch", []) if a and a.strip()]
        cap = max(len(watch), int(cfg.get("bilibili_author_seeds", 8)))
        for a in watch + sorted(author_hits, key=lambda x: -author_hits[x]):
            if a not in authors:
                authors.append(a)
            if len(authors) >= cap:
                break

        if authors:
            print("  → 按 UP 主名再搜 %d 個（手動盯的 %d 個）"
                  % (len(authors), len(watch)))
        gained2 = 0
        for a in authors:
            try:
                vids = bilibili_search(a, cookie, order="pubdate")
            except RateLimited as e:
                print("  ! 按 UP 主搜索被风控（%s），停止第三轮。" % e)
                blocked = True
                break
            got = absorb(vids, None, "UP主：" + a)
            gained2 += got
            if got:
                print("     UP主 %-18s → 新增 %d 条（累计 %d）" % (a[:18], got, len(out)))
            bili_wait()
        print("  → 第三轮结束，多抓到 %d 条" % gained2)

    status["blocked"] = blocked
    status["ok"] = not blocked
    return out




def fmt_wan(n):
    """1540881 → 154.1万"""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n >= 100000000:
        return "%.2f亿" % (n / 100000000.0)
    if n >= 10000:
        return "%.1f万" % (n / 10000.0)
    return str(n)


def github_repo(full_name):
    """按 owner/repo 精确取一个仓库（给 config 里的 github_seeds 用）。"""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + GITHUB_TOKEN
    try:
        _, body = http_get("https://api.github.com/repos/" + full_name, headers)
        return json.loads(body)
    except Exception as e:
        print("  ! 取仓库失败 %s：%s" % (full_name, e))
        return None


def github_post(r, ch_id, level, source, pinned=False, note=None):
    """把 GitHub 仓库对象转成一条帖子。"""
    full = r.get("full_name")
    stars = int(r.get("stargazers_count") or 0)
    pushed = 0
    try:
        pushed = int(datetime.strptime(
            r.get("pushed_at", "")[:19], "%Y-%m-%dT%H:%M:%S"
        ).replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        pass
    return {
        "id": "github:" + full,
        "platform": "github",
        "character": ch_id,
        "title": r.get("name", full),
        "summary": (r.get("description") or "（這個倉庫沒有寫簡介）")[:140],
        "author": (r.get("owner") or {}).get("login", ""),
        "url": r.get("html_url", ""),
        "cover": (r.get("owner") or {}).get("avatar_url", ""),
        "published": to_iso(pushed) if pushed else None,
        "published_ts": pushed,
        "heat": stars,
        "heat_label": "%d ★" % stars,
        "metrics": {
            "Star": stars,
            "Fork": int(r.get("forks_count") or 0),
            "Issue": int(r.get("open_issues_count") or 0),
        },
        "match": level,
        "found_by": source,
        "pinned": pinned,
        "note": note,
        "first_seen": datetime.now(TZ).isoformat(timespec="seconds"),
        "last_seen": datetime.now(TZ).isoformat(timespec="seconds"),
    }


def collect_github(cfg, days):
    cutoff = time.time() - days * 86400
    out = []
    seen = set()

    # ---------------- 人工指定的仓库 ----------------
    # 关键词搜索认的是仓库名和简介，像 dsh-bili-whale 这种
    # 简介里只有「鱼」「B 站」，一个角色词都没有的，永远搜不到。
    for seed in cfg.get("github_seeds", []):
        full = seed.get("repo")
        r = github_repo(full)
        if not r:
            continue
        seen.add(full)
        out.append(github_post(r, seed.get("character", "other"), "weak",
                               "手動指定", pinned=True, note=seed.get("note")))
        print("  GitHub 手動指定 %-28s %d ★" % (full, int(r.get("stargazers_count") or 0)))

    for q in cfg["github_queries"]:
        repos = github_search(q, per_page=20)
        kept = 0
        for r in repos:
            full = r.get("full_name")
            if not full or full in seen:
                continue
            text = " ".join([
                r.get("name", ""), r.get("full_name", ""),
                r.get("description") or "",
                " ".join(r.get("topics") or []),
            ])
            ch_hit = None
            for ch in cfg["characters"]:
                if match_character(text, ch):
                    ch_hit = ch
                    break
            if not ch_hit:
                continue
            ok, level = filter_post(text, "", ch_hit, cfg)
            if not ok:
                continue
            post = github_post(r, ch_hit["id"], level, "搜尋：" + q)
            if post["published_ts"] and post["published_ts"] < cutoff:
                continue
            seen.add(full)
            out.append(post)
            kept += 1
        print("  GitHub %-18s 抓到 %d 条（累计 %d）" % (q, kept, len(out)))
        time.sleep(3.2)   # 未登录时 GitHub 搜索限速 10 次/分钟
    return out


# --------------------------------------------------------------------------
# 六、去重 + 记录「第一次见到它的时间」
# --------------------------------------------------------------------------

def merge_history(posts, cutoff, carry_cutoff):
    """
    讀上一次的 posts.json，做三件事：

      1. 同一條帖子（同一個 id）不重複收，只更新熱度，
         並算出「比上次漲了多少」，網頁上就能顯示 ↑
      2. 保留第一次見到它的時間，這樣「NEW」只會亮一次
      3. 上次抓到了、這次因為搜索排名變動而掉出去的帖子，
         只要還在時間窗口內，就繼續留著（標記 carried），
         不然使用者重新整理一次，東西就莫名消失了
    """
    path = os.path.join(DATA_DIR, "posts.json")
    old = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for p in json.load(f).get("posts", []):
                    old[p.get("id")] = p
        except Exception as e:
            print("  ! 讀舊數據失敗（當作第一次跑）：%s" % e)

    found = set()
    for p in posts:
        found.add(p["id"])
        prev = old.get(p["id"])
        if prev:
            p["first_seen"] = prev.get("first_seen") or p["first_seen"]
            try:
                p["hot_delta"] = int(p["heat"]) - int(prev.get("heat") or 0)
            except Exception:
                p["hot_delta"] = 0
        else:
            p["hot_delta"] = None      # None = 这次新出现的

    carried = []
    for pid, op in old.items():
        if pid in found:
            continue
        if op.get("platform") not in ("bilibili", "github"):
            continue
        if op.get("pinned") or op.get("classic"):
            op["hot_delta"] = 0
            carried.append(op)          # 人工指定的、和「經典」，永远不退场
            continue
        if int(op.get("published_ts") or 0) < carry_cutoff:
            continue                    # 掉出结果又太旧了，该退场
        op["carried"] = True            # 这次没搜到，但还留在榜上
        op["hot_delta"] = 0
        carried.append(op)

    if carried:
        print("  + 保留 %d 条上次抓到、这次掉出搜索结果的帖子" % len(carried))
    return posts + carried



# --------------------------------------------------------------------------
# 六点五、自動化要用的：健康紀錄 + 開跑前自檢
# --------------------------------------------------------------------------

def read_health():
    p = os.path.join(DATA_DIR, "health.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_health(ok, err, n_posts, took):
    """每一輪寫一次。連續失敗次數要累加，所以得先讀上一輪的。"""
    prev = read_health()
    now = datetime.now(TZ).isoformat(timespec="seconds")
    fails = 0 if ok else int(prev.get("consecutive_failures") or 0) + 1
    h = {
        "last_attempt": now,
        "last_ok": now if ok else prev.get("last_ok"),
        "consecutive_failures": fails,
        "last_error": None if ok else err,
        "posts": n_posts,
        "took_seconds": took,
        "runs": int(prev.get("runs") or 0) + 1,
        "ok_runs": int(prev.get("ok_runs") or 0) + (1 if ok else 0),
    }
    fsutil.write_json(os.path.join(DATA_DIR, "health.json"), h)
    return h


def other_crawler_busy(cfg):
    """
    鐵律②的機器版。

    ai-film-radar 也在打 B 站，兩個同時跑會讓 412 來得更快。以前靠人問一句
    「對面停了沒」，定時跑之後沒人盯著，所以讓它自己看一眼對方的數據庫
    最後寫入時間。回傳 (路徑, 幾秒前) = 對面還在動；回傳 None = 可以開工。
    """
    g = cfg.get("guard") or {}
    if not g.get("enabled"):
        return None
    rel = (g.get("other_db") or "").strip()
    if not rel:
        return None
    path = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(HERE, rel))
    if not os.path.exists(path):
        return None                      # 沒裝那個項目，就沒什麼好等的
    minutes = float(g.get("minutes") or 10)
    age = time.time() - os.path.getmtime(path)
    return (path, age) if age < minutes * 60 else None


# --------------------------------------------------------------------------
# 七、主流程
# --------------------------------------------------------------------------

def main():
    days = None                      # None = 沒指定，等一下從 config.json 的 window_days 讀
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            pass

    # 額度模式的兩個旋鈕，可以臨時用命令行覆蓋，不用改 config.json：
    #   python collect.py --chunk 10 --chunk-pause 180
    chunk_arg = pause_arg = None
    for flag, setter in (("--chunk", "chunk"), ("--chunk-pause", "pause")):
        if flag in sys.argv:
            try:
                val = float(sys.argv[sys.argv.index(flag) + 1])
                if setter == "chunk":
                    chunk_arg = int(val)
                else:
                    pause_arg = val
            except Exception:
                print("  ! %s 后面的数字读不懂，忽略这个参数" % flag)

    with open(os.path.join(HERE, "config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if days is None:
        # 採集窗口。頁面上有「近 7 天 / 近 30 天 / 全部時間」三個檢視，
        # 但抓回來的資料得先涵蓋 30 天，否則點了 30 天也是空的。
        try:
            days = int(cfg.get("window_days", 30))
        except (TypeError, ValueError):
            days = 30

    pace = set_bili_pace(cfg, chunk=chunk_arg, pause=pause_arg)
    SOFT_412["on"] = True
    SOFT_412["used"] = 0
    try:
        SOFT_412["pause"] = max(30.0, float(cfg.get("bilibili_412_pause", 120) or 120))
    except (TypeError, ValueError):
        SOFT_412["pause"] = 120.0

    os.makedirs(DATA_DIR, exist_ok=True)
    started = datetime.now(TZ)
    print("=" * 62)
    print("肥鱼雷达 · 开始抓取  %s（最近 %d 天）" % (started.strftime("%Y-%m-%d %H:%M"), days))
    print("=" * 62)

    busy = other_crawler_busy(cfg)
    if busy:
        print("=" * 62)
        print("  暫停：另一個項目還在爬 B 站")
        print("  %s 在 %d 秒前才寫過。" % (os.path.basename(busy[0]), busy[1]))
        print("  兩個腳本同時打，412 會來得更快。這一輪什麼都不動，等對方停了再跑。")
        print("=" * 62)
        return 3

    print("\n[B 站]")
    if pace["chunk"]:
        print("  節奏：每 %d 個請求停 %.0f 秒（額度模式）"
              % (pace["chunk"], pace["pause"]))
    else:
        print("  節奏：每個請求間隔 %.1f 秒（正常档）" % pace["delay"])
    bi_status = {}
    try:
        bi = collect_bilibili(cfg, days, bi_status)
        bi_ok = bi_status.get("ok", True)
        bi_blocked = bi_status.get("blocked", False)
    except Exception as e:
        print("  !! B站整体失败：%s" % e)
        bi, bi_ok, bi_blocked = [], False, True

    print("\n[GitHub]")
    try:
        gh = collect_github(cfg, days)
        gh_ok = True
    except Exception as e:
        print("  !! GitHub 整体失败：%s" % e)
        gh, gh_ok = [], False

    # 掉出搜索结果的旧帖，最多再留 3 天；人工钉选的永远留着
    carry_cutoff = time.time() - min(days, 3) * 86400
    posts = merge_history(bi + gh, time.time() - days * 86400, carry_cutoff)

    # 每个平台内部各排各的：B 站按播放，GitHub 按 Star。
    # 跨平台比大小没有意义，所以网页上也只做「分平台」，不做总榜。
    for platform in ("bilibili", "github"):
        group = [p for p in posts if p["platform"] == platform]
        group.sort(key=lambda x: (-int(x.get("heat") or 0), -int(x.get("published_ts") or 0)))

    meta = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "took_seconds": round((datetime.now(TZ) - started).total_seconds(), 1),
        "window_days": days,
        "platforms": {
            "bilibili": {"ok": bi_ok, "count": len(bi),
                         "note": ("被風控攔下，本輪數據不完整（隔幾分鐘再跑一次即可）"
                                  if bi_blocked else
                                  "公開搜索接口，按播放量 + 最新兩種排序採集")},
            "github":   {"ok": gh_ok, "count": len(gh), "note": "公開 Search API，按最近更新排序"},
            "xiaohongshu": {"ok": False, "count": 0, "note": "未接入：需要 X-s/X-t 簽名與登錄態，本工具暫不抓取"},
            "twitter":     {"ok": False, "count": 0, "note": "未接入：官方免費 API 已不提供搜索讀取"},
            "heybox":      {"ok": False, "count": 0, "note": "未接入：App 接口需要動態簽名 hkey"},
        },
        "total": len(posts),
    }

    # 這一輪算成功還是失敗：B 站被 412 擋、或兩個平台都空手，都算失敗。
    ok = bool(bi_ok and gh_ok and (bi or gh))
    if bi_blocked:
        err = "B 站被風控攔下（412），本輪數據不完整"
    elif not gh_ok:
        err = "GitHub 這一輪失敗"
    elif not ok:
        err = "兩個平台都沒抓到東西"
    else:
        err = None
    health = write_health(ok, err, len(posts), round((datetime.now(TZ) - started).total_seconds(), 1))
    meta["automation"] = {
        "last_ok": health.get("last_ok"),
        "consecutive_failures": health.get("consecutive_failures", 0),
        "last_error": health.get("last_error"),
    }

    # 方法頁（method.html）頂部那五個數字由 split_posts.py 一起寫進 data/stats.js，
    # 因為它是資料處理的最後一步，永遠跟最終的 posts.json 對得上。

    # 三份數據全部走原子寫：寧可這輪不更新，也不要留一個半截的 JSON。
    fsutil.write_json(os.path.join(DATA_DIR, "posts.json"), {"meta": meta, "posts": posts})

    # 给网页用的版本：包一层 window.FISH_RADAR，这样双击 index.html（file://）
    # 也能直接读，不会撞上浏览器对本地 fetch JSON 的限制。
    fsutil.write_text(
        os.path.join(DATA_DIR, "posts.js"),
        "/* 由 collect.py 自动生成，请不要手改 */\n"
        "window.FISH_RADAR = " + json.dumps({"meta": meta, "posts": posts}, ensure_ascii=False) + ";\n")

    fsutil.write_json(os.path.join(DATA_DIR, "meta.json"), meta)

    carried_n = len(posts) - len(bi) - len(gh)
    print("\n" + "=" * 62)
    print("本轮新抓：B 站 %d 条，GitHub %d 条" % (len(bi), len(gh)))
    print("加上沿用上次的 %d 条，榜上共 %d 条，用时 %.1f 秒"
          % (carried_n, len(posts), meta["took_seconds"]))
    print("数据已写入：" + DATA_DIR)

    # 顺序很重要：先补繁体标题，再拆首屏。
    # 反过来的话，新抓的那批帖子在 posts_top/rest 里没有 title_t，
    # 网页切繁体时只能退回简体标题——一个很容易看不出来的瑕疵。
    try:
        import localize
        localize.build_title_t()
        localize.build_i18n_map()
    except Exception as e:
        print("  ! 简繁转换跳过（网页会退回简体标题，不影响别的）：%s" % e)

    # 顺手把首屏拆了，不然网页那边还是旧的首屏 30 条
    try:
        import split_posts
        info = split_posts.build(quiet=True)
        print("首屏拆分：%d 条 → %.1f KB，其余 %d 条 → %.1f KB"
              % (info["top"], info["top_kb"], info["rest"], info["rest_kb"]))
    except Exception as e:
        print("  ! 首屏拆分失败（网页仍能开，只是首屏用旧的）：%s" % e)
    print("=" * 62)


if __name__ == "__main__":
    sys.exit(main() or 0)
