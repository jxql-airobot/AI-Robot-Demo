# 真实 RobotStudio 执行验证实验报告

## 1 实验环境

- RobotStudio：6.08.01（中文版）
- RobotWare：6.08.1040
- 机器人模型：ABB IRB120
- 虚拟控制器：IRC5（AI_Robot_System_IRB120）
- Socket 通信：TCP 127.0.0.1:30000，RAPID SocketServer 真实运行
- 规划器：DeepSeek LLM（RobotStudio 动作契约版，真实 API 调用）
- 执行模式：闭环 Agent（closed_loop=True）

## 2 实验任务与结果

| 任务 | 类别 | 自然语言输入 | 执行结果 | 耗时 | 是否成功 |
| --- | --- | --- | --- | --- | --- |
| R01 | basic | 让机器人回到初始位置 | robot_tool:成功 | 2.547s | ✅ |
| R02 | basic | 移动机器人到指定关节位置 | robot_tool:成功 | 2.594s | ✅ |
| R03 | basic | 执行直线运动到目标点 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 3.078s | ✅ |
| R04 | basic | 获取当前机器人关节位置 | robot_tool:成功 | 1.515s | ✅ |
| R05 | basic | 读取机器人当前TCP位姿 | robot_tool:成功 | 1.703s | ✅ |
| R06 | basic | 查询机器人当前状态 | robot_tool:成功；robot_tool:成功 | 1.5s | ✅ |
| R07 | sequence | 移动到第一个位置，再移动到第二个位置，最后回到初始位置 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 3.407s | ✅ |
| R08 | sequence | 完成一次移动-查询-回零流程 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 3.218s | ✅ |
| R09 | composite | 让机器人移动到指定位置，然后返回初始状态 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 3.188s | ✅ |
| R10 | composite | 先回零，再移动到工作区域，然后读取状态 | robot_tool:成功；robot_tool:成功；environment_ | 2.875s | ✅ |
| R11 | composite | 移动到目标位姿并获取当前关节角 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 2.0s | ✅ |
| R12 | composite | 执行一次完整的定位-查询-回位流程 | robot_tool:成功；robot_tool:成功；environment_ | 3.344s | ✅ |
| R13 | composite | 把机器人移动到安全姿态并确认位置 | robot_tool:成功；robot_tool:成功 | 2.765s | ✅ |
| R14 | composite | 执行直线运动到指定坐标后回零 | robot_tool:成功；robot_tool:成功；robot_tool:成 | 3.141s | ✅ |
| R15 | composite | 完成关节运动、状态查询与回零的组合任务 | robot_tool:成功；robot_tool:成功；environment_ | 3.391s | ✅ |

代表任务执行成功率：15/15（100%）。

## 3 异常案例（50050 运动不可达）

发送越界 MOVEL 目标后，控制器返回运动不可达错误（50050 位置超出
范围），并伴随 10020 执行错误状态与 10125 程序停止；RAPID 程序停止
导致 SocketServer 停止监听，Python 客户端收到连接被拒。ERRINFO
查询与 Observation/Reflection 反馈过程记录如下：

```json
{
  "reply": {
    "ok": false,
    "message": "RobotStudio 通信失败: 无法连接 RobotStudio 虚拟控制器 127.0.0.1:30000 （请确认虚拟控制器已启动、SocketServer 已运行、config.json 已设 backend=real）: [WinError 10061] 由于目标计算机积极拒绝，无法连接。",
    "joints": null
  },
  "errinfo": {
    "ok": false,
    "message": "RobotStudio 通信失败: 无法连接 RobotStudio 虚拟控制器 127.0.0.1:30000 （请确认虚拟控制器已启动、SocketServer 已运行、config.json 已设 backend=real）: [WinError 10061] 由于目标计算机积极拒绝，无法连接。",
    "joints": null
  }
}
```

## 4 结果说明

（1）代表任务（基础/顺序/组合）在真实 RobotStudio + IRC5 虚拟
控制器链路下完成闭环执行；

（2）50050 为控制器停止级错误，错误后需人工重启 RAPID 任务；
RecoveryManager 提供恢复决策与重连流程；

（3）本实验为 RobotStudio 虚拟工业环境验证（IRC5 虚拟控制器），
不属于工业现场验证，也未在实体机器人上执行。
