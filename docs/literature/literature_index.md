# 文献库索引

## 一、已有论文（12 篇，10 篇有 PDF）

| 论文 | 方向 | 优先级 | 与 AI-Robot-Demo 关系 | PDF | 笔记 |
| --- | --- | --- | --- | --- | --- |
| ReAct | 02 Robot Agent | ★★★ 核心 | Agent"推理-行动-反馈"思想直接来源 | ✅ | ✅ |
| SayCan | 02 Robot Agent | ★★★ 核心 | LLM 连机器人技能；能力约束思想对应 RobotTool/安全层 | ✅ | ✅ |
| Inner Monologue | 02 Robot Agent | ★★★ 核心 | 执行反馈再规划，对应未来 Memory/Feedback | ✅ | ✅ |
| PaLM-E | 01 LLM 规划 | ★★★ 核心 | 具身智能框架，未来"视觉语言机器人"方向 | ✅ | ✅ |
| RT-2 | 01 LLM 规划 | ★★★ 核心 | VLA 语言到动作，了解未来方向 | ✅ | ✅ |
| RAG（Lewis 2020） | 03 RAG | ★★★ 核心 | 论文 RAG 模块的理论来源 | ✅ | ✅ |
| ChatGPT for Robotics | 03 RAG | ★★ 重点 | 函数库 + 提示工程，对应动作契约设计 | ✅ | ✅ |
| 机器人软件架构映射研究 | 04 架构 | ★★ 重点 | 软件架构代际与模块化，支撑第 3 章 | ✅ | ✅ |
| 具身 AI 综述 | 05 具身智能 | ★ 背景 | 领域全景，答辩"未来方向"依据 | ✅ | ✅ |
| Foundation Models in Robotics | 05 具身智能 | ★ 背景 | LLM 任务规划定位，未来基础模型集成 | ✅ | ✅ |
| 工厂机器人任务规划 | 01 LLM 规划 | ★★★ 核心（缺全文） | 与本项目最接近的工业 LLM 规划论文 | ❌ | ⚠️ 占位 |
| ROS: The Complete Reference | 04 架构 | ★ 背景（缺全文） | ROS 背景书，论文用 Macenski [10] 即可 | ❌ | ⚠️ 占位 |

## 二、22 篇参考文献分级映射

### 核心精读（8 篇）——直接影响系统理解

| 编号 | 论文 | 对应项目 |
| --- | --- | --- |
| [15] | ReAct | Agent 模块设计 |
| [6] | SayCan | RobotTool 设计 |
| [7] | Inner Monologue | 未来 Memory/Feedback |
| [8] | PaLM-E | 未来具身智能方向 |
| [9] | RT-2 | 未来 VLA 方向 |
| [19] | RAG | 论文 RAG 模块 |
| [10] | ROS2（Macenski） | ROS2 系统设计 |
| [21] | Software Architecture in Practice | 软件工程部分 |

### 重点了解（7 篇）

| 编号 | 论文 | 目的 |
| --- | --- | --- |
| [3] | Attention is All You Need | Transformer 基础（只看结构与注意力思想） |
| [4] | A Survey of Large Language Models | LLM 发展脉络 |
| [5] | Language Models are Few-Shot Learners | GPT 少样本能力 |
| [14] | Chain-of-Thought Prompting | LLM 推理增强 |
| [16] | LLM Based Autonomous Agents 综述 | Planning / Memory / Tool use |
| [17] | Toolformer | 工具调用，对应 Agent 调 RobotTool |
| [18] | HuggingGPT | LLM 作为任务调度中心 |

### 了解即可（7 篇）

| 编号 | 论文 | 用途 |
| --- | --- | --- |
| [1] | 我国工业机器人技术现状（王田苗） | 论文绪论背景 |
| [2] | 机器人技术研究进展（谭民） | 机器人发展背景 |
| [11] | Gazebo | 了解仿真平台 |
| [12] | ABB RobotStudio | 了解 ABB 仿真环境 |
| [13] | BERT | Transformer 语言模型背景 |
| [20] | 软件工程导论 | 论文软件工程理论 |
| [22] | 设计模式 | 软件设计思想 |

## 三、阅读顺序建议

第一阶段（论文阶段）：核心 8 篇——先 ReAct、SayCan，再 RAG、ROS2、软件
架构，最后 PaLM-E、RT-2、Inner Monologue 了解方向。

第二阶段（答辩前）：重点 7 篇——LLM 综述、Agent 综述、Transformer、GPT-3、
CoT、Toolformer、HuggingGPT。

第三阶段（读研后）：背景 7 篇 + 具身智能综述 + Foundation Models。
