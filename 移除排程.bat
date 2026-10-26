@echo off
chcp 65001 >nul
echo.
echo 正在移除 4 个计划任务...
echo.

schtasks /Delete /TN "FishRadar-0800" /F
schtasks /Delete /TN "FishRadar-1300" /F
schtasks /Delete /TN "FishRadar-1800" /F
schtasks /Delete /TN "FishRadar-2300" /F

echo.
echo 完成。之后不会再自动跑了，数据要手动双击 更新數據.bat。
echo.
pause
