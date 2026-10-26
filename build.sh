#!/bin/sh
# ============================================================
# Cloudflare Pages 的建置腳本
# ============================================================
# 為什麼需要它：Pages 沒有「排除檔案」的功能（.assetsignore 是 Workers
# Static Assets 的東西，Pages 不讀），連 collect.py / config.json 都會
# 被公開下載。所以改成「只挑網頁要的檔案放進 dist/」。
#
# 在 Cloudflare 後台填：
#   Build command            bash build.sh
#   Build output directory   dist
# ============================================================

set -e

rm -rf dist
mkdir -p dist/data dist/assets

# 網頁本體
cp index.html method.html dist/
cp promos.js og-cover.jpg dist/
cp _headers dist/

# 數據：只拿網頁真的會載入的四個
# （posts.json 原始檔 680 KB 和 posts.js 都是生成物，網頁沒讀，別放出去）
cp data/i18n.js data/posts_top.js data/posts_rest.js data/stats.js dist/data/

# 圖片
cp assets/*.jpg dist/assets/ 2>/dev/null || true

echo "dist/ 準備好了："
ls -la dist
