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

真实模式(需要 API Key)：

```bash
python main.py
```

离线演示模式(不需要 API Key，内置关键词规划器)：

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
- `退出`

## 每个文件的作用

| 文件 | 作用 |
| --- | --- |
| main.py | 程序入口：接收用户输入，串联"AI 规划 -> 机器人执行" |
| llm.py | DeepSeek 接口：设计系统提示词，把自然语言转成 JSON 动作指令；内置 MockPlanner 供离线测试 |
| robot.py | 模拟机器人：维护工作台状态，按 JSON 指令执行移动/抓取/放置/扫描 |
| requirements.txt | 依赖清单 |
| .env / .env.example | API 密钥配置 |
| .gitignore | 防止密钥和缓存文件被上传 |

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

## 未来升级路线

1. 阶段 1：DeepSeek + Python + JSON 任务规划(当前)
2. 阶段 2：加入机器人记忆和环境信息
3. 阶段 3：学习 ROS2 机器人通信系统
4. 阶段 4：Gazebo 机器人仿真环境
5. 阶段 5：接入真实机械臂和工业设备
