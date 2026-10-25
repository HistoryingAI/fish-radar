# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 简繁双语
====================

B 站抓下来的标题是简体，网页界面是繁体。这个脚本做两件事：

  1. 给每条帖子加一个 title_t（繁体标题），用 OpenCC 的 s2t 词典转，
     是「词级」转换，不是逐字替换，所以「头发」不会变成「頭發」。

  2. 生成 data/i18n.js —— 一张「繁体字 → 简体字」的对照表，
     只收 index.html 里真正出现过的字（几百个，几 KB）。
     网页切到简体模式时，靠它把界面文字换掉。

为什么界面不用 OpenCC 在浏览器里转：
  浏览器里没有词典，逐字替换会出错（发/髮、后/後）。
  而界面文字是我们自己写的，字集有限，预先算好一张表最稳。

跑法：
    python localize.py
"""

import json
import os
import sys

import fsutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "vendor"))
os.chdir(HERE)

import opencc

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA = os.path.join(HERE, "data")
# s2tw = 简体 → 台湾正体（只换字形和地区用字，不换词汇）
# 用它而不是 s2t，是因为 s2t 会把「账号」写成「賬號」，台湾一般写「帳號」
S2T = opencc.OpenCC("s2tw")
T2S = opencc.OpenCC("t2s")


def is_han(ch):
    return "\u4e00" <= ch <= "\u9fff"


def build_title_t():
    path = os.path.join(DATA, "posts.json")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)

    posts = doc.get("posts", [])
    changed = 0
    for p in posts:
        t = p.get("title") or ""
        tt = S2T.convert(t)
        if tt != t:
            changed += 1
        p["title_t"] = tt

    fsutil.write_json(path, doc)

    print("标题：%d 条，其中 %d 条转成繁体后有变化" % (len(posts), changed))
    return posts


def build_i18n_map():
    """扫描 index.html 和 method.html，把出现过的繁体字转成简体，做成对照表。"""
    pages = ["index.html", "method.html"]
    src = ""
    for name in pages:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                src += f.read()

    chars = set(ch for ch in src if is_han(ch))
    mapping = {}
    for ch in sorted(chars):
        s = T2S.convert(ch)
        if s != ch and len(s) == 1:
            mapping[ch] = s

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "i18n.js")
    fsutil.write_text(
        out,
        "/* 由 localize.py 自动生成，不要手改 */\n"
        "window.FISH_I18N = "
        + json.dumps({"t2s": mapping}, ensure_ascii=False, separators=(",", ":")) + ";\n")

    print("界面字表：index.html + method.html 里 %d 个汉字，其中 %d 个繁简不同 → i18n.js %.1f KB"
          % (len(chars), len(mapping), os.path.getsize(out) / 1024.0))
    return mapping


def main():
    posts = build_title_t()
    build_i18n_map()

    # 抽几条看看转换质量，别全信我
    print("\n抽样（简体 → 繁体）：")
    n = 0
    for p in posts:
        if p.get("title_t") and p["title_t"] != p["title"]:
            print("  %-34s → %s" % (p["title"][:34], p["title_t"][:34]))
            n += 1
            if n >= 6:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
