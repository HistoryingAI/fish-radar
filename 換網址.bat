@echo off
REM ============================================================
REM  肥鱼雷达 · 换网址
REM
REM  什么时候双击：域名买好、网站已经在新域名上打开之后。
REM
REM  它做两件事：
REM    1. 把 index.html 里的分享图地址 / canonical 改成新网址
REM       （不改的话，发到微信、B 站、Discord 都是白板）
REM    2. 提交 + 推送，等自动部署
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set "DOMAIN=%~1"
if "%DOMAIN%"=="" set "DOMAIN=https://fishradar.vip"

echo.
echo   要设定的网址：%DOMAIN%
echo.
echo   直接按 Enter 就用这个；要换别的，现在打进去再按 Enter。
set "INPUT="
set /p "INPUT=  > "
if not "%INPUT%"=="" set "DOMAIN=%INPUT%"

REM ---------- 找 Python（跟 自动更新.bat 一样的顺序） ----------
set "PY="
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopy
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 goto :nopy

REM ---------- 改 ----------
"%PY%" set_og.py "%DOMAIN%"
if errorlevel 1 goto :fail

REM ---------- 推 ----------
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT goto :nogit

"%GIT%" add index.html
"%GIT%" commit -m "og: 换成新域名 %DOMAIN%" >nul 2>&1
"%GIT%" push
if errorlevel 1 goto :pushfail

echo.
echo   完成。等 30 秒，重新整理网页，分享卡就会用新网址。
echo   最后确认一件事：打开 %DOMAIN%/og-cover.jpg
echo   看得到图 = 对了；404 = 还没部署好，再等一下。
echo.
pause
exit /b 0

:nopy
echo.
echo   [错误] 找不到能用的 Python。
echo   这台机器上的 Python 路径可能变了，把这段错误贴给 AI。
echo.
pause
exit /b 1

:fail
echo.
echo   [错误] 上面有报错，没有改成。往上翻看原因。
echo.
pause
exit /b 1

:nogit
echo.
echo   网址已经改好了，但找不到 git，所以还没推上去。
echo   手动跑这三行（在 fish-radar 文件夹里）：
echo       git add index.html
echo       git commit -m "og"
echo       git push
echo.
pause
exit /b 0

:pushfail
echo.
echo   [错误] 推送失败。最常见的原因：代理软件没开（127.0.0.1:7897）。
echo   开好代理再双击一次本文件即可（网址不会重复改）。
echo.
pause
exit /b 2
