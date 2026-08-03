@echo off
chcp 65001 >nul
wsl.exe -d Ubuntu-22.04 -- bash -lc "source ~/ros2_ws/install/setup.bash && ros2 launch ai_robot demo.launch.py"
pause
