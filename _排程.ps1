# 肥魚雷達 · 排程註冊（由 安裝排程.bat 呼叫，不要直接雙擊）
#
# 為什麼不用 schtasks：
#   schtasks /Create 沒有「補跑錯過的」和「喚醒電腦」這兩個開關，
#   結果就是電腦一睡，08:00 那輪永遠不跑，而且不會補。
#
# 這裡用 PowerShell 的 ScheduledTasks，能設：
#   StartWhenAvailable  錯過了（電腦關著/睡著）就在下次有機會時補跑
#   WakeToRun           睡眠中會把電腦叫醒
#   IgnoreNew           上一輪還在跑就不要疊第二個

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat  = Join-Path $root '自動更新.bat'

if (-not (Test-Path $bat)) {
    Write-Host "[错误] 找不到 自動更新.bat" -ForegroundColor Red
    exit 1
}

$times = @('08:00', '13:00', '18:00', '23:00')

$action = New-ScheduledTaskAction -Execute 'cmd.exe' `
          -Argument ('/c ""{0}""' -f $bat) -WorkingDirectory $root

$settings = New-ScheduledTaskSettingsSet `
            -StartWhenAvailable `
            -WakeToRun `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -MultipleInstances IgnoreNew
$settings.ExecutionTimeLimit = 'PT1H'

$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) `
             -LogonType Interactive -RunLevel Limited

foreach ($t in $times) {
    $name = 'FishRadar-' + ($t -replace ':', '')
    $trigger = New-ScheduledTaskTrigger -Daily -At $t
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host ("  [OK] {0}  每天 {1}（错过会补跑，睡眠会唤醒）" -f $name, $t)
}

Write-Host ''
Write-Host '当前状态：'
foreach ($t in $times) {
    $name = 'FishRadar-' + ($t -replace ':', '')
    $info = Get-ScheduledTaskInfo -TaskName $name
    Write-Host ("  {0}  下次 {1}  上次 {2}  结果 {3}" -f `
        $name.PadRight(16), $info.NextRunTime, $info.LastRunTime, $info.LastTaskResult)
}
