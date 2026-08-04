# RobotStudio 真实联调指南（V6.0 第二阶段）

> 目标：AI Agent 通过 RAPID Socket TCP 控制 ABB RobotStudio 虚拟控制器内的
> 工业机器人。本文档在 RobotWare 安装完成后按步骤执行。

## 1. 环境要求

| 软件 | 版本 | 状态 |
| --- | --- | --- |
| RobotStudio | 6.08.01 | ✅ 已安装（D 盘） |
| RobotWare | 6.08（与 RobotStudio 匹配） | ❌ 需安装 |
| Python | 3.10（WSL）/ 3.12（Windows） | ✅ |

注意：必须安装与 RobotStudio 匹配的 RobotWare 6.08，
否则"新建工作站 -> 从布局创建系统"时下拉列表不显示虚拟控制器。

## 2. 创建虚拟控制器步骤

1. 打开 RobotStudio 6.08
2. 新建工作站：文件 -> 新建 -> 空工作站
3. 添加机器人：基本 -> ABB 模型库 -> 选择 IRB 系列（如 IRB 120）
4. 创建系统：基本 -> 机器人系统 -> 从布局创建系统
   - 选择 RobotWare 6.08
   - 系统名如 `AI_Robot_System`
   - 点击"完成"，等待虚拟控制器启动
5. 确认虚拟控制器状态：控制器标签页出现 `AI_Robot_System` 且为运行中

## 3. 导入 RAPID 程序

1. 双击控制器下的 **RAPID**
2. 展开任务 `T_ROB1` -> 右键 -> **导入模块** -> 选择
   `robotstudio/rapid/socket_server.mod`
3. 程序指针设为 `main` 作为入口

## 4. 启动 Socket Server

1. 在 RAPID 中打开 `SocketServer` 模块
2. 启动程序：点击 **PP 到 main**（程序指针到 main），再点击 **启动**
3. 教学器/日志出现：`AI Agent SocketServer 等待连接 (端口 30000)`
4. 确认虚拟控制器网络：默认 127.0.0.1 可访问

## 5. Python 连接测试

1. 修改 `robotstudio/config.json`：

```json
{
  "backend": "real",
  "host": "127.0.0.1",
  "port": 30000,
  "timeout": 5
}
```

2. 运行真实连接测试：

```bash
python robotstudio/robotstudio_real_connection_test.py --real
```

预期输出：

```
[OK] Mock 连接/命令/返回格式测试通过
[OK] 真实 RobotStudio 连接成功 127.0.0.1:30000
     关节位置: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
[OK] move_home 执行成功: 0,0,0,0,0,0
```

## 6. Agent 调用流程

```
用户输入（GUI 对话）
  -> Agent.handle("回到Home位置")
    -> robot_tool(RobotStudioBackend)
      -> RobotStudioClient.send_action({"action": "move_home"})
        -> TCP: "HOME\n"
          -> RAPID HandleCommand -> MoveAbsJ 归零
        <- TCP: "OK 0,0,0,0,0,0"
    -> 返回 {ok, joints, last_action}
  -> GUI 显示执行结果与关节位置
```

## 7. 常见错误

| 错误 | 可能原因 | 解决 |
| --- | --- | --- |
| 连接超时 / Connection refused | 虚拟控制器未启动 / SocketServer 未运行 / 端口不对 | 启动 RAPID 程序；检查 config port |
| SocketBind 失败 | 端口 30000 被占用 | 换端口并同步改 config 与 .mod |
| RobotWare 不在下拉列表 | RobotWare 6.08 未安装或版本不匹配 | 安装匹配版本 |
| 命令返回 ERROR 未知命令 | 协议不一致 | 检查 .mod 与 command_schema.py 一致 |
| 中文乱码 | 终端编码 | 用 Windows Terminal + UTF-8 |
| 断线后无响应 | 连接被关闭 | 客户端自动重连（已实现）；确认 RAPID 仍监听 |

## 附：Mock 与 Real 切换

- `"backend": "mock"`：本地 Mock 服务端，无 RobotStudio 也能全链路测试
- `"backend": "real"`：连接 RobotStudio 虚拟控制器
