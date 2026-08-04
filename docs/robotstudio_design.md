# RobotStudio 集成设计（V6.0）

## 1. 为什么选择 RobotStudio

- **工业级仿真**：ABB RobotStudio 是工业机器人领域事实标准仿真工具，
  验证"AI Agent 能否控制工业机器人"最有说服力
- **RAPID Socket 简单稳定**：虚拟控制器原生支持 RAPID Socket 通信，
  Python 用标准库即可控制，无需安装额外 SDK
- **本地已安装**：本机已装 RobotStudio 6.08.01（D 盘），具备联调条件

## 2. 与 Gazebo 的区别

| 维度 | Gazebo 模式 | RobotStudio 模式 |
| --- | --- | --- |
| 机器人类型 | 自建差速移动机器人（URDF） | ABB 工业机械臂（如 IRB 系列） |
| 应用场景 | 移动 + 视觉 + 导航 | 工业工位动作（MoveJ/MoveL） |
| 通信方式 | ROS2 话题 | RAPID Socket TCP |
| 动作类型 | move/pick/place/scan | move_home/joint_move/linear_move |
| 仿真目的 | 通用机器人研究 | 工业机器人控制验证 |

两种模式共用同一套 AI 决策层（Agent/Planner/RAG），仅在执行后端不同。

## 3. 系统架构

```
用户任务
  -> Streamlit GUI（机器人后端选择：Gazebo / RobotStudio）
    -> AI Agent（可解释 Plan + RAG 记忆）
      -> RobotTool（工具接口）
        -> RobotStudioBackend（执行适配层）
          -> RobotStudioClient（TCP）
            -> MockRobotStudioServer 或 真实虚拟控制器（RAPID SocketServer）
  <- 执行结果（OK/ERROR + 关节位置）
```

AI 决策层与机器人执行层完全分离：Agent 不直接接触 RobotStudio 代码。

### 3.1 为什么采用 Backend 插件架构，而不是独立 RobotStudio Agent

本项目采用 **RobotTool 多后端（Backend 插件）架构**，而非为 RobotStudio
单独实现一个 Agent 子类，原因如下：

1. **单一决策层**：Agent 只有一套规划 / 记忆 / RAG / 上下文逻辑。
   执行差异全部收敛到 backend 层（`execute(action)` / `get_state()`），
   不复制 Agent 核心逻辑
2. **可插拔扩展**：新增执行后端只需实现同接口——
   GazeboBackend / LocalBackend / RobotStudioBackend 结构一致，
   未来真实 ABB 机器人、PLC 同样适用
3. **避免维护两套大脑**：独立 RobotStudio Agent 会复制记忆/RAG/Plan 流程，
   任何 Agent 能力升级都要改两处，容易漂移
4. **与项目定位一致**：RobotStudio 只是"工业机器人智能体执行平台"的执行
   后端之一，不是独立系统

> 说明：开发过程中曾存在一套并行实现（`robotstudio/robotstudio_agent.py`
> 独立 Agent 子类 + 独立 `gui/robotstudio_backend.py`），其引用了不存在的
> `RobotStudioStatusBackend`，且与 Backend 插件设计重复，已在
> `refactor(robotstudio)` 提交中移除；测试支撑文件迁移至 `tests/`。

## 4. 通信方式（RAPID Socket TCP）

### 原理

RobotStudio 虚拟控制器内运行 RAPID SocketServer 程序：

```rapid
SocketCreate / SocketBind("0.0.0.0", 30000) / SocketListen / SocketAccept
```

Python 通过 TCP 发送文本命令，RAPID 解析后执行 MoveAbsJ/MoveL 并回发结果。

### 协议

```
客户端 -> HOME\n | MOVEJ j1,...,j6\n | MOVEL x,y,z,rx,ry,rz\n | GETPOS\n
服务端 <- OK j1,...,j6\n | ERROR <message>\n
```

### 为什么不用 PC SDK

PC SDK 需要 .NET Framework + pythonnet + ABB 环境配置，复杂度高；
第一阶段只需简单动作控制，RAPID Socket 完全够用。
PC SDK 留到真实机器人阶段（需要信号 I/O、RAPID 注入等高级能力时）。

## 5. 实验结果（Mock 模式，第一阶段）

运行：`python agent/test_robotstudio_tool.py`（Mock，无 RobotStudio）

| 任务 | 结果 |
| --- | --- |
| 回到Home位置 | ✅ 执行 move_home，关节归零 |
| 移动到指定点 | ✅ 执行 MOVEJ，关节更新 |
| 简单搬运动作 | ✅ 多步骤（MOVEJ + HOME）全部成功 |
| 关节状态查询 | ✅ 返回 6 轴关节角度 |

真实 RobotStudio 联调实验（第二阶段完成 RobotWare 安装后补充）：

| 任务 | 成功率 | 平均响应时间 | 执行时间 | 失败原因 |
| --- | --- | --- | --- | --- |
| Home 移动 | | | | |
| 指定点移动 | | | | |
| 简单搬运动作 | | | | |

## 6. 未来工业机器人扩展路线

```
V6    ABB RobotStudio 虚拟工业机器人（当前）
V7    真实 ABB 机器人（PC SDK / RWS）
V8    PLC 通信（Modbus/OPC UA）
V9    工业 AI 助手（视觉 + 质量检测 + 任务编排）

最终目标：AI Agent -> 工业设备 -> 智能制造场景
```

接口设计保证后端可插拔：新增后端只需实现
`execute(action)` / `get_state()`（与 Local/Ros2/RobotStudio backend 同接口）。
