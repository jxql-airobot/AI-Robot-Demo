' Background launcher for AI Robot Demo.
' Starts ROS2+Gazebo and the Streamlit GUI hidden in the background,
' then opens the browser. No cmd/terminal windows are shown.
' Double-click this file, or run:  wscript.exe "path\to\this.vbs"

Set ws = CreateObject("WScript.Shell")

' 1) ROS2 + Gazebo simulation system (hidden background)
ws.Run "wsl.exe -d Ubuntu-22.04 -- bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/start_ros2_system.sh", 0, False

' 2) Wait for the simulation to start
WScript.Sleep 12000

' 3) Streamlit GUI (hidden background)
ws.Run "wsl.exe -d Ubuntu-22.04 -- bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/start_gui.sh", 0, False

' 4) Wait for the GUI, then open the browser
WScript.Sleep 15000
ws.Run "http://localhost:8501", 1, False
