# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 首屏拆分
====================

做一件事：把 data/posts.json 拆成两个文件。

    data/posts_top.js    首屏要用的 30 条（约 40KB，同步加载）
    data/posts_rest.js   其余全部（异步加载，画完首屏再补）

为什么要拆：现在 311 条一次性 256KB，浏览器要等这 256KB 下完才画第一屏。
两百条的时候没感觉，两千条的时候就是「打开白屏三秒」。

首屏那 30 条不是随便挑的，是按「默认视图」挑的——
也就是你打开页面、什么都不点，看到的头 30 条。
这样首屏画出来和加载完之后的头 30 条完全一致，不会跳。

只读本地文件，不联网。跑法：
    python split_posts.py
"""

import json
import os
import sys

import fsutil
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TOP_N = 30
WINDOW_DAYS = 7


def load_config():
    try:
        with open(os.path.join(HERE, "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build(top_n=TOP_N, window_days=WINDOW_DAYS, quiet=False):
    """读 posts.json，写出 posts_top.js / posts_rest.js。返回统计 dict。"""
    src = os.path.join(DATA, "posts.json")
    if not os.path.exists(src):
        raise FileNotFoundError("找不到 data/posts.json，先跑一次 collect.py")

    with open(src, "r", encoding="utf-8") as f:
        doc = json.load(f)

    meta = doc.get("meta", {})
    posts = doc.get("posts", [])

    # 公開版可以整批屏蔽平台（config.json 的 hide_platforms）。
    # 典型用法：上線前把 github 加進去——大陸多數人打不開，留著只是一排死鏈。
    # 只影響「寫給網頁的檔案」，posts.json 這份抓取緩存不動，本地照樣能看全量。
    hidden = [str(x) for x in (load_config().get("hide_platforms") or [])]
    if hidden:
        posts = [p for p in posts if p.get("platform") not in hidden]

    # 默认视图 = 近 7 天 + 全部相关度，按热度降序
    cutoff = time.time() - window_days * 86400

    def in_default_view(p):
        ts = p.get("published_ts") or 0
        return (not ts) or ts >= cutoff

    pool = [p for p in posts if in_default_view(p)]
    pool.sort(key=lambda p: (-(p.get("heat") or 0), -(p.get("published_ts") or 0)))

    top = pool[:top_n]
    top_ids = {p.get("id") for p in top}
    rest = [p for p in posts if p.get("id") not in top_ids]

    # meta 里带上全量统计，这样首屏的统计卡一上来就是对的数字
    meta_out = dict(meta)
    meta_out["split"] = {
        "top": len(top),
        "rest": len(rest),
        "total": len(posts),
        "window_days": window_days,
    }
    if hidden:
        meta_out["hidden_platforms"] = hidden

    def dump(path, varname, payload):
        fsutil.write_text(
            path,
            "/* 由 split_posts.py 自动生成，不要手改 */\n"
            "window.%s = " % varname + json.dumps(payload, ensure_ascii=False) + ";\n")
        return os.path.getsize(path)

    n1 = dump(os.path.join(DATA, "posts_top.js"), "FISH_RADAR_TOP",
              {"meta": meta_out, "posts": top})
    n2 = dump(os.path.join(DATA, "posts_rest.js"), "FISH_RADAR_REST",
              {"posts": rest})

    # 方法頁頂部那五個數字：跟最終的 posts.json 一起算，所以永遠不會過期。
    stats = {
        "total": len(posts),
        "bilibili": sum(1 for p in posts if p.get("platform") == "bilibili"),
        "github": sum(1 for p in posts if p.get("platform") == "github"),
        "strong": sum(1 for p in posts if p.get("match") == "strong"),
        "weak": sum(1 for p in posts if p.get("match") == "weak"),
        "classic": sum(1 for p in posts if p.get("classic")),
        "window_days": meta.get("window_days") or window_days,
    }
    fsutil.write_text(
        os.path.join(DATA, "stats.js"),
        "/* 由 split_posts.py 自动生成，不要手改（method.html 的數字條用） */\n"
        "window.FISH_STATS = " + json.dumps(stats, ensure_ascii=False, separators=(",", ":")) + ";\n")

    info = {"total": len(posts), "top": len(top), "rest": len(rest),
            "top_kb": n1 / 1024.0, "rest_kb": n2 / 1024.0,
            "ratio": 100.0 * n1 / max(1, n1 + n2)}

    if not quiet:
        print("总数 %d 条" % info["total"])
        print("  首屏 %-3d 条 → posts_top.js   %6.1f KB" % (info["top"], info["top_kb"]))
        print("  其余 %-3d 条 → posts_rest.js  %6.1f KB" % (info["rest"], info["rest_kb"]))
        print("  首屏占比 %.0f%%" % info["ratio"])
    return info


def main():
    try:
        build()
    except FileNotFoundError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
