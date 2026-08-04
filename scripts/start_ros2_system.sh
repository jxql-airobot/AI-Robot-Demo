#!/usr/bin/env bash
# V3/V4 ROS2 + Gazebo 仿真系统启动脚本 (UTF-8)
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
echo "=== ROS2 + Gazebo 仿真系统 (V3/V4) ==="
ros2 launch ai_robot demo_v4.launch.py
exec bash
