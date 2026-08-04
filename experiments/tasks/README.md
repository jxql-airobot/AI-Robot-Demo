# 论文实验任务集

面向毕业论文第五章“实验与结果分析”设计的任务集，共 16 条，分三类：

## 1. 基础运动任务（basic_tasks.json，task_001~006）

验证机器人基础执行能力：HOME / MOVEJ / GETPOS / MOVEL / STATUS / GETPOSE。

- `expected_action`：期望的 RAPID 命令；
- `expected`：供自动评测的工具/动作映射；
- 评价方式：`execution_success`（执行成功率）。

## 2. 复杂任务规划任务（complex_tasks.json，task_101~105）

验证 Agent 任务拆解能力：搬运流程 / 扫描报告 / 记忆驱动搬运 /
移动+状态读取 / 移动到工作区域。

- `expected_steps` / `min_steps`：期望子任务与最少步骤数；
- `expected_recall` + `seed_memory`：记忆驱动任务；
- 评价方式：`plan_and_execution` / `recall_and_execution` /
  `execution_success`（记录子任务数量、规划正确性、执行结果）。

## 3. 工业知识任务（knowledge_tasks.json，task_201~205）

验证 RAG 知识增强：运动指令区别 / 报警处理 / 直线运动参数 /
Socket 断开处理 / 奇点避免。

- `expected_keywords`：回答中应出现的关键词；
- `seed_memory`：预置工业知识条目（内容取自项目真实联调记录）；
- 评价方式：`answer_and_citation`（回答正确性 + 是否引用知识库）。

## 运行方式

基础/复杂任务可复用现有执行链路（`Agent(backend="robotstudio")` +
`RobotStudioMockPlanner`，mock/real 均可）；知识任务评价“回答正确性”
需要知识问答能力与 RAG 检索（后续实验脚本阶段实现，任务集先按此格式设计）。
