# 实验与评测（V5.4 / V6.2）

## 目录结构

```
experiments/
├── tasklog/        # V6.2 统一实验日志系统（JSON Lines）
├── tasks/          # 任务集定义（JSON）
├── results/        # 评测结果（JSON 摘要 + CSV 汇总/明细）
├── evaluate.py     # 自动评测脚本
├── robotstudio_benchmark.py   # RobotStudio 实验基准（mock/real）
├── thesis_experiments.py      # V6.2 论文三组实验（CSV）
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

```
task_id, timestamp, user_input, planner_output, generated_plan, tool_calls,
backend, execution_steps, success, error_message,
response_time, planning_time, execution_time
```

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
