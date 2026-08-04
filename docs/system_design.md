# 系统设计说明

## 1. 功能介绍

系统采用**分层 + 双运行栈**设计：

- **Windows 栈（V1/V2）**：`main.py` 直接串联 LLM 规划与 SimRobot 世界模型，不依赖 ROS2
- **WSL 栈（V3/V4+）**：ROS2 节点 + Gazebo 仿真，AI 大脑作为 ROS2 节点运行
- **共享核心**：`llm.py`（DeepSeek/Mock 规划器）、`memory.py`（SQLite 记忆）、
  `robot.py`（SimRobot 世界模型）在两侧原样复用

## 2. 技术选择原因

### 双运行栈

- V1/V2 用纯 Python 快速验证"LLM → JSON 动作 → 世界模型"闭环
- V3 起引入 ROS2，验证"AI 大脑作为机器人系统一个节点"的真实工业架构
- 核心模块接口一致（`plan_task` / `execute` / `remember`），替换执行层不破坏上层

### JSON 动作契约

- 自然语言是模糊的，机器只能执行确定的结构化指令
- JSON 作为"人和机器之间的翻译契约"，与真实机器人系统的消息格式（ROS2 msg）对应

### SQLite 记忆

- 轻量嵌入式数据库，单文件持久化，Python 内置 sqlite3，无需安装服务
- 记忆分类（环境信息/物体信息/用户知识），查询用 LIKE 模糊匹配

## 3. 数据流程

### Windows 栈（V1/V2）

```
用户输入 → 记忆查询 → 记忆 + 任务 → DeepSeek → JSON 动作 → SimRobot 执行
```

### ROS2 栈（V3/V4）

```
task_cli --发布--> /ai_robot/task --> ai_brain（记忆 + DeepSeek 规划）
ai_brain --发布--> /ai_robot/action --> robot_controller（世界模型 + 导航）
robot_controller --发布--> /ai_robot/status --> 反馈
Gazebo 相机 --/camera/image_raw--> vision_node（OpenCV 颜色识别）--> SQLite + /ai_robot/vision
```

### V5.2 Agent 栈（当前主链路）

```
GUI 对话 --> Agent --> RAG 检索 --> DeepSeek Plan --> 工具 --> /ai_robot/action
          --> robot_controller --> Gazebo --> /ai_robot/status --> GUI 展示
```

## 4. 当前实现状态

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| LLM 规划 | ✅ | DeepSeek 真实模式 + Mock 离线模式自动切换 |
| Memory | ✅ | SQLite 三类记忆，跨会话持久化 |
| ROS2 通信 | ✅ | 4 个节点 + 4 个话题，launch 一键启动 |
| Gazebo 仿真 | ✅ | 差速机器人 + 相机 + 3 零件 + 物理导航 |
| GUI | ✅ | Streamlit 5 标签页，中英文配置分离 |
| Agent | ✅ | 可解释 Plan + 四工具 + 指代消解 |
| RAG | 🚧 | 基础模块完成，Agent/GUI 集成进行中 |

## 5. 未来扩展方向

- Agent 与 RAG 完整集成（planner 上下文注入语义记忆）
- 任务队列与多步动作序列化执行
- 真实机器人接口（MoveIt / RobotStudio / 真实机械臂）
- 评测与日志体系（实验数据自动采集）
