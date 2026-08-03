# AI Robot Demo launcher: opens V1/V2 demo, ROS2 system and task terminal
$base = 'F:\AI-Projects\AI-Robot-Demo'
Write-Host '============================================'
Write-Host '  AI 机器人 Demo 全家桶启动器'
Write-Host '  ----------------------------------------'
Write-Host '  正在打开 3 个窗口:'
Write-Host '   [1] V1/V2  Windows 版演示'
Write-Host '   [2] V3/V4  ROS2 + Gazebo 仿真系统'
Write-Host '   [3] 任务终端 (配合仿真系统使用)'
Write-Host '============================================'
Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动AI机器人Demo.bat" -WorkingDirectory $base
Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动ROS2机器人系统.bat" -WorkingDirectory $base
Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动ROS2任务终端.bat" -WorkingDirectory $base
Write-Host '全部窗口已打开, 本窗口 5 秒后自动关闭。'
Start-Sleep -Seconds 5