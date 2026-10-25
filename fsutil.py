# -*- coding: utf-8 -*-
"""
肥鱼雷达 · 原子写
=================

为什么需要它：以前是 open(path, "w") 直接覆盖。跑到一半断电、被 Ctrl+C、
磁盘满，留下的就是一个半截的 JSON —— 几百条数据一次全废，网页直接白屏。
定时跑之后没人看着，这个风险不能留。

改成「先写同目录的 .tmp，再 os.replace 换过去」：

  · os.replace 在同一个磁盘上是原子操作：读的人要么看到旧文件，要么看到新文件，
    不会看到「写了一半」的第三种状态
  · 中途失败只会留下一个 .tmp，原文件毫发无损
  · 顺手 fsync 一下，避免断电时数据还在系统缓存里没落盘

用法：
    import fsutil
    fsutil.write_json(path, obj)          # 缩进 1，和原来的 json.dump(indent=1) 一致
    fsutil.write_text(path, "一整段文本")  # 需要原样换行时传 newline=""
"""

import json
import os


def write_text(path, text, newline=None):
    """原子写文本。newline="" 表示不转换换行符（改 index.html 那种场合用）。"""
    tmp = path + ".tmp"
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # 原子换过去
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def write_json(path, obj, indent=1):
    """原子写 JSON。indent=None 就是不换行（网页用的 .js 当载荷时用）。"""
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=indent))
