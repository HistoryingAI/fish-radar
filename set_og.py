# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 把 og:image 换成绝对网址
====================================

本机双击打开时，og:image 写相对路径没问题；但链接贴到微信 / B 站 / Discord，
它们的爬虫不会猜到你的域名，只会当成「没有图」，分享出去就是白板。

所以上线前跑一次：

    python set_og.py https://你的域名

它会把 index.html 里的 og:image / twitter:image 换成绝对网址，
并补一行 <link rel="canonical">。

想检查现在的状态：
    python set_og.py --check
"""

import os

import fsutil
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")


def main():
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print(__doc__)
        return 1

    html = open(INDEX, encoding="utf-8").read()

    if args[0] == "--check":
        m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        cur = m.group(1) if m else "（没有）"
        if cur.startswith("http"):
            print("og:image = %s" % cur)
            print("已经是绝对网址，可以直接上线。")
            return 0
        print("og:image = %s" % cur)
        print("还是相对路径。上线前跑一次：python set_og.py https://你的域名")
        return 0

    base = args[0].rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    if not re.match(r"^https?://[^/\s]+", base):
        print("这个域名看起来不太对：%s" % base)
        return 1

    old = html
    html = re.sub(r'(property="og:image"\s+content=")([^"]*)(")',
                  r"\g<1>%s/og-cover.jpg\g<3>" % base, html)
    html = re.sub(r'(name="twitter:image"\s+content=")([^"]*)(")',
                  r"\g<1>%s/og-cover.jpg\g<3>" % base, html)

    # canonical：告诉搜索引擎「这个页面的正式地址是这个」
    if 'rel="canonical"' in html:
        html = re.sub(r'<link rel="canonical" href="[^"]*">',
                      '<link rel="canonical" href="%s/">' % base, html)
    else:
        html = html.replace("</title>", '</title>\n<link rel="canonical" href="%s/">' % base, 1)

    if html == old:
        print("没有变化——检查一下 index.html 里的 og:image 是不是被改过。")
        return 0

    fsutil.write_text(INDEX, html, newline="")

    print("已更新 index.html")
    print("  og:image  = %s/og-cover.jpg" % base)
    print("  canonical = %s/" % base)
    print("\n别忘了确认 og-cover.jpg 真的在那个地址上能打开（不是 404）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
