@echo off
chcp 65001 >nul
echo Starting AI Robot Agent GUI (Streamlit)...
echo Open http://localhost:8501 in your browser after startup.
wsl.exe -d Ubuntu-22.04 -- bash -lc "cd /mnt/f/AI-Projects/AI-Robot-Demo && source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && python3 -m streamlit run gui/app.py --server.headless true"
pause
