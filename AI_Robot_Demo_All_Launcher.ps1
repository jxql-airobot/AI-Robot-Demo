# AI Robot Demo 全家桶启动器 (V5.1, 4 窗口 + UTF-8)
# ====================================================
# 用 Windows Terminal 打开 4 个标签页, 全部强制 UTF-8, 解决中文乱码:
#   [1] V1/V2 AI机器人Demo (Windows Python, PYTHONUTF8=1)
#   [2] V3/V4 ROS2 + Gazebo 仿真系统 (LANG=C.UTF-8)
#   [3] 任务终端 (LANG=C.UTF-8)
#   [4] V5.1 Streamlit GUI (LANG=C.UTF-8)
# 启动后自动在默认浏览器打开 http://localhost:8501

$base = 'F:\AI-Projects\AI-Robot-Demo'
$wtPath = (Get-Command wt.exe -ErrorAction SilentlyContinue).Source

Write-Host '============================================'
Write-Host '  AI 机器人 Demo 全家桶 (V5.1)'
Write-Host '  ----------------------------------------'
Write-Host '  正在打开 4 个窗口:'
Write-Host '   [1] V1/V2  Windows 版演示'
Write-Host '   [2] V3/V4  ROS2 + Gazebo 仿真系统'
Write-Host '   [3] 任务终端 (配合仿真系统使用)'
Write-Host '   [4] V5.1   Streamlit GUI'
Write-Host '============================================'

if (-not $wtPath) {
    Write-Host '未找到 Windows Terminal, 回退到旧版 cmd 启动方式。'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动AI机器人Demo.bat" -WorkingDirectory $base
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动ROS2机器人系统.bat" -WorkingDirectory $base
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动ROS2任务终端.bat" -WorkingDirectory $base
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\启动GUI界面.bat" -WorkingDirectory $base
} else {
    # Windows Terminal 一条命令开 4 个标签页。
    # 注意: wt 会把分号当成标签分隔符, 所以复杂命令全部放进独立脚本, 这里只传脚本路径。
    $scripts = Join-Path $base 'scripts'
    $cmd = "new-tab --title `"V1/V2 AI机器人Demo`" powershell.exe -NoExit -ExecutionPolicy Bypass -File `"$scripts\run_v1v2.ps1`""
    $cmd += " ; new-tab --title `"V3/V4 ROS2仿真系统`" wsl.exe -d Ubuntu-22.04 -- bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/start_ros2_system.sh"
    $cmd += " ; new-tab --title `"任务终端`" wsl.exe -d Ubuntu-22.04 -- bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/start_task_cli.sh"
    $cmd += " ; new-tab --title `"V5.1 GUI`" wsl.exe -d Ubuntu-22.04 -- bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/start_gui.sh"

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $wtPath
    $psi.Arguments = $cmd
    $psi.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
}

Write-Host '窗口已打开, 等待 Streamlit 启动后自动打开浏览器...'
Start-Sleep -Seconds 10
try {
    Start-Process 'http://localhost:8501'
} catch {
    Write-Host "自动打开浏览器失败: $_"
}
Write-Host '完成。本窗口 3 秒后自动关闭。'
Start-Sleep -Seconds 3
