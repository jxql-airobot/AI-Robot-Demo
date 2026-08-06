# RWS 自动恢复真实验证报告

## 1 实验环境

- RobotStudio 6.08.01 + RobotWare 6.08.1040 + IRB120 + IRC5 虚拟控制器
- RWS: http://127.0.0.1；RAPID SocketServer TCP 127.0.0.1:30000
- 恢复流程：50050 → RWS 设置入口 → resetpp → start → 等 Socket 恢复

## 2 实验结果

- 实验轮次：10
- 任务恢复成功率：10/10（100%）

| 轮次 | 错误码 | 恢复前状态 | 恢复后状态 | 恢复耗时 | Socket 重连 | 任务成功 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 50050 | running → stopped | running | 0.235 s | 0.016 s | ✓ |
| 2 | 50050 | running → stopped | running | 0.188 s | 0.0 s | ✓ |
| 3 | 50050 | running → stopped | running | 0.235 s | 0.016 s | ✓ |
| 4 | 50050 | running → stopped | running | 0.187 s | 0.0 s | ✓ |
| 5 | 50050 | running → stopped | running | 0.218 s | 0.0 s | ✓ |
| 6 | 50050 | running → stopped | running | 0.203 s | 0.016 s | ✓ |
| 7 | 50050 | running → stopped | running | 0.203 s | 0.0 s | ✓ |
| 8 | 50050 | running → stopped | running | 0.187 s | 0.0 s | ✓ |
| 9 | 50050 | running → stopped | running | 0.235 s | 0.016 s | ✓ |
| 10 | 50050 | running → stopped | running | 0.218 s | 0.015 s | ✓ |

## 3 结论

在真实 RobotStudio-IRC5 虚拟控制器链路上，50050 停止级错误发生后，通过 RobotWebServices 自动完成错误清除、PP 重置、RAPID 启动与Socket 重连，无需人工重启 RAPID。
实验环境为虚拟控制器，结果不代表实体机器人上的行为。
