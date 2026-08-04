#!/usr/bin/env bash
# 任务终端启动脚本 (UTF-8)
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
echo "=== 任务终端 (V3/V4) ==="
ros2 run ai_robot task_cli
exec bash
