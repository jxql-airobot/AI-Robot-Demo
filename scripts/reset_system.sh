#!/usr/bin/env bash
# 彻底清理并重启 AI Robot Demo 仿真（调试用，避免 wsl 参数传递问题）
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8

pkill -9 -f 'gzserve[r]' 2>/dev/null
pkill -9 -f 'gzclien[t]' 2>/dev/null
pkill -9 -f 'ros2 launch ai_robo[t]' 2>/dev/null
pkill -9 -f 'lib/ai_robo[t]' 2>/dev/null
pkill -9 -f 'streamlit ru[n]' 2>/dev/null
pkill -9 -f 'spawn_entity.py' 2>/dev/null
pkill -9 -f 'ros2 daemo[n]' 2>/dev/null
sleep 3

source /opt/ros/humble/setup.bash
source /home/$USER/ros2_ws/install/setup.bash
setsid nohup ros2 launch ai_robot demo_v4.launch.py > /tmp/launcher_sim.log 2>&1 &
echo RESET_DONE
