# AI-Robot-Demo

用 DeepSeek API 作为机器人"大脑"的最小可行 Demo：用户输入自然语言任务，AI 理解任务并输出结构化 JSON 机器人动作指令，再由模拟机器人执行。

示例：

```
输入: 把红色零件移动到检测区
AI 输出: {"action": "move", "object": "红色零件", "target": "检测区"}
机器人: 移动机械臂 -> 抓取红色零件 -> 移动到检测区 -> 放置
```

## 核心思想

这个项目不是简单调用聊天机器人，而是"机器人 AI 大脑"的原型：

```
用户 -> 自然语言任务 -> 大语言模型 -> 任务理解 -> 动作规划 -> 机器人执行
```

- DeepSeek 负责理解人的意图
- JSON 负责把人的语言转换成机器可以执行的数据
- robot.py 未来会被 ROS2 机器人控制程序替代

## V2 新增功能

- **SQLite Memory**：机器人记忆系统，数据持久化保存在 `database.db`
- **Robot Knowledge Storage**：可保存环境信息、物体信息、用户知识
- **Context-aware Task Planning**：AI 结合相关记忆做任务规划

V2 工作流程：

```
用户输入 → 记忆查询 → 相关记忆 + 任务 → DeepSeek → JSON 动作 → robot.py
```

示例：

```
输入: 记住：A区域在生产线左侧
输出: 已保存: A区域 -> 生产线左侧（环境信息）

输入: 把零件送到A区域
输出: 检索到记忆 A区域 -> 生产线左侧，AI 生成 move 指令，机器人执行
```

记忆保存在 SQLite 数据库中，关掉程序再打开仍然有效。

## V3 新增功能

- **ROS2 Robot Framework**：AI 大脑以 ROS2 节点运行（WSL2 + Ubuntu 22.04 + ROS2 Humble）
- **话题通信**：节点之间用话题（topic）收发数据，取代直接函数调用
- **三个节点**：`task_cli`（任务输入）/ `ai_brain`（AI 大脑：记忆 + DeepSeek 规划）/ `robot_controller`（机器人控制器）

```
task_cli ──发布──▶ /ai_robot/task ──▶ ai_brain（记忆查询 + DeepSeek 规划）
                                              │ 发布 JSON 动作
                                              ▼
                                         /ai_robot/action
                                              │
                              robot_controller（世界模型执行）
                                              │ 发布状态
                                              ▼
                                         /ai_robot/status
```

ROS2 代码位于 `ros2_ws/src/ai_robot/`（WSL 中为 `/home/zlx06/ros2_ws/`），复用 V1/V2 的 llm.py、memory.py、robot.py。

运行（WSL Ubuntu 终端）：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch ai_robot demo.launch.py
```

另开一个终端输入任务：

```bash
source ~/ros2_ws/install/setup.bash
ros2 run ai_robot task_cli
```

## V4 新增功能

- **Gazebo 仿真世界**：带相机和差速轮的机器人 + 红/蓝/绿三个彩色零件
- **vision_node 视觉节点**：OpenCV HSV 颜色识别，把检测结果写入记忆库
- **视觉 + AI 结合**：AI 大脑规划时能查到"红色零件 -> 右侧区域（视觉识别）"这类视觉记忆
- **机器人物理移动**：move 动作会驱动机器人在 Gazebo 里转向、开往目标工位（简单的"转向-直行"导航控制）

```
Gazebo 相机 ──/camera/image_raw──▶ vision_node（OpenCV 颜色识别）
                                          │ 检测结果写入记忆
                                          ▼
                                    SQLite 记忆（物体信息）
                                          │
                              ai_brain 查询记忆 → DeepSeek 规划
```

运行（WSL Ubuntu 终端，带仿真窗口）：

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch ai_robot demo_v4.launch.py
```

另开终端输入 `红色零件在哪里`、`扫描工作台`，AI 会结合视觉记忆回答/规划。

## V5.1 新增功能

- **Streamlit GUI**：独立图形界面客户端（`gui/` 目录），不修改任何 V1-V4 代码
- 五个页面：任务对话 / 工作台状态 / 记忆查看 / 视觉感知 / 机器人状态
- ROS2 模式为主：发布 `/ai_robot/task`，订阅 `/ai_robot/status`、`/ai_robot/vision`、`/odom`
- Local 模式（直接复用 V1/V2 单机版）为后续版本规划

运行（WSL，需先启动仿真系统）：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
cd /mnt/f/AI-Projects/AI-Robot-Demo
python3 -m streamlit run gui/app.py
```

浏览器打开 http://localhost:8501

一键启动：桌面「AI机器人Demo全家桶」快捷方式（Windows Terminal 开 4 个标签页：V1/V2 演示、ROS2+Gazebo、任务终端、V5.1 GUI，全 UTF-8 无乱码）。

## 技术栈

- Python 3.12
- DeepSeek API (deepseek-chat，OpenAI 兼容接口)
- OpenAI Python SDK
- python-dotenv (读取 .env 密钥)

## 目录结构

```
AI-Robot-Demo
├── main.py           # 主程序: 交互循环 / 单次任务
├── llm.py            # 大模型接口: 自然语言 -> JSON 动作指令
├── robot.py          # 模拟机器人: 执行 JSON 动作指令
├── memory.py         # V2 记忆系统: SQLite 保存/查询记忆
├── database.db       # V2 记忆数据库(自动生成，不提交 git)
├── ros2_ws/          # V3/V4 ROS2 功能包(ai_robot: brain / controller / task_cli / vision + models)
├── README.md
├── requirements.txt
├── .env              # API 密钥(不提交到 GitHub)
├── .env.example      # 密钥模板(提交到 GitHub)
└── .gitignore
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key(真实模式)

```bash
copy .env.example .env
```

打开 `.env`，把 `DEEPSEEK_API_KEY` 换成你自己的密钥。

### 3. 运行

方式一：双击桌面上的 **AI机器人Demo** 快捷方式（最省事）。

方式二：命令行运行。

```bash
python main.py
```

程序会自动判断：`.env` 里有有效 API Key 就使用 DeepSeek 真实模式，没有就自动降级为内置离线演示模式，无需手动加参数。也可以强制离线：

```bash
python main.py --mock
```

单次任务模式：

```bash
python main.py --task "把红色零件移动到检测区"
python main.py --mock --task "把蓝色零件放到成品区"
```

## 测试示例

运行后输入以下指令试试：

- `把红色零件移动到检测区`
- `把蓝色零件放到成品区`
- `扫描工作台`
- `抓取绿色零件`
- `记住：A区域在生产线左侧`（V2 记忆）
- `把零件送到A区域`（V2 结合记忆规划）
- `红色零件在哪里`（V4 结合视觉记忆）
- `退出`

## 每个文件的作用

| 文件 | 作用 |
| --- | --- |
| main.py | 程序入口：接收用户输入，串联"AI 规划 -> 机器人执行" |
| llm.py | DeepSeek 接口：设计系统提示词，把自然语言转成 JSON 动作指令；内置 MockPlanner 供离线测试 |
| robot.py | 模拟机器人：维护工作台状态，按 JSON 指令执行移动/抓取/放置/扫描 |
| memory.py | V2 记忆系统：SQLite 保存/查询记忆，格式化后提供给 AI 作为上下文 |
| requirements.txt | 依赖清单 |
| .env / .env.example | API 密钥配置 |
| .gitignore | 防止密钥和缓存文件被上传 |
| 启动AI机器人Demo.bat | 桌面快捷方式使用的启动脚本 |

## 安全说明

`.env`（API Key）、`database.db`（记忆数据库）等敏感或自动生成的文件已被 `.gitignore` 排除，不会上传。数据库首次运行会自动创建，clone 后无需手动准备。

## 项目发展路线

| 版本 | 名称 | 内容 | 状态 |
| --- | --- | --- | --- |
| V1 | LLM任务规划 | DeepSeek + Python + JSON 任务规划 | ✅ |
| V2 | Memory记忆系统 | SQLite 记忆和环境信息 | ✅ |
| V3 | ROS2机器人通信 | 学习机器人通信系统，让 AI 大脑连接机器人控制系统 | ✅ |
| V4 | Gazebo仿真 | 建立机器人仿真环境，并加入视觉感知（OpenCV/YOLO） | ✅ |
| V5 | AI Robot Agent科研完善 | 完善 AI 机器人大脑的科研能力 | 🚧 进行中 |
| V5.1 | GUI 图形界面 | Streamlit 独立客户端（任务对话/工作台/记忆/视觉/机器人状态） | ✅ |
| V5.2 | Agent 工具调用与可解释规划 | 四工具 + Plan 展示（任务分析/目标/执行步骤/当前状态） | ✅ |
| V5.3 | RAG 语义记忆 | 向量嵌入 + 混合检索（语义为主，关键词兜底） | 🚧 进行中 |
| V6 | ABB RobotStudio/真实机器人 | 接入 ABB RobotStudio 与真实机械臂 | 规划中 |
| V7 | 工业智能制造应用 | 面向工业智能制造的落地应用 | 规划中 |
