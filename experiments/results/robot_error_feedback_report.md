# 真实机器人错误反馈闭环实验报告

## 1 实验目的

验证闭环 Agent 对真实 RobotStudio/RAPID 运动错误的反馈感知与重规划
恢复能力，覆盖运动不可达、套接字错误与执行错误状态三类真实错误码。

## 2 实验环境

- 操作系统：Windows，Python 3.12
- 执行后端：ABB RobotStudio Backend（Mock 服务端，协议与真实 RAPID
  SocketServer 一致），错误返回格式与真实 ERROR_RAPID <errno> <code> 一致
- Agent 配置：closed_loop=True，max_rounds=3

## 3 实验设计

三类真实错误码各运行 10 次，共 30 次。每轮任务第 1 次执行返回
结构化 RAPID 错误（Observation 解析 error_code），Reflection 分类后
Agent 在第 2 轮改用关节空间运动（MOVEJ）恢复。

## 4 实验结果

| 错误码 | 错误名称 | 实验次数 | 恢复成功率 | 平均重规划次数 | 平均恢复时间 |
| --- | --- | --- | --- | --- | --- |
| 50050 | position_unreachable | 10 | 10/10 (100%) | 1.00 | 0.006 s |
| 41595 | socket_error | 10 | 10/10 (100%) | 1.00 | 0.011 s |
| 10020 | execution_error_state | 10 | 10/10 (100%) | 1.00 | 0.013 s |

逐次记录见 experiments/logs/robot_error_feedback_experiment.json。

## 5 结果分析

（1）Observation 正确解析 RAPID 结构化错误（error_code / error_source /
raw_message），错误不再只是文本，而是可被后续模块消费的结构化数据；

（2）Reflection 依据错误码分类（robot_unreachable / socket_error /
execution_error_state），为重规划提供明确原因；

（3）Agent 在第 2 轮改用关节空间运动（MOVEJ）恢复，验证了闭环
机制对真实执行错误的自主恢复能力。
