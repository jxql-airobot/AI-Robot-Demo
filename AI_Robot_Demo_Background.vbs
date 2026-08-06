' 后台启动 AI Robot Demo：ROS2 + Gazebo 仿真 + Streamlit GUI，隐藏运行。
' 双击本文件或通过快捷方式调用（wscript.exe）。
' 启动逻辑在 scripts/launcher_background_*.sh 中（setsid 保持后台进程）。

Set ws = CreateObject("WScript.Shell")

' 1) ROS2 + Gazebo 仿真系统（隐藏后台）
ws.Run "wsl.exe -d Ubuntu-22.04 -e bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/launcher_background_sim.sh", 0, False

' 2) 等待仿真启动
WScript.Sleep 12000

' 3) Streamlit GUI（隐藏后台）
ws.Run "wsl.exe -d Ubuntu-22.04 -e bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/launcher_background_gui.sh", 0, False

' 4) 等待 GUI，然后打开浏览器
WScript.Sleep 15000
ws.Run "http://localhost:8501", 1, False

