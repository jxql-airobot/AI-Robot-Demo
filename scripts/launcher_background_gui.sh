#!/usr/bin/env bash
# 后台启动 Streamlit GUI（供 Launcher -Background 调用）
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/../.."
source /opt/ros/humble/setup.bash
source /home/$USER/ros2_ws/install/setup.bash
pkill -f 'streamlit ru[n]' 2>/dev/null
sleep 1
setsid nohup python3 -m streamlit run gui/app.py --server.headless true --server.port 8501 > /tmp/launcher_gui.log 2>&1 &
