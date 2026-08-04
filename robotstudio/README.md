# ABB RobotStudio Backend (V6.0)

AI Agent 控制 ABB RobotStudio 虚拟工业机器人的执行后端。
当前为第一阶段：**Mock 模式完整软件链路**，不依赖 RobotStudio/RobotWare。

## 定位

RobotStudio 只是「基于大语言模型的工业机器人智能体执行平台」的**执行后端之一**：

```
AI Agent（决策层）
  -> RobotTool（工具接口）
    -> GazeboBackend      （现有，ROS2 仿真）
    -> RobotStudioBackend （新增，ABB 工业机器人仿真）
```

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `command_schema.py` | 统一动作 -> RAPID 文本命令（HOME/MOVEJ/MOVEL/GETPOS），回复解析 |
| `robotstudio_client.py` | TCP 客户端（连接/发命令/收回复），Mock 自动起本地服务端 |
| `mock_robotstudio.py` | Mock 虚拟控制器（本地 TCP 服务端，协议与 RAPID 一致） |
| `config.py` / `config.json` | 主机/端口/超时/后端模式配置（backend: mock/real） |
| `rapid/socket_server.mod` | RAPID SocketServer 程序（第二阶段导入 RobotStudio 用） |
| `test_robotstudio.py` | 模块测试：schema + 客户端 + Mock 闭环 + Backend |

## 通信协议（RAPID Socket TCP）

```
客户端 -> HOME\n | MOVEJ j1,...,j6\n | MOVEL x,y,z,rx,ry,rz\n | GETPOS\n
服务端 <- OK j1,...,j6\n | ERROR <message>\n
```

## 使用方法

```bash
# 1. Mock 闭环测试（无需 RobotStudio）
python robotstudio/test_robotstudio.py

# 2. Agent 集成测试（自然语言 -> 规划 -> RobotStudio 后端）
python agent/test_robotstudio_tool.py

# 3. GUI 后端测试（WSL）
python3 gui/test_robotstudio_backend.py
```

## 第二阶段（真实 RobotStudio 联调）

需要人工完成：

1. 安装 RobotWare 6.08（与 RobotStudio 版本匹配）
2. RobotStudio 新建工作站 -> 添加 ABB 机器人（如 IRB 120）
3. 创建系统并启动虚拟控制器
4. 导入 `rapid/socket_server.mod` 并运行（监听端口 30000）
5. `config.json` 中 `backend` 改为 `"real"`，确认 host/port
6. Python TCP 连接测试
