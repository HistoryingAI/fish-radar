# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 分享卡片
====================

生成 og-cover.jpg（1200×630），就是链接贴到微信／B 站／Discord 时
自动展开的那张图。纯本地画，不联网、不下载字体。

跑法：
    python make_og.py
"""

import json
import os
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1200, 630

FONT_CANDIDATES = [
    ("C:/Windows/Fonts/msjhbd.ttc", 0),      # 微软正黑 粗
    ("C:/Windows/Fonts/msyhbd.ttc", 0),      # 微软雅黑 粗
    ("C:/Windows/Fonts/msjh.ttc", 0),
    ("C:/Windows/Fonts/simhei.ttf", 0),
]


def pick_font(size):
    for path, idx in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()


def vgrad(img, top, bottom):
    """竖着的渐变，比纯色好看一点点。"""
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)


def public_stats():
    """跟 split_posts.py 用同一套規則：config.json 的 hide_platforms 裡的不算公開條目。

    分享卡片上的「收錄 N 條」要跟網頁上看到的數字一致，
    不然貼到群裡寫 703、點進去只有 644，看起來就像在虛報。
    """
    stats = {"total": 0, "strong": 0, "classic": 0, "generated": ""}
    p = os.path.join(HERE, "data", "posts.json")
    if not os.path.exists(p):
        return stats

    hidden = []
    try:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
            hidden = [str(x) for x in (json.load(f).get("hide_platforms") or [])]
    except Exception:
        pass

    with open(p, encoding="utf-8") as f:
        doc = json.load(f)
    pub = [x for x in doc.get("posts", []) if x.get("platform") not in hidden]
    stats["total"] = len(pub)
    stats["strong"] = sum(1 for x in pub if x.get("match") == "strong")
    stats["classic"] = sum(1 for x in pub if x.get("classic"))
    g = doc.get("meta", {}).get("generated_at", "")
    if g:
        stats["generated"] = g[:10]
    return stats


def main():
    stats = public_stats()

    img = Image.new("RGB", (W, H))
    vgrad(img, (10, 18, 32), (7, 13, 24))
    d = ImageDraw.Draw(img, "RGBA")

    # 背景网格
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(120, 180, 255, 12))
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(120, 180, 255, 12))

    # 右上角光晕
    for r in range(420, 0, -6):
        a = int(3 * (1 - r / 420.0) + 1)
        d.ellipse([W - r - 60, -r + 40, W + r - 60, r + 40], fill=(58, 134, 255, a))

    # 左侧强调条
    d.rounded_rectangle([72, 150, 80, 420], radius=4, fill=(76, 201, 240, 255))

    d.text((104, 128), "肥魚雷達", font=pick_font(96), fill=(232, 241, 255, 255))
    d.text((110, 244), "F I S H   R A D A R", font=pick_font(30), fill=(76, 201, 240, 230))

    d.text((110, 306), "AI 娘二創 · B 站熱帖聚合",
           font=pick_font(40), fill=(168, 194, 226, 255))
    d.text((110, 366), "每一條都連回原帖，不搬運圖片",
           font=pick_font(26), fill=(122, 146, 178, 255))

    # 底部数字条
    box_y = 470
    d.rounded_rectangle([104, box_y, W - 104, box_y + 92], radius=16,
                        fill=(18, 32, 54, 220), outline=(76, 201, 240, 90), width=1)
    items = [
        ("收錄", "%d 條" % stats["total"]),
        ("強相關", "%d" % stats["strong"]),
        ("經典", "%d" % stats["classic"]),
    ]
    x = 136
    for label, val in items:
        d.text((x, box_y + 18), label, font=pick_font(20), fill=(110, 133, 165, 255))
        d.text((x, box_y + 44), val, font=pick_font(34), fill=(232, 241, 255, 255))
        x += 250

    if stats["generated"]:
        d.text((104, 588), "數據抓取於 " + stats["generated"] + " · 非官方 · 開源",
               font=pick_font(20), fill=(80, 100, 130, 255))

    out = os.path.join(HERE, "og-cover.jpg")
    img.save(out, "JPEG", quality=90, optimize=True)
    print("已生成 %s（%d×%d）· %.1f KB · 收錄 %d 條"
          % (os.path.basename(out), W, H, os.path.getsize(out) / 1024, stats["total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
