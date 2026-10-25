@echo off
chcp 65001 >nul
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo [错误] 找不到 git。
  echo 先装 Git for Windows，装完重新开机，再双击本文件。
  echo 下载：https://git-scm.com/download/win
  echo.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [提示] 这个文件夹还不是 git 仓库。
  echo 先照 DEPLOY.md 的「一次性设定」做一遍，之后这按钮就能用了。
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   把 data 的变化推上去
echo ============================================
echo.

git add data/

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "data: 自动更新"
  git push
  echo.
  echo 推上去了。等 30 秒 Vercel 会自动部署，然后刷新网页就好。
) else (
  echo 数据没有变化，不用推。
)

echo.
pause
