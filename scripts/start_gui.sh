#!/usr/bin/env bash
# V5.1 Streamlit GUI 启动脚本 (UTF-8)
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
# 清理上次残留的 GUI 进程, 防止 8501 端口被占用
pkill -f streamlit 2>/dev/null
sleep 1
cd /mnt/f/AI-Projects/AI-Robot-Demo
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
echo "=== V5.1 Streamlit GUI ==="
echo "浏览器打开: http://localhost:8501"
python3 -m streamlit run gui/app.py --server.headless true --browser.gatherUsageStats=false
exec bash
