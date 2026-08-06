# 闭环 Agent 异常恢复实验报告

## 1 实验目的

验证闭环 Agent（规划-执行-观察-反思-重新规划）在工业机器人任务
执行失败情况下的异常恢复能力，包括动作参数异常、通信异常与执行
失败三类场景下的重规划成功率与恢复效率。

## 2 实验环境

- 操作系统：Windows，Python 3.12
- 后端类型：ABB RobotStudio 虚拟控制器（IRC5 + IRB120，TCP 127.0.0.1:30000，RAPID SocketServer 真实运行）
- Agent 配置：closed_loop=True，rag_enabled=False
- max_rounds：3

## 3 实验设计

三类异常各运行 10 次，共 30 次：

1. 动作参数异常（action_param）：首轮规划生成非法关节参数，
   验证 Safety 预检拒绝与重规划恢复；
2. 通信异常（communication）：后端首轮返回 socket 错误，
   验证异常捕获、Reflection 分类与重规划恢复；
3. 执行失败（execution）：后端首轮返回运动失败，验证 Observation
   反馈、Reflection 分类与重规划恢复。

## 4 实验结果

| 异常类型 | 实验次数 | 恢复成功率 | 平均重规划次数 | 平均恢复时间 |
| --- | --- | --- | --- | --- |
| action_param | 10 | 100% (10/10) | 1.00 | 0.328 s |
| communication | 10 | 100% (10/10) | 1.00 | 0.297 s |
| execution | 10 | 100% (10/10) | 1.00 | 0.300 s |

原始逐次记录见 experiments/logs/closed_loop_experiment.json。

## 5 结果分析

（1）Observation 反馈作用：执行器完成后，Observation 将后端返回的
失败信息（stage/error/message）统一为结构化观察，供后续分析；

（2）Reflection 异常分类作用：Reflection 依据观察内容把失败分类为
action_param / communication / execution，为重规划提供明确原因；

（3）Replanning 机制作用：失败原因注入下一轮规划上下文，Agent 在
新一轮生成修正后的计划并再次执行；

（4）闭环相比单轮执行的优势：单轮执行在失败即停止，闭环通过
观察反馈与异常分析实现失败情况下的自动重规划，提高任务完成率。
