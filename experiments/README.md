# 实验与评测（V5.4）

## 目录结构

```
experiments/
├── tasks/          # 任务集定义（JSON）
├── results/        # 评测结果（JSON 摘要 + CSV 汇总/明细）
├── evaluate.py     # 自动评测脚本
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
