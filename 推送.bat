@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"

if not defined GIT (
  echo [错误] 找不到 git。
  pause
  exit /b 1
)

echo.
echo ============================================
echo   把本机所有提交推上去
echo ============================================
echo.
echo   用途：改了 index.html、DEPLOY.md 这类文件之后，
echo   由 AI 帮你提交好，你双击这个推上去。
echo   只是更新数据的话，用 發布.bat 就够了。
echo.

"%GIT%" push
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo 推上去了。Vercel 大约 30 秒后自动部署完成。
) else (
  echo 失败了（代码 %RC%）。
  echo 如果是 Connection was reset，先确认代理软件开着。
)
echo.
pause
exit /b %RC%
