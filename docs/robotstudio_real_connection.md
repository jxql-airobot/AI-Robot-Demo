# RobotStudio 真实联调指南（V6.1）

> 目标：AI Agent 通过 RAPID Socket TCP 控制 ABB RobotStudio 虚拟控制器内的工业机器人。
> 本文档基于 2026-08-04 在 RobotStudio 6.08 + RobotWare 6.08.1040 + IRC5 上的真实联调结果编写。

## 1. 环境要求

| 软件 | 版本 | 状态 |
| --- | --- | --- |
| RobotStudio | 6.08.01 | 已安装（中文版） |
| RobotWare | 6.08.1040 | 已安装（与 RobotStudio 匹配） |
| 机器人 | IRB 120 | 控制器类型 IRC5 |
| Python | 3.12（Windows） | 客户端使用 |

> 虚拟控制器系统名：`AI_Robot_System_IRB120`，TCP 端口 30000。

## 2. 关键前置条件：616-1 PC Interface 选项

**RAPID 的 Socket 系列指令（SocketCreate / SocketBind / SocketAccept /
SocketReceive / SocketSend）依赖控制器选项 616-1 PC Interface（Socket Messaging）。
系统没有该选项时，编译会报：**

```
选项缺失。(161): 指令 SocketCreate 需要选项 PC
```

创建系统时必须勾选：系统选项 -> **通信（Communication）-> 616-1 PC Interface**。
已有系统可在控制器上右键 -> 选项 -> 修改系统选项 添加，然后冷启动控制器。

## 3. 创建虚拟控制器步骤

1. 打开 RobotStudio 6.08；
2. 新建工作站：文件 -> 新建 -> 空工作站；
3. 添加机器人：基本 -> ABB 模型库 -> 选择 **IRB 120**（控制器类型 IRC5）；
4. 创建系统：基本 -> 机器人系统 -> 从布局创建系统：
   - 选择 **RobotWare 6.08**；
   - 系统名：`AI_Robot_System_IRB120`；
   - **选项树 -> 通信 -> 勾选 616-1 PC Interface**（关键！）；
5. 等待虚拟控制器启动，状态为运行中；
6. 保存工作站（如 `AI_Robot_IRB120.rspag`）。

## 4. 加载并启动 RAPID SocketServer

模块文件：`robotstudio/rapid/socket_server.mod`（入口例行程序 `socket_main`）。

1. 展开 控制器 -> RAPID -> `T_ROB1`，删除旧的 socket 测试模块（避免同名/符号冲突）；
2. 右键 `T_ROB1` -> 加载模块 -> 选择 `socket_server.mod`；
3. 确认“程序已加载”且无语法错误；
4. 右键模块 -> 设为已启动；
5. 打开 RAPID 编辑器，右键 `PROC socket_main` -> **PP 到例行程序** -> 启动；
6. 示教器消息：`AI Robot SocketServer listening on port 30000`。

> 注意：启动时 RobotStudio 默认找 `main`，本项目入口是 `socket_main`，
> 必须先用“PP 到例行程序”把程序指针指到 `socket_main` 再启动。

## 5. 通信架构

```
用户输入（GUI 对话框）
  -> Agent
    -> robot_tool（RobotStudioBackend）
      -> RobotStudioClient.send_action({"action": "move_home"})
        -> TCP: "HOME\n"
          -> RAPID socket_server HandleCommand
            -> MoveAbsJ / MoveL（机器人动作）
        <- TCP: "OK 0.00,0.00,0.00,0.00,0.00,0.00\n"
    -> 返回 {ok, joints, message}
```

## 6. 协议定义

```
客户端 ->  HOME | MOVEJ j1,...,j6 | MOVEL x,y,z,rx,ry,rz | GETPOS | STATUS
服务端 <-  OK j1,...,j6 | ERROR <message>
```

实测协议行为（RobotWare 6.08.1040）：

- `SocketReceive \Str` **保留**行尾 `\r\n`，服务端需自行去掉（`TrimLine`）；
- `SocketSend \Str` **不自动**补行尾，服务端需自行追加 `\0A`（LF）；
- 回复为单行文本，客户端按 `\n` 切行解析。
- `MOVEL` 参数为 TCP 位姿：`x,y,z` 单位米，`rx,ry,rz` 为欧拉角（roll/pitch/yaw，
  单位度）；RAPID 侧用 `OrientZYX(rz, ry, rx)` 转成四元数，执行真实 `MoveL`
  （速度 `v1000`，`fine` 停止点）。**注意：协议用米，RAPID `robtarget.trans`
  用毫米，服务端必须 ×1000 换算**（V6.2 已处理）。
- `MOVEL` 的 `rx,ry,rz` 全为 0 时表示**保持当前工具朝向**（服务端用 `CRobT()`
  取当前姿态，只改位置），用于纯位置直线运动，避免腕部奇异区。
- `GETPOSE` 返回当前 TCP 位姿 `x,y,z,rx,ry,rz`（x/y/z 单位米，来自
  `CRobT()` + `EulerZYX`）。
- 所有命令的 `OK` 回复携带**实测关节角**：RAPID 用 `CJointT()` 读回真值，
  不再是“最近一次命令值”。

## 7. RAPID 兼容性要点（实测踩坑记录）

| 问题 | 结论 |
| --- | --- |
| `RESUME` 指令 | RobotWare 6.08.1040 不识别（引用错误 130），错误处理用 `RETURN`/`RETRY` |
| `StrFind` | 签名是 `StrFind(String, StartPos, Charset)`，不是子串查找 |
| `StrMatch` | 子串查找用 `StrMatch(String, StartPos, Pattern)`；未找到返回非 0（按 <=0 处理） |
| `StrToVal` | 签名是 `StrToVal(Str, ValVar)`，返回 bool，不是单参函数 |
| `confdata` 聚合 | 是 **4 个分量** `[cf1,cf4,cfx,cfy]`；写成 3 个会报“记录类型集合中的组件太少” |
| `EulerZYX` 调用 | 可选参数在前：`EulerZYX(\X, rot)`；写成 `EulerZYX(rot \X)` 报“自变量过多” |
| 米/毫米单位 | 协议用米，RAPID `robtarget.trans` 用毫米，MOVEL 目标必须 ×1000（GETPOSE ÷1000） |
| `Chr()` | 不存在；字符串内控制字符用 `\0A`（LF）、`\0D`（CR） |
| `"\n"` 转义 | 不支持，必须写 `"\0A"` |
| 模块文件头 | 必须直接以 `MODULE` 开头；UTF-8 BOM 或文件头注释会导致 `(1,1) 预期值 'module'` |
| 入口命名 | 不能叫 `main`（与控制器已有全局 main 冲突），用 `socket_main` |

## 8. 错误处理（多客户端）

- 客户端断开：`SocketReceive` 报 **41595**（连接被远程主机关闭），由 `HandleClient`
  的 ERROR 段捕获后 `RETURN`；
- 复用客户端套接字：`SocketAccept` 报 **41600**（客户端套接字已在用），
  需要在每个会话结束后 `SocketClose client_socket;`；
- 等待超时：`SocketAccept` 默认 60 秒超时报 **41581**，由 `socket_main` 的
  ERROR 段 `RETRY` 继续等待，服务端不会因无人连接而停止；
- `SocketClose` 独立为 `CloseClient` 过程，关闭出错时安全返回；
- 服务端主循环：`WHILE TRUE` Accept -> 处理 -> 关闭，支持连续多客户端。

## 9. Python 测试

```bash
# Mock 闭环（无 RobotStudio 也能跑）
python robotstudio/robotstudio_real_connection_test.py

# 真实连接（需先启动 RAPID socket_main）
python robotstudio/robotstudio_real_connection_test.py --real

# 手动全流程
python robotstudio/manual_test_client.py --real
```

`config.json` 中 `backend` 可切换 `mock` / `real`：

```json
{ "host": "127.0.0.1", "port": 30000, "timeout": 5, "backend": "real" }
```

## 10. 实测结果（2026-08-04）

测试链路：Python 客户端 -> TCP 30000 -> RAPID socket_server -> IRC5 虚拟控制器 -> IRB120 运动。

### 10.1 V6.1（TCP 闭环）

| 命令 | 测试次数 | 成功率 | 平均响应时间 |
| --- | --- | --- | --- |
| GETPOS | 3 | 100% | 145 ms（首次 433 ms，稳态 ~1 ms） |
| HOME（MoveAbsJ 回零） | 3 | 100% | 46 ms |
| MOVEJ（MoveAbsJ） | 3 | 100% | 172 ms（首次 423 ms，稳态 ~46 ms） |
| STATUS | 3 | 100% | 0.9 ms |
| MOVEL（占位） | 3 | 100% | 0.8 ms |

### 10.2 V6.2（真实直线运动 + 真值回读 + 实验基准）

| 命令 | 测试次数 | 成功率 | 平均响应时间 |
| --- | --- | --- | --- |
| HOME（MoveAbsJ 回零） | 5 | 100% | ~470 ms |
| MOVEJ（MoveAbsJ，非奇异姿态） | 5 | 100% | ~650 ms |
| MOVEL（真实 MoveL，100mm） | 5 | 100% | 271 ms |
| GETPOSE（CRobT 位姿反馈） | 5 | 100% | ~1 ms |
| GETPOS/STATUS（CJointT 真值） | 5 | 100% | ~1 ms |

实测验证（2026-08-04）：

- MOVEJ [10,20,30,45,60,0] 后 GETPOSE 返回 (0.3169, 0.1006, 0.3016) m，
  与官方 DH 参数正运动学计算结果 (317, 101, 301) mm 一致；
- MOVEL 到当前位置 +0.1m（X）后 GETPOSE 返回 (0.4168, 0.1006, 0.3016) m，
  **位移 99.9mm、姿态保持不变（欧拉角变化 <0.03°）**，关节真值从
  [10,20,30,45,60,0] 变为 [7.73,37.76,3.37,40.96,67.54,5.42]——真实直线运动闭环成立；
- RobotStudio 实验基准（`experiments/robotstudio_benchmark.py --backend real --rounds 5`）：
  **8 任务 × 5 轮 = 40/40 成功率 100%，平均响应 0.539s，RAG 召回率 100%**。
  报告：`experiments/results/20260804_145535_robotstudio_report.md`。

多客户端验证：client1 连接执行 4 条命令后断开，服务端不重启，client2 再次连接
执行 4 条命令成功，关节状态跨连接保持（client2 GETPOS 正确读到 client1 的 MOVEJ 结果）。

超时存活验证：client1 执行完毕后，服务端空等 70 秒（超过 `SocketAccept`
默认 60 秒超时），client2 再次连接仍然成功执行命令，确认服务端不会因等待超时停止。

## 11. 已知限制与后续计划

- ~~`MOVEL` 占位~~：V6.2 已实现真实 `MoveL` + 位姿解析（`ParsePose` + `OrientZYX`）；
- ~~返回最近命令值~~：V6.2 起 `STATUS/GETPOS/HOME/MOVEJ/MOVEL` 均用
  `CJointT()` 读实测关节真值；
- `MOVEL` 默认保持当前朝向（rx,ry,rz=0 时），显式欧拉角也支持；
- 单端口单服务器，未做鉴权与并发连接隔离；
- 后续：真实 ABB 机器人（RobotWare + 现场网络）、PLC 通信（V7+）。

## 12. 常见错误排查

| 错误 | 可能原因 | 解决 |
| --- | --- | --- |
| 50026 靠近奇点 | 路径经过腕部/肩部奇异区（历史上还因单位错误把目标算到基座轴心附近） | 非奇异姿态起步 + `SingArea \Wrist` + 目标远离奇异区 |
| 50442 轴配置错误 | 目标点给定轴配置不可达 | `ConfL \Off` 自动选最近可行配置 |
| 50501 短距离运动 | 目标距离过短（单位错误时仅 ~0.3mm） | 检查米/毫米换算，MOVEL 目标 ×1000 |
| 161 选项缺失，SocketCreate 需要 PC | 系统缺 616-1 PC Interface | 系统选项 -> 通信 -> 勾选 616-1 |
| 41595 套接字错误 | 客户端断开 | 已由 ERROR 段处理，无需操作 |
| 41581 套接字错误 | SocketAccept 等待超时（默认 60s） | 已由 ERROR 段 RETRY 继续等待 |
| 41600 套接字错误 | 客户端套接字未关闭 | 会话结束 SocketClose（已实现） |
| 41603 套接字错误 | socket 已创建未关闭 | 重新加载模块或重置程序 |
| 语法错误(1,1) 预期值 module | BOM/文件头注释 | 文件以 MODULE 开头、无 BOM |
| Connection refused | socket_main 未启动 | 启动 RAPID 程序后再测 |
| 符号 main 未找到 | 启动入口不是 main | PP 到 socket_main 再启动 |
