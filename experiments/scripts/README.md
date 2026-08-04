# 实验脚本

本目录保存论文实验的辅助脚本：

| 脚本 | 用途 |
| --- | --- |
| `stats.py` | 读取统一实验日志（`results/runtime_logs.json`），输出成功率 / 平均响应时间 / 错误次数，可按 `task_type` / `backend` 分组 |
| `run_task_sets.py` | 论文任务集批量运行与评测（基础/复杂/知识/语言变体，支持 DeepSeek 规划器入口） |
| `generate_thesis_results.py` | 由 CSV/日志生成第五章结果表与论文图 |

```bash
python experiments/scripts/stats.py
python experiments/scripts/stats.py --group task_type
```

## DeepSeek Planner 入口（run_task_sets.py --planner deepseek）

```bash
# 基础/复杂任务：DeepSeek 规划器（mock 或真实 RobotStudio）
python experiments/scripts/run_task_sets.py --tasks complex --planner deepseek --backend mock --rounds 3
python experiments/scripts/run_task_sets.py --tasks basic --planner deepseek --backend real --rounds 3

# 语言变体：默认两种规划器对比；--planner 可只跑指定一种
python experiments/scripts/run_task_sets.py --tasks variant --rounds 3          # 规则 vs LLM 对比
python experiments/scripts/run_task_sets.py --tasks variant --planner deepseek --rounds 3  # 仅 LLM
```

说明：

- DeepSeek 规划器为实验入口实现（`DeepSeekRobotStudioPlanner`，含 RobotStudio
  动作契约工具描述 + 安全约束层），核心代码零修改；
- 输出文件按 规划器/后端 区分（`task_sets_*_deepseek[_real].csv`），不覆盖已有数据；
- 语言变体对比结果：规则规划器 4%（1/24）vs LLM 规划器 88%（21/24，平均 93%）。
