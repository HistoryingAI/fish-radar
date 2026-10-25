@echo off
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
  echo [错误] 这个文件夹还不是 git 仓库。
  pause
  exit /b 1
)

echo.
echo ============================================
echo   第一次上传到 GitHub
echo ============================================
echo.
echo   如果弹出浏览器，登录 GitHub 并点授权。
echo   只需要授权这一次，以后 發布.bat 就不用再登了。
echo.
echo   出现 "main -^> main" 就是成功。
echo.

"%GIT%" push -u origin main
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo ============================================
  echo   推上去了。接下来去 Vercel 导入这个仓库，
  echo   步骤见 DEPLOY.md 的第 4 步。
  echo ============================================
) else (
  echo ============================================
  echo   失败了（代码 %RC%）。
  echo   把上面那段红字截图给我，我看看卡在哪。
  echo ============================================
)
echo.
pause
exit /b %RC%
