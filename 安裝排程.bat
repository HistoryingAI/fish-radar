@echo off
REM ============================================================
REM  安装四个每日计划任务：08:00 / 13:00 / 18:00 / 23:00
REM
REM  双击一次就行。装完可以随时删：双击 移除排程.bat
REM
REM  2026-10-27 改：改用 PowerShell 注册，因为 schtasks 没法设
REM  「错过补跑」和「睡眠唤醒」——电脑一睡，早上 8 点那轮就永远不跑。
REM
REM  注意：
REM    · 任务只在"你登录着"的时候跑；睡眠中会尝试唤醒，
REM      关机期间错过的那次会在下次开机后补跑一次。
REM    · 跑的时候会弹一个黑窗口，几分钟，别关它（关掉 = Ctrl+C，这一轮白跑）。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

if not exist "自動更新.bat" (
  echo [错误] 找不到 自動更新.bat，请确认它和本文件在同一个文件夹。
  pause
  exit /b 1
)
if not exist "_排程.ps1" (
  echo [错误] 找不到 _排程.ps1，请确认它和本文件在同一个文件夹。
  pause
  exit /b 1
)

echo.
echo 即将安装 4 个计划任务，指向：
echo   %~dp0自動更新.bat
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_排程.ps1"
set RC=%ERRORLEVEL%

echo.
if not "%RC%"=="0" (
  echo [错误] 注册失败（代码 %RC%）。
  echo 常见原因：这台机器的任务计划服务被组策略挡了。
  echo 把上面那段错误贴给 AI。
) else (
  echo ============================================
  echo   装好了。
  echo.
  echo   想马上试一次（不用等到点）：双击 自動更新.bat
  echo   想看它有没有正常跑：看 logs\update.log
  echo   想卸载：双击 移除排程.bat
) 
echo.
pause
exit /b %RC%
