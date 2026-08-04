# RobotStudio 实验记录（V6.0）

> 记录 AI Agent 控制 ABB RobotStudio 虚拟机器人的实验结果。
> Mock 数据已完成；真实数据在 RobotWare 安装 + 虚拟控制器联调后补充。

## 1. 实验任务

| 任务 | 自然语言指令 | 预期动作 |
| --- | --- | --- |
| 任务1：Home 移动 | 让机器人回到Home位置 | HOME（MoveAbsJ 归零） |
| 任务2：目标点移动 | 移动到指定点 | MOVEJ（关节移动） |
| 任务3：简单搬运动作 | 执行简单搬运动作 | MOVEJ + HOME（多步骤） |

## 2. 指标

- 成功率：命令执行返回 OK 的比例
- 响应时间：Agent 生成计划 + 工具调用总耗时（s）
- 执行时间：RobotStudio 端命令执行耗时（s）
- 错误原因：失败样本的 ERROR 信息

## 3. Mock 实验结果（2026-08-04）

运行：`python agent/test_robotstudio_tool.py`（本地 Mock，无 RobotStudio）

| 任务 | 成功率 | 平均响应(s) | 执行时间(s) | 错误原因 |
| --- | --- | --- | --- | --- |
| 任务1：Home 移动 | 100%（1/1） | ~0.01 | ~0.005 | 无 |
| 任务2：目标点移动 | 100%（1/1） | ~0.01 | ~0.005 | 无 |
| 任务3：简单搬运动作 | 100%（2/2 步） | ~0.01 | ~0.005 | 无 |

说明：Mock 为本地 TCP 即时响应，执行时间接近 0；真实联调后以实测为准。

## 4. 真实联调结果（待补）

RobotWare 安装并完成虚拟控制器联调后填写：

| 任务 | 成功率 | 平均响应(s) | 执行时间(s) | 错误原因 |
| --- | --- | --- | --- | --- |
| 任务1：Home 移动 | | | | |
| 任务2：目标点移动 | | | | |
| 任务3：简单搬运动作 | | | | |

### 记录方法

```bash
# 手动测试客户端（每次执行打印耗时与结果）
python robotstudio/manual_test_client.py --real

# 批量评测（Agent 链路）
python experiments/evaluate.py --mode robotstudio --rounds 5
```

## 5. 失败分析模板

| 错误信息 | 原因 | 处理 |
| --- | --- | --- |
| ERROR 未知命令 | 协议不一致 | 对比 command_schema.py 与 socket_server.mod |
| 连接超时 | 虚拟控制器未启动 | 启动 RAPID 程序 |
| ERROR MOVEJ 参数无法解析 | 参数格式错误 | 检查关节数量与数值 |
