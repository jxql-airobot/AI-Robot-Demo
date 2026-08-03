# ai_robot (ROS2 功能包)

AI Robot Demo V3：把 V1/V2 的 AI 大脑接入 ROS2 通信系统。

## 节点

| 节点 | 作用 | 话题 |
| --- | --- | --- |
| `task_cli` | 终端输入自然语言任务 | 发布 `/ai_robot/task`，订阅 `/ai_robot/status` |
| `brain_node` | AI 大脑：记忆 + DeepSeek 规划 | 订阅 `/ai_robot/task`，发布 `/ai_robot/action` |
| `robot_controller` | 机器人控制器：世界模型执行 | 订阅 `/ai_robot/action`，发布 `/ai_robot/status` |

## 运行

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch ai_robot demo.launch.py
```

另开终端运行任务输入：

```bash
source ~/ros2_ws/install/setup.bash
ros2 run ai_robot task_cli
```
