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
where python >nul 2>nul && set "PY=python"
if not defined PY (
  if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
    set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
  )
)
if not defined PY (
  if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
)

if not defined PY (
  echo [错误] 找不到 Python。
  echo 请到 https://www.python.org/downloads/ 下载安装，
  echo 安装时记得勾选 "Add python.exe to PATH"，然后重新双击本文件。
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
