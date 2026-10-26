@echo off
REM ============================================================
REM  肥鱼雷达 · 测速
REM
REM  双击就会从这台电脑直连（不走代理）测一遍：
REM    百度（对照） / 你的正式网址 / 旧的 Vercel 地址
REM
REM  想知道「大陆到底能不能开」，这个数字比感觉靠谱。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set "NODE="
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe" set "NODE=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
if not defined NODE where node >nul 2>nul && set "NODE=node"
if not defined NODE if exist "%ProgramFiles%\nodejs\node.exe" set "NODE=%ProgramFiles%\nodejs\node.exe"
if not defined NODE goto :nonode

"%NODE%" 測速.js %*
echo.
pause
exit /b 0

:nonode
echo.
echo   [错误] 找不到 node。
echo   把这段贴给 AI，让它帮你把 node 的路径补进来。
echo.
pause
exit /b 1
