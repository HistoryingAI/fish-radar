@echo off
REM ============================================================
REM  安装四个每日计划任务：08:00 / 13:00 / 18:00 / 23:00
REM
REM  双击一次就行。装完可以随时删：双击 移除排程.bat
REM
REM  注意：
REM    · 任务只在"你登录着"的时候跑（默认），睡眠时错过的那次不补，
REM      但一天有四次，影响不大。
REM    · 跑的时候会弹一个黑窗口，几秒到几分钟，别关它。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set "SCRIPT=%~dp0自動更新.bat"

if not exist "%SCRIPT%" (
  echo [错误] 找不到 自動更新.bat，请确认它和本文件在同一个文件夹。
  pause
  exit /b 1
)

echo.
echo 即将安装 4 个计划任务，指向：
echo   %SCRIPT%
echo.

schtasks /Create /TN "FishRadar-0800" /TR "%SCRIPT%" /SC DAILY /ST 08:00 /F
schtasks /Create /TN "FishRadar-1300" /TR "%SCRIPT%" /SC DAILY /ST 13:00 /F
schtasks /Create /TN "FishRadar-1800" /TR "%SCRIPT%" /SC DAILY /ST 18:00 /F
schtasks /Create /TN "FishRadar-2300" /TR "%SCRIPT%" /SC DAILY /ST 23:00 /F

echo.
echo ============================================
echo   装好了。当前的状态：
echo ============================================
schtasks /Query /TN "FishRadar-0800" /FO LIST | findstr /C:"任务名" /C:"下次运行时间" /C:"状态"
schtasks /Query /TN "FishRadar-1300" /FO LIST | findstr /C:"任务名" /C:"下次运行时间" /C:"状态"
schtasks /Query /TN "FishRadar-1800" /FO LIST | findstr /C:"任务名" /C:"下次运行时间" /C:"状态"
schtasks /Query /TN "FishRadar-2300" /FO LIST | findstr /C:"任务名" /C:"下次运行时间" /C:"状态"

echo.
echo   想马上试一次（不用等到点）：
echo     双击 自動更新.bat
echo   想看它有没有正常跑：看 logs\update.log
echo.
pause
