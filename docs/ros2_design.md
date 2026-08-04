# ROS2 设计说明

## 1. 功能介绍

ROS2 层（`ros2_ws/src/ai_robot/`）把 AI 大脑接入机器人标准通信体系，
让"AI 规划"与"机器人控制"通过话题解耦。

## 2. 技术选择原因

- **ROS2 Humble**：机器人领域事实标准中间件，发布-订阅模型天然适合
  "大脑发指令、控制器执行、状态回传"的架构
- **Python 节点（rclpy）**：与 V1/V2 Python 代码无缝复用，开发效率高
- **话题（Topic）**：单向发布-订阅，多个节点可同时订阅同一状态，
  与系统"状态广播"需求匹配（服务/动作留作后续）
- **Launch 文件**：一条命令启动多节点，降低演示复杂度

## 3. 数据流程

### 节点与话题

| 话题 | 类型 | 方向 | 内容 |
| --- | --- | --- | --- |
| `/ai_robot/task` | String | task_cli → ai_brain | 用户自然语言任务 |
| `/ai_robot/action` | String(JSON) | ai_brain / Agent → robot_controller | 结构化动作指令 |
| `/ai_robot/status` | String | robot_controller → 各节点 | 工作台状态反馈 |
| `/ai_robot/vision` | String(JSON) | vision_node → 各节点 | 视觉识别结果 |
| `/camera/image_raw` | Image | Gazebo → vision_node | 相机原始图像 |
| `/odom` | Odometry | Gazebo → robot_controller | 里程计 |
| `/cmd_vel` | Twist | robot_controller → Gazebo | 差速驱动指令 |

### 节点职责

| 节点 | 职责 |
| --- | --- |
| `task_cli` | 任务输入终端（等待状态反馈打印完再收下一条） |
| `ai_brain` | AI 大脑：记忆查询 + DeepSeek 规划 + 发布动作 |
| `robot_controller` | 世界模型执行 + V4 物理导航（/odom → /cmd_vel） |
| `vision_node` | OpenCV HSV 颜色识别 → 写记忆 + 发布 /ai_robot/vision |
| `robot_state_publisher` | 发布 URDF 的 TF |
| `spawn_entity` | 把机器人/零件放进 Gazebo |

## 4. 当前实现状态

- `demo.launch.py`：ai_brain + robot_controller（无 Gazebo）
- `demo_v4.launch.py`：Gazebo + robot_state_publisher + 3 零件 + 三个 AI 节点
- 已实测：任务下发 → 记忆检索 → DeepSeek 规划 → 控制器执行 → 状态回传
- 容错：brain 记忆操作在数据库缺失时自动重建（`9a1fdf5`）
- 稳定：task_cli 等待状态反馈再收下一条（`f0ced60`）

## 5. 未来扩展方向

- 服务（Service）用于一问一答式查询（如模型列表）
- 动作（Action）用于长任务（导航到目标）
- 参数服务器 / 生命周期节点
- 多机器人话题命名空间
