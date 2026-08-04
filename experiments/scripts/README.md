# 实验脚本

本目录保存论文实验的辅助脚本：

| 脚本 | 用途 |
| --- | --- |
| `stats.py` | 读取统一实验日志（`results/runtime_logs.json`），输出成功率 / 平均响应时间 / 错误次数，可按 `task_type` / `backend` 分组 |

```bash
python experiments/scripts/stats.py
python experiments/scripts/stats.py --group task_type
```
