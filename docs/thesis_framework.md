# 毕业论文框架（基于系统实验与设计）

> 依据 docs/experiment.md（实验数据）、docs/research_introduction.md（研究介绍）
> 与各设计文档起草，供撰写论文时直接引用。

## 论文题目（建议）

**基于大语言模型的机器人智能体任务规划系统设计与实现**

## 章节框架

### 第一章 绪论

- 1.1 研究背景与意义：LLM 应用于机器人任务规划的研究背景
  （素材：research_introduction.md 第 1 节）
- 1.2 国内外研究现状：LLM 规划、Agent、RAG、机器人仿真相关研究
  （需补充文献调研）
- 1.3 主要研究内容与贡献：
  1. 可解释任务规划（任务分析/目标/执行步骤/当前状态）
  2. 工具化 Agent 架构（四工具统一接口）
  3. 轻量 RAG 语义记忆（SQLite + numpy 余弦）
  4. 分层双栈系统（Windows 验证 + WSL ROS2/Gazebo）
- 1.4 论文组织结构

### 第二章 相关技术基础

- 2.1 大语言模型与结构化输出（DeepSeek、JSON 契约、prompt 工程）
  （素材：docs/agent_design.md、learning_notes.md 1.1-1.2）
- 2.2 Agent 架构与工具调用（素材：docs/agent_design.md）
- 2.3 检索增强生成 RAG（素材：docs/rag_design.md）
- 2.4 机器人中间件 ROS2 与仿真 Gazebo（素材：docs/ros2_design.md、gazebo_design.md）

### 第三章 系统需求分析与总体设计

- 3.1 需求分析：功能需求（任务理解/记忆/规划/执行/反馈）、
  非功能需求（可解释性、可扩展性、易用性）
- 3.2 总体架构：六层架构图（用户→GUI→Agent→LLM→RAG→工具→ROS2→Gazebo）
  （素材：docs/architecture.md）
- 3.3 模块划分与数据流（素材：docs/system_design.md）

### 第四章 系统详细设计与实现

- 4.1 LLM 任务规划模块（V1/V2：llm.py、JSON 动作契约、Mock 降级）
- 4.2 记忆模块（V2：SQLite 三类记忆；V5.3：向量表 + 混合检索）
- 4.3 Agent 模块（V5.2：Planner/Executor/Context/Tools，可解释 Plan）
- 4.4 RAG 模块（V5.3：embedder/vector_store/retriever，配置化）
- 4.5 ROS2 通信模块（V3：节点与话题）
- 4.6 Gazebo 仿真模块（V4：URDF/传感器/物理导航）
- 4.7 GUI 模块（V5.1：Streamlit 五面板，语言配置化）

### 第五章 系统测试与实验

- 5.1 测试环境与任务集（素材：experiments/tasks/task_set.json）
- 5.2 评价指标定义（成功率/响应时间/AI规划时间/工具执行时间/RAG召回率，
  素材：docs/experiment.md 5.4）
- 5.3 实验结果与分析（真实数据，素材：experiments/results/ 与 experiment.md 5.2-5.3）
  - 总体成功率 100%（18/18），平均响应 2.04s
  - 语义查询 RAG 召回率 100%
  - LLM 稳定性观察：3 轮采样总体成功率 88.9%~100%，含失败样本分析
- 5.4 功能测试记录（V1-V5.3 开发过程验证，素材：experiment.md 5.1）

### 第六章 总结与展望

- 6.1 工作总结
- 6.2 不足与改进方向（真实机械臂 V6、评测扩展、视觉升级 YOLO）

## 写作素材映射

| 论文章节 | 素材来源 |
| --- | --- |
| 研究背景/创新点 | docs/research_introduction.md |
| 架构图/数据流 | docs/architecture.md |
| 系统设计 | docs/system_design.md |
| Agent 设计 | docs/agent_design.md + agent/ 源码 |
| RAG 设计 | docs/rag_design.md + agent/rag/ 源码 |
| ROS2/Gazebo | docs/ros2_design.md + docs/gazebo_design.md |
| 实验数据 | experiments/results/ + docs/experiment.md |
| 版本演进 | docs/version_history.md |

## 写作建议

- 每章先写图表再写文字（架构图、时序图、结果表格）
- 实验章节直接引用 experiments/results/ 的 CSV/JSON，保证数据可追溯
- 论文实验建议每任务 ≥5 轮取均值（LLM 存在单轮波动）
