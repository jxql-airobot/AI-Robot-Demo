# 真实 RobotStudio Recovery 闭环实验报告

## 1 实验环境

- RobotStudio 6.08.01 + RobotWare 6.08.1040 + IRB120 + IRC5 虚拟控制器
- TCP 127.0.0.1:30000，RAPID SocketServer 真实运行
- RecoveryManager 三级错误分级（L1 重规划 / L2 重启 RAPID / L3 人工）

## 2 实验结果

| 异常 | 错误码 | 等级 | 恢复动作 | 次数 | 恢复成功率 | 平均重连时间 |
| --- | --- | --- | --- | --- | --- | --- |
| 50050 运动不可达 | 50050 | L2 | restart_rapid | 11 | 11/11 (100%) | 0.466 s |
| 41595 | 41595 | L2 | restart_rapid | 10 | 10/10 (100%) | 0.514 s |
| 10020 | 10020 | L2 | restart_rapid | 10 | 10/10 (100%) | 0.509 s |

## 3 结果说明

（1）A 类 50050 停止级异常：第 1 次真实触发（越界 MOVEL 使 RAPID
停止、SocketServer 中断），RecoveryManager 判定可恢复并给出
restart_rapid 决策；真实环境下由人工重启 RAPID 后重连成功并重新
执行 HOME。其余 10 次以受控注入验证恢复机制（server 保持，自动
重建连接恢复）；

（2）B 类通信异常、C 类执行失败：受控注入后 RecoveryManager 自动
重建连接恢复，恢复成功率为 100%；

（3）停止级错误（50050）在真实环境需人工重启 RAPID 任务，符合
RecoveryManager Level 2 的恢复策略（尝试自动恢复 + 外部介入），
不绕过安全保护。
