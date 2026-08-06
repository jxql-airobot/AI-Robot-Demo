#!/usr/bin/env bash
# 后台启动 ROS2 + Gazebo 仿真（供 Launcher -Background 调用）
# 用 setsid 脱离 WSL 会话，wsl.exe 退出后仿真仍保持运行。
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
source /opt/ros/humble/setup.bash
source /home/zlx06/ros2_ws/install/setup.bash
# 清理残留（[r] 正则避免匹配并杀掉脚本自身）
pkill -f 'gzserve[r]' 2>/dev/null
pkill -f 'gzclien[t]' 2>/dev/null
pkill -f 'lib/ai_robo[t]' 2>/dev/null
pkill -f 'streamlit ru[n]' 2>/dev/null
sleep 2
setsid nohup ros2 launch ai_robot demo_v4.launch.py > /tmp/launcher_sim.log 2>&1 &

