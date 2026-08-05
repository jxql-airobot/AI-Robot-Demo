# AI Robot Demo 官方启动器
# ====================================================
# 用法:
#   .\AI_Robot_Demo_Launcher.ps1            # 前台模式: 打开 4 个窗口(推荐调试)
#   .\AI_Robot_Demo_Launcher.ps1 -Background # 后台模式: 无窗口运行, 仅自动开浏览器
#
# 启动内容:
#   [1] V1/V2 AI机器人Demo (Windows Python, PYTHONUTF8=1)
#   [2] V3/V4 ROS2 + Gazebo 仿真系统
#   [3] 任务终端 (配合仿真系统使用)
#   [4] V5.x Streamlit GUI (自动打开 http://localhost:8501)

param(
    [switch]$Background
)

$base = $PSScriptRoot
if (-not $base) { $base = 'F:\AI-Projects\AI-Robot-Demo' }
$scripts = Join-Path $base 'scripts'

if ($Background) {
    Write-Host '[后台模式] 启动 ROS2 + Gazebo 与 GUI（无窗口）...'
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d', 'Ubuntu-22.04', '--',
        'bash', (Join-Path $scripts 'start_ros2_system.sh') -WindowStyle Hidden
    Start-Sleep -Seconds 12
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d', 'Ubuntu-22.04', '--',
        'bash', (Join-Path $scripts 'start_gui.sh') -WindowStyle Hidden
    Start-Sleep -Seconds 15
    try { Start-Process 'http://localhost:8501' } catch { Write-Host "自动打开浏览器失败: $_" }
    Write-Host '完成。'
    return
}

Write-Host '============================================'
Write-Host '  AI Robot Demo 全家桶启动器'
Write-Host '  ----------------------------------------'
Write-Host '  正在打开 4 个窗口:'
Write-Host '   [1] V1/V2  Windows 版演示'
Write-Host '   [2] V3/V4  ROS2 + Gazebo 仿真系统'
Write-Host '   [3] 任务终端 (配合仿真系统使用)'
Write-Host '   [4] V5.x   Streamlit GUI'
Write-Host '============================================'

$wtPath = (Get-Command wt.exe -ErrorAction SilentlyContinue).Source
if (-not $wtPath) {
    Write-Host '未找到 Windows Terminal, 回退到 cmd 启动方式。'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "$base\scripts\run_v1v2.ps1" -WorkingDirectory $base
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d', 'Ubuntu-22.04', '--',
        'bash', (Join-Path $scripts 'start_ros2_system.sh')
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d', 'Ubuntu-22.04', '--',
        'bash', (Join-Path $scripts 'start_task_cli.sh')
    Start-Process -FilePath 'wsl.exe' -ArgumentList '-d', 'Ubuntu-22.04', '--',
        'bash', (Join-Path $scripts 'start_gui.sh')
} else {
    $cmd = "new-tab --title `"V1/V2 AI机器人Demo`" powershell.exe -NoExit -ExecutionPolicy Bypass -File `"$scripts\run_v1v2.ps1`""
    $cmd += " ; new-tab --title `"ROS2 仿真系统`" wsl.exe -d Ubuntu-22.04 -- bash `"$scripts\start_ros2_system.sh`""
    $cmd += " ; new-tab --title `"任务终端`" wsl.exe -d Ubuntu-22.04 -- bash `"$scripts\start_task_cli.sh`""
    $cmd += " ; new-tab --title `"GUI`" wsl.exe -d Ubuntu-22.04 -- bash `"$scripts\start_gui.sh`""
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $wtPath
    $psi.Arguments = $cmd
    $psi.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
}

Write-Host '窗口已打开, 等待 Streamlit 启动后自动打开浏览器...'
Start-Sleep -Seconds 10
try { Start-Process 'http://localhost:8501' } catch { Write-Host "自动打开浏览器失败: $_" }
Write-Host '完成。本窗口 3 秒后自动关闭。'
Start-Sleep -Seconds 3
