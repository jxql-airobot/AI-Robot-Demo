# 实验与评测（V5.4 / V6.2）

## 目录结构

```
experiments/
├── scripts/        # V6.2 实验辅助脚本（stats.py 统计）
├── tasklog/        # V6.2 统一实验日志系统（JSON Lines）
├── tasks/          # 任务集定义（JSON：task_set / task_set_robotstudio / basic_tasks）
├── results/        # 评测结果（JSON 摘要 + CSV 汇总/明细）
├── evaluate.py     # 自动评测脚本
├── robotstudio_benchmark.py   # RobotStudio 实验基准（mock/real）
├── thesis_experiments.py      # V6.2 论文三组实验（CSV）
├── logs/           # 实验过程日志（人工整理材料）
├── figures/        # 实验图表
└── README.md
```

## 运行评测

```bash
# WSL 内（RAG 已配置）
python3 experiments/evaluate.py                # 本地模式 + 自动规划器
python3 experiments/evaluate.py --rounds 5
python3 experiments/evaluate.py --planner mock # 离线复现（不调用 DeepSeek）
python3 experiments/evaluate.py --mode ros2    # ROS2 模式（需仿真系统启动）
```

## 输出指标

- 成功率：计划匹配期望 + 所有步骤执行成功
- 响应时间：Agent.handle 总耗时
- AI 规划时间：planner.plan 耗时
- 工具执行时间：executor 耗时
- RAG 召回率：语义任务中期望记忆是否进入 top-3 检索结果

## 任务集

任务集在 `tasks/task_set.json`，每类任务含期望条件
（expected_tool / expected_action / expected_recall 等）。
新增实验任务直接在该文件中追加。

## V6.2 统一实验日志系统（experiments/tasklog/）

每次 `Agent.handle()` 执行结束自动写入一条 JSON 记录（JSON Lines）到
`experiments/results/runtime_logs.json`，Gazebo / RobotStudio / Local / Mock
统一格式：

统一字段（论文实验 schema）：

```
task_id, task_type, input, agent_enabled, rag_enabled, generated_plan,
execution_result, success, response_time, error
```

扩展字段（深入分析用）：

```
timestamp, planner_output, tool_calls, backend, planning_time, execution_time
```

`task_type` 可通过 `Agent.handle(task, task_type="basic_motion")` 传入，
用于实验分类统计；`rag_enabled` 自动取自 Agent 的 RAG 开关。

```bash
python -m experiments.tasklog.task_logger            # 查看当前日志条数
python -m experiments.tasklog.task_logger --clear   # 清空日志
```

> 注意：包名用 `tasklog` 而非 `logging`——`logging` 与 Python 标准库撞名，
> 会让从 experiments/ 目录启动的脚本无法 import。

## V6.2 论文三组实验（thesis_experiments.py）

```bash
python experiments/thesis_experiments.py --experiment 1 --rounds 5   # Agent 规划测试
python experiments/thesis_experiments.py --experiment 2 --rounds 5   # RAG vs 无RAG
python experiments/thesis_experiments.py --experiment 3 --backend robotstudio --real --rounds 5
python experiments/thesis_experiments.py --experiment 3 --backend gazebo --rounds 5  # 需 WSL ROS2
```

输出 CSV（utf-8-sig，Excel 直接打开）：

- `experiment1_planning.csv`：成功率 / 平均响应 / 规划 / 执行
- `experiment2_rag.csv`：无 RAG vs RAG 的成功率 / 召回率
- `experiment3_backend.csv`：Gazebo vs RobotStudio 执行成功率 / 执行时间

> 实验 2 的语义召回需要 RAG 模型（sentence-transformers，WSL 已配置）；
> Windows 上未安装模型时两种模式均为关键词检索。

## V6.2 日志统计（scripts/stats.py）

```bash
python experiments/scripts/stats.py                       # 总体成功率/响应/错误
python experiments/scripts/stats.py --group task_type     # 按任务类型分组
python experiments/scripts/stats.py --group backend       # 按后端分组
```

输出：任务数 / 成功率 / 平均响应时间（含规划、执行分解）/ 错误次数 / 错误 TOP。

## 基础任务集（tasks/basic_tasks.json）

10 条论文基础任务，字段：`id / name / task_type / input / expected`
（期望工具/动作/召回，可选 `seed_memory` 预置记忆），覆盖
基础运动 / 状态 / 规划 / 视觉 / 记忆(RAG) / 指代消解。

## 论文任务集（tasks/，task_001~task_205 共 16 条）

- `basic_tasks.json`：6 条基础运动/状态任务（HOME/MOVEJ/GETPOS/MOVEL/STATUS/GETPOSE）；
- `complex_tasks.json`：5 条复杂规划任务（搬运流程/扫描报告/记忆驱动/多步执行）；
- `knowledge_tasks.json`：5 条工业知识任务（RAG 问答，含预置工业知识 seed_memory）；
- 字段：`task_id / task_type / input / expected_action / expected / evaluation`
  （复杂任务另含 `expected_steps / min_steps`，知识任务含 `expected_keywords`）；
- 任务集说明见 `tasks/README.md`。

## DeepSeek 规划器实验（--planner deepseek）

`run_task_sets.py` 支持 LLM 规划器入口：

```bash
python experiments/scripts/run_task_sets.py --tasks complex --planner deepseek --backend real --rounds 3
python experiments/scripts/run_task_sets.py --tasks variant --rounds 3        # 语言泛化对比
python experiments/scripts/run_task_sets.py --tasks variant --planner deepseek --rounds 3
```

- 实验报告：`docs/thesis/results/planner_comparison_results.md`
- 对比图：`docs/thesis/images/thesis_planner_comparison.png`
- 结果：语言变体 规则 4% vs LLM 88%（平均 93%）；真实 RobotStudio 11/11 100%
