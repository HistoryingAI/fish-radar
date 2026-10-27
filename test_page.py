#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 页面体检
====================

不联网、不开浏览器，只检查 index.html 和它引用的文件有没有明显毛病。
借的是 ai-film-radar 那套「test_pages.py」的思路。

跑法：
    python test_page.py

任何一条不过，退出码是 1。
"""

import os
import re
import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")

fails = []
warns = []


def ok(msg):
    print("  [OK]   " + msg)


def bad(msg):
    print("  [FAIL] " + msg)
    fails.append(msg)


def warn(msg):
    print("  [WARN] " + msg)
    warns.append(msg)


def main():
    if not os.path.exists(INDEX):
        print("找不到 index.html")
        return 1

    html = open(INDEX, encoding="utf-8").read()

    print("\n一、结构")
    # 1. 重复 id（踩过的坑：id 撞了会导致 JS 抓错元素、后半页空白）
    ids = re.findall(r'\bid="([^"]+)"', html)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        bad("有重复 id：%s" % ", ".join(dup))
    else:
        ok("没有重复 id（共 %d 个）" % len(ids))

    # 2. 标签大致闭合
    for tag in ("div", "section", "footer", "script", "style"):
        o = len(re.findall(r"<%s[\s>]" % tag, html))
        c = len(re.findall(r"</%s>" % tag, html))
        if o != c:
            bad("<%s> 开 %d 个、闭 %d 个" % (tag, o, c))
    if not fails:
        ok("主要标签开闭数量一致")

    print("\n二、分享与合规")
    if 'property="og:image"' in html and 'name="twitter:card"' in html:
        ok("有 OG / Twitter 分享 meta")
    else:
        bad("缺少 og:image 或 twitter:card")

    if "免責聲明" in html or "免责声明" in html:
        ok("页脚有免责声明")
    else:
        bad("页脚没有免责声明")

    if "og-cover.jpg" in html:
        if os.path.exists(os.path.join(HERE, "og-cover.jpg")):
            ok("og-cover.jpg 存在")
        else:
            bad("html 引用了 og-cover.jpg，但文件不存在")
        if re.search(r'og:image"\s+content="(https?:)?//', html):
            ok("og:image 用的是绝对地址")
        else:
            warn("og:image 还是相对路径——本机预览没问题，上线后微信／B 站抓不到，要改成绝对网址")

    print("\n三、数据文件")
    for src in re.findall(r'<script src="([^"]+)"', html):
        path = os.path.join(HERE, src.replace("/", os.sep))
        if os.path.exists(path):
            ok("%-22s %.1f KB" % (src, os.path.getsize(path) / 1024))
        else:
            bad("引用了 %s，但文件不存在" % src)

    # 首屏拆分是否生效：不能还挂着老的 256KB posts.js
    if 'src="data/posts.js"' in html:
        bad("还在同步加载 data/posts.js（没有走首屏拆分）")
    else:
        ok("首屏已拆分，未同步加载全量 posts.js")

    if 'src="data/posts_top.js"' in html:
        ok("首屏脚本是 posts_top.js")
    else:
        bad("首屏脚本不是 posts_top.js")

    # 拆分文件里必须带着 meta（否则统计卡会显示 0）
    top = os.path.join(HERE, "data", "posts_top.js")
    if os.path.exists(top):
        txt = open(top, encoding="utf-8").read()
        if '"meta"' in txt and '"platforms"' in txt:
            ok("posts_top.js 带了 meta（统计卡不会显示 0）")
        else:
            bad("posts_top.js 没带 meta，统计卡会显示 0")
        if '"platform": "github"' in txt:
            bad("posts_top.js 里还有 GitHub 条目（hide_platforms 没生效，跑一次 split_posts.py）")
        else:
            ok("posts_top.js 不含 GitHub（公开版只管 B 站）")

    print("\n四、内容")
    for word, label in [("肥魚雷達", "标题"), ("開啟原帖", "原帖链接"),
                        ("導出 CSV", "CSV 导出按钮"), ("載入中", "首屏加载提示")]:
        if word in html:
            ok("有%s" % label)
        else:
            bad("缺少%s" % label)

    print("\n五、三个新功能")
    if 'id="langBtn"' in html and 'id="themeBtn"' in html:
        ok("有简繁 / 深浅色两个开关")
    else:
        bad("缺少 langBtn 或 themeBtn")

    if 'data-theme="light"' in html and "--card:#ffffff" in html.replace(" ", ""):
        ok("有浅色主题变量")
    elif 'body[data-theme="light"]' in html:
        ok("有浅色主题样式")
    else:
        bad("没有浅色主题样式")

    if "載入更多" in html and "PAGE_SIZE = 20" in html:
        ok("有「▶ 載入更多」且每页 20 条")
    else:
        bad("分页没做或每页条数不对")

    if 'src="data/i18n.js"' in html:
        ok("引用了简繁字表 i18n.js")
    else:
        bad("没有引用 data/i18n.js")

    # 数据里每条都应该有繁体标题
    tp = os.path.join(HERE, "data", "posts.json")
    if os.path.exists(tp):
        with open(tp, encoding="utf-8") as f:
            posts = json.load(f).get("posts", [])
        miss = [p for p in posts if not p.get("title_t")]
        if miss:
            bad("%d 条没有 title_t（繁体标题），跑 python localize.py" % len(miss))
        else:
            ok("%d 条都带繁体标题" % len(posts))

    print("\n六、推广位")
    if "<iframe" in html.lower():
        bad("页面里出现了 iframe —— 推广位只能用超链接")
    else:
        ok("没有 iframe")

    if 'id="promo"' in html and 'src="promos.js"' in html:
        ok("有推广位容器，内容来自 promos.js")
    else:
        bad("缺少推广位容器或没引用 promos.js")

    promo_js = os.path.join(HERE, "promos.js")
    if os.path.exists(promo_js):
        txt = open(promo_js, encoding="utf-8").read()
        # 只看代码，不看注释（注释里提到 target / iframe 是正常的说明文字）
        code = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        if "target=" in code or "<iframe" in code.lower():
            bad("promos.js 的代码里手写了 target 或 iframe —— 链接属性由页面统一加")
        else:
            ok("promos.js 只放数据，不自己拼链接属性")
        if "bilibili.com/opus/" in code:
            ok("活动链接在 promos.js 里")
        else:
            warn("promos.js 里没有找到 B 站活动链接")
        for m in re.findall(r'img:\s*"([^"]+)"', code):
            if os.path.exists(os.path.join(HERE, m.replace("/", os.sep))):
                ok("推广图存在：%s" % m)
            else:
                bad("推广图不存在：%s" % m)
    else:
        bad("没有 promos.js")

    print("\n七、搜索 / 排序 / 过期提醒")
    if 'id="q"' in html and 'type="search"' in html:
        ok("有搜索框")
    else:
        bad("没有搜索框")

    if all(('data-s="%s"' % s) in html for s in ("heat", "new", "delta")):
        ok("有三种排序：热度 / 最新 / 涨幅")
    else:
        bad("排序选项不全")

    if 'id="stale"' in html and "renderStale" in html:
        ok("有数据过旧提醒（超过 24 小时）")
    else:
        bad("没有过旧提醒")

    if "function sourceChip" in html:
        ok("卡片有「来源」小标（搜索 / 相关 / UP主 / 手动）")
    else:
        bad("卡片没有来源小标")

    if "/" in html and "keydown" in html:
        ok("有 / 快捷键聚焦搜索")
    else:
        warn("没看到 / 快捷键")

    print("\n八、平台只剩 B 站（2026-10-27 的決定）")
    stray = [w for w in ("小紅書", "小红书", "推特", "小黑盒") if w in html]
    if stray:
        bad("页面上还有「%s」——公开版只放 B 站" % "、".join(stray))
    else:
        ok("没有小红书／推特／小黑盒的痕迹")

    if 'id="cols"' in html or "分平台榜" in html:
        bad("还留着「分平台榜」")
    else:
        ok("分平台榜已移除")

    cfg_path = os.path.join(HERE, "config.json")
    if os.path.exists(cfg_path):
        cfg = open(cfg_path, encoding="utf-8").read()
        if '"hide_platforms"' in cfg and "github" in cfg.split('"hide_platforms"')[1][:40]:
            ok("config.json 把 github 放进 hide_platforms")
        else:
            warn("config.json 的 hide_platforms 里没有 github，GitHub 会重新出现在公开页")

    print("\n" + "=" * 52)
    if fails:
        print("不通过：%d 项失败，%d 项警告" % (len(fails), len(warns)))
        for f in fails:
            print("  - " + f)
        return 1
    print("全部通过（%d 项警告）" % len(warns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
