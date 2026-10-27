@echo off
REM ============================================================
REM  肥鱼雷达 · 抓取最新数据（手动）
REM
REM  2026-10-27 改：抓到之后会问你要不要顺手推上去。
REM  原因：以前两个按钮分工是「更新數據.bat 只抓」「發布.bat 才推」，
REM  但名字看不出这层差别——抓完刷新网页发现没变化，很容易以为抓挂了。
REM  现在抓完直接问，默认推。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   肥魚雷達 - 正在抓取最新數據
echo   大約需要 3~4 分鐘，跑完再重新整理網頁
echo   （窗口停著不動是正常的，不要關掉）
echo ============================================
echo.

set "PY="
REM 顺序很重要：先找确定能用的那份。
REM 以前把 where python 放第一，结果抓到 Windows 商店的 python.exe 别名，
REM 一跑就 9009，看起来像"脚本坏了"，其实就是根本没跑起来。
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
  set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)

if not defined PY (
  echo [错误] 找不到 Python。
  echo 请到 https://www.python.org/downloads/ 下载安装，
  echo 安装时记得勾选 "Add python.exe to PATH"，然后重新双击本文件。
  echo.
  pause
  exit /b 1
)

REM 真的能跑起来才算数（商店别名在这里会被挡下）
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo [错误] Python 跑不起来：%PY%
  echo 如果你装了微软商店版的 Python，它会是个空壳别名。
  echo 到「设置 → 应用 → 高级应用设置 → 应用执行别名」里把它关掉。
  echo.
  pause
  exit /b 1
)

"%PY%" collect.py
set RC=%ERRORLEVEL%
echo.
echo ============================================
if "%RC%"=="3" (
  echo   這次沒有跑：另一個項目還在爬 B 站。
  echo   等它停了再雙擊一次，數據沒有動，不用擔心。
  echo ============================================
  pause
  exit /b 3
)
if not "%RC%"=="0" (
  echo   跑完了，但出了問題（代碼 %RC%）。
  echo   數據沒有被破壞，上一次的還在。詳情看上面的訊息。
  echo ============================================
  pause
  exit /b %RC%
)
echo   抓取完成。
echo ============================================
echo.

REM ---------- 要不要推上去 ----------
set "ANS="
set /p "ANS=  要现在推上去、让网站也更新吗？（直接 Enter = 要，打 n = 只留在本机） "
if /i "%ANS%"=="n" goto :localonly

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT goto :nogit

"%GIT%" add data/
"%GIT%" diff --cached --quiet
if not errorlevel 1 goto :nochange

"%GIT%" commit -m "data: 手动更新" >nul 2>&1
"%GIT%" push
if not errorlevel 1 goto :pushed

echo.
echo   第一次推送失败，20 秒后换 OpenSSL 后端再试一次...
timeout /t 20 /nobreak >nul
"%GIT%" -c http.sslBackend=openssl push
if not errorlevel 1 goto :pushed_ssl

echo.
echo [错误] 推送两次都失败。数据已经存在本机，没有丢。
echo   最常见的原因：代理软件没开（127.0.0.1:7897）。
echo   开好代理后，双击 推送.bat 就能补推。
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

:nochange
echo.
echo   数据没有变化，不用推。
echo.
pause
exit /b 0

:localonly
echo.
echo   好，只留在本机。要看效果就双击 index.html。
echo   要上线的时候，双击 發布.bat。
echo.
pause
exit /b 0

:nogit
echo.
echo   数据抓好了，但找不到 git，所以还没推上去。
echo   手动跑这三行（在 fish-radar 文件夹里）：
echo       git add data/
echo       git commit -m "data"
echo       git push
echo.
pause
exit /b 0
