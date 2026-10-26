@echo off
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
) else if not "%RC%"=="0" (
  echo   跑完了，但出了問題（代碼 %RC%）。
  echo   數據沒有被破壞，上一次的還在。詳情看上面的訊息。
) else (
  echo   完成。双击 index.html 查看结果。
)
echo ============================================
pause
exit /b %RC%
