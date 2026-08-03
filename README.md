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

## GitHub 上传规范

第一次上传：

```bash
git init
git add .
git commit -m "first AI robot demo"
git branch -M main
git remote add origin 仓库地址
git push -u origin main
```

以后更新：

```bash
git add .
git commit -m "update project"
git push
```

注意：`.env`、`__pycache__/`、`.vscode/` 已被 .gitignore 排除，不会上传，避免 API Key 泄露。

V2 起，`database.db`（记忆数据库）也已加入 .gitignore。数据库是程序运行时自动生成的，clone 后首次运行即可创建，无需手动准备。

## 未来升级路线

1. 阶段 1：DeepSeek + Python + JSON 任务规划 ✅
2. 阶段 2：加入机器人记忆和环境信息 ✅（SQLite Memory）
3. 阶段 3：学习 ROS2 机器人通信系统
4. 阶段 4：Gazebo 机器人仿真环境
5. 阶段 5：接入真实机械臂和工业设备
