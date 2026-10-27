@echo off
REM ============================================================
REM  肥鱼雷达 · 自动更新（给计划任务调用的，不用手动双击）
REM
REM  做三件事：
REM    1. 抓数据（collect.py）
REM    2. 抓成功了才提交
REM    3. 推上去，Cloudflare Pages 自动部署
REM
REM  为什么不成功就不推：宁可页面停在上一版，也不要上线一份
REM  "被 412 拦了一半"的数据。失败了下一轮会补。
REM
REM  2026-10-27 改：推送失败会换 OpenSSL 后端再试一次。
REM  原因：计划任务里有时候会报
REM    schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS
REM  那是 Windows 的 TLS 库在这个上下文拿不到凭据，换成 Git 自带的
REM  OpenSSL 后端就能绕过去（实测能过 TLS，只差账号验证）。
REM
REM  日志：logs\update.log
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

if not exist logs mkdir logs
set "LOG=logs\update.log"

echo. >> "%LOG%"
echo ---------- %date% %time% 开始 ---------- >> "%LOG%"

REM ---------- 找 Python ----------
REM 顺序：先找确定能用的那份，最后才退回 PATH。
REM 教训（2026-10-26）：以前把 where python 放第一，抓到的是微软商店的
REM python.exe 别名，一跑就 9009，排程连跑两次全是"采集退出码 9009"。
set "PY="
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [错误] 找不到 Python >> "%LOG%"
  exit /b 1
)

REM 真的能跑起来才算数（商店别名在这里会被挡下）
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo [错误] Python 跑不起来（可能是商店别名）：%PY% >> "%LOG%"
  exit /b 1
)

REM ---------- 抓 ----------
"%PY%" collect.py --chunk 20 --chunk-pause 90 >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo [%date% %time%] 采集退出码 %RC%，本轮不推送 >> "%LOG%"
  exit /b %RC%
)

REM ---------- 找 Git ----------
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT (
  echo [错误] 找不到 git >> "%LOG%"
  exit /b 1
)

REM ---------- 提交 ----------
"%GIT%" add data/ >> "%LOG%" 2>&1
"%GIT%" diff --cached --quiet
if not errorlevel 1 goto :nochange

"%GIT%" commit -m "data: 自动更新 %date%" >> "%LOG%" 2>&1

REM ---------- 推（失败换 OpenSSL 后端再试一次）----------
"%GIT%" push >> "%LOG%" 2>&1
if not errorlevel 1 goto :pushed

echo [%date% %time%] 第一次推送失败，20 秒后换 OpenSSL 后端重试 >> "%LOG%"
timeout /t 20 /nobreak >nul
"%GIT%" -c http.sslBackend=openssl push >> "%LOG%" 2>&1
if not errorlevel 1 goto :pushed_ssl

echo [%date% %time%] 推送两次都失败，数据留在本机，下一轮会再试 >> "%LOG%"
exit /b 2

:pushed
echo [%date% %time%] 已推送，Cloudflare Pages 30 秒后部署 >> "%LOG%"
exit /b 0

:pushed_ssl
echo [%date% %time%] 已推送（用了 OpenSSL 后端）>> "%LOG%"
exit /b 0

:nochange
echo [%date% %time%] 数据没有变化，不提交 >> "%LOG%"
exit /b 0
