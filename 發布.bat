@echo off
REM ============================================================
REM  肥鱼雷达 · 把 data 的变化推上去
REM
REM  2026-10-27 改：
REM   · 提示文字从 Vercel 改成 Cloudflare Pages
REM   · 推送失败会换 OpenSSL 后端重试一次
REM   · 修一个坑：以前「data 没变化」就直接说「不用推」，
REM     但如果有别的提交还没推（例如改了 index.html），它会漏推。
REM     现在会再检查一次本地是不是领先于远端。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"

if not defined GIT (
  echo [错误] 找不到 git。
  echo 先装 Git for Windows，装完重新开机，再双击本文件。
  echo 下载：https://git-scm.com/download/win
  echo.
  pause
  exit /b 1
)

"%GIT%" rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [提示] 这个文件夹还不是 git 仓库。
  echo 先照 DEPLOY.md 的「一次性设定」做一遍，之后这按钮就能用了。
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   把改动推上去
echo ============================================
echo.

"%GIT%" add data/
"%GIT%" diff --cached --quiet
if errorlevel 1 (
  "%GIT%" commit -m "data: 手动更新"
) else (
  echo   data 没有变化。
)

REM 不管刚才有沒有提交，都检查一次本地是不是领先远端
"%GIT%" rev-list --count "@{u}..HEAD" > "%TEMP%\fish_ahead.txt" 2>nul
set "AHEAD="
set /p AHEAD=<"%TEMP%\fish_ahead.txt"
del "%TEMP%\fish_ahead.txt" >nul 2>&1

if "%AHEAD%"=="0" goto :nothing

echo   有 %AHEAD% 个提交要推...

"%GIT%" push
if not errorlevel 1 goto :pushed

echo.
echo   第一次推送失败，20 秒后换 OpenSSL 后端再试一次...
timeout /t 20 /nobreak >nul
"%GIT%" -c http.sslBackend=openssl push
if not errorlevel 1 goto :pushed_ssl

echo.
echo [错误] 推送两次都失败（代码 %ERRORLEVEL%）。
echo   最常见的原因：代理软件没开（127.0.0.1:7897）。
echo   开好代理再双击一次本文件即可，提交不会重复。
echo.
pause
exit /b 2

:pushed
echo.
echo   推上去了。等 30 秒 Cloudflare 自动部署，然后按 Ctrl+F5 强制刷新网页。
echo.
pause
exit /b 0

:pushed_ssl
echo.
echo   推上去了（用了 OpenSSL 后端）。等 30 秒 Cloudflare 自动部署，然后 Ctrl+F5。
echo.
pause
exit /b 0

:nothing
echo.
echo   本地和远端一致，没有要推的东西。
echo   （如果网页看起来还是旧的，按 Ctrl+F5 强制刷新，或者是部署还没跑完。）
echo.
pause
exit /b 0
