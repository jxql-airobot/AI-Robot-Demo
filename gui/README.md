# AI Robot Agent GUI (V5.1)

Streamlit 图形界面，作为独立客户端连接 AI-Robot-Demo 的 ROS2 仿真系统。
不修改任何 V1-V4 代码，不修改任何现有 ROS2 节点。

## 运行（ROS2 模式，主模式）

在 WSL Ubuntu 终端：

```bash
cd ~
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
cd /mnt/f/AI-Projects/AI-Robot-Demo
streamlit run gui/app.py
```

浏览器打开 http://localhost:8501

先启动仿真系统（另一终端）：

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch ai_robot demo_v4.launch.py
```

## 本地模式（规划中，暂未实现）

不依赖 ROS2，直接复用 llm.py / memory.py / robot.py（V1/V2 单机版）。

## 依赖安装

```bash
# WSL 内（先锁 numpy，再装 streamlit）
pip install numpy==1.26.4
pip install streamlit
```

## 已知注意事项

- numpy 绝不能升到 2.x，否则 cv_bridge 报 `_ARRAY_API not found`
- GUI 进程必须能 import rclpy（先 source ROS2 环境）
