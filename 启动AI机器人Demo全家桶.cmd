@echo off
rem 后台启动：ROS2+Gazebo 与 GUI 全部在后台运行，不弹 cmd 窗口。
rem 需要看窗口/调试时，改用 AI_Robot_Demo_All_Launcher.ps1。
start "" wscript.exe "F:\AI-Projects\AI-Robot-Demo\AI_Robot_Demo_Background.vbs"
exit
