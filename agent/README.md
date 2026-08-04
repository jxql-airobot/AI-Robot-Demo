# AI Robot Agent 层设计 (V5.2)

> 状态：设计完成，待实现。本文档是 V5.2 的架构设计文档。

## 1. 架构设计

### 定位

新增独立 `agent/` 层，作为「AI Robot 智能体」的新大脑：

```
用户输入 (GUI 对话 / agent_cli)
        │
        ▼
   ┌─────────┐
   │  Agent  │  任务理解 + 会话上下文
   └────┬────┘
        ▼
   ┌─────────┐
   │ Planner │  生成可解释 Plan（任务分析/目标/执行步骤/当前状态）
   └────┬────┘
        ▼
   ┌─────────┐
   │Executor │  按步骤调用工具
   └────┬────┘
        ▼
  ┌──────────────────────────┐
  │ tools: memory/robot/     │
  │        vision/environment│
  └────┬─────────────────────┘
        ▼
   已有模块: memory.py / robot.py / ROS2 话题 (V1-V4 零修改)
```

### 设计原则

1. **V1-V4 零修改**：llm.py / memory.py / robot.py / ROS2 节点 / Gazebo 全部不动
2. **可解释 Plan，不展示 LLM 完整思考链**：只展示
   `任务分析 / 目标 / 执行步骤 / 当前状态`
3. **工具化**：Agent 通过四个工具调用已有能力，工具接口统一
4. **双后端**：robot_tool 支持本地模拟（robot.py）和 ROS2（/ai_robot/action → robot_controller）

## 2. 文件规划

| 文件 | 作用 |
| --- | --- |
| `agent/__init__.py` | 包声明，导出 Agent |
| `agent/core.py` | Agent 主类：handle(task) = 上下文更新 → 规划 → 执行 → 结果汇总 |
| `agent/planner.py` | Plan 生成：DeepSeekPlanPlanner（LLM）+ MockPlanPlanner（离线） |
| `agent/executor.py` | Plan 执行器：按 steps 依次调用工具，收集每步结果 |
| `agent/context.py` | 会话上下文：多轮对话、上一计划/结果、当前工作台状态、指代消解 |
| `agent/plan_schema.py` | Plan 数据结构与校验（字段：task_analysis/goal/steps/current_state） |
| `agent/tools/__init__.py` | 工具注册表 `TOOL_REGISTRY` |
| `agent/tools/base.py` | BaseTool 接口：name / description / run(args) -> dict |
| `agent/tools/memory_tool.py` | 记忆工具：查询/保存/列出（复用 memory.py） |
| `agent/tools/robot_tool.py` | 机器人工具：执行动作（本地 SimRobot 或 ROS2 发布 action） |
| `agent/tools/vision_tool.py` | 视觉工具：读取最新识别结果（ROS2 /ai_robot/vision 或记忆） |
| `agent/tools/environment_tool.py` | 环境工具：工作台/工位/里程计/环境记忆 |
| `agent/agent_cli.py` | 终端入口：与 GUI 共用 Agent，方便独立测试（第二步实现） |
| `agent/README.md` | 本文档 |

## 3. 数据流

```
用户自然语言
  → Agent.handle(task)
     1. context.update(task)             # 会话上下文 + 指代消解
     2. planner.plan(task, context)      # 生成 Plan JSON
     3. executor.execute(plan)           # 按步骤调工具
          ├─ memory_tool     → MemoryStore (SQLite)
          ├─ vision_tool     → /ai_robot/vision (ROS2) 或 记忆中的物体信息
          ├─ environment_tool → 工作台/工位/odom/环境记忆
          └─ robot_tool      → /ai_robot/action → robot_controller (V3/V4 节点不变)
                                 → /ai_robot/status 回传结果
     4. context.update_result(plan, results)  # 更新当前状态
  → 返回 AgentResponse {plan, step_results, final_message, current_state}
  → GUI 展示：任务分析 / 目标 / 执行步骤 / 当前状态 + 各步结果
```

### Plan 数据结构

```json
{
  "task_analysis": "用户想把红色零件移动到检测区",
  "goal": "红色零件从当前位置移动到检测区",
  "steps": [
    {"tool": "vision_tool", "args": {"scan": true}, "purpose": "确认红色零件当前位置"},
    {"tool": "robot_tool", "args": {"action": "move", "object": "红色零件", "target": "检测区"}, "purpose": "执行移动"},
    {"tool": "environment_tool", "args": {}, "purpose": "核对执行后的工作台状态"}
  ],
  "current_state": "上料区: 红色/蓝色/绿色零件; 检测区: 空; 成品区: 空"
}
```

### GUI 展示映射

```
任务分析：<task_analysis>
目标：<goal>
执行步骤：
  1. <purpose>（工具：<tool>）
  2. ...
当前状态：<current_state>
```

## 4. 工具接口

```python
class BaseTool:
    name: str
    description: str
    def run(self, args: dict) -> dict:
        # 返回 {"ok": bool, "result": ..., "message": str}
```

| 工具 | 能力 | 底层复用 |
| --- | --- | --- |
| `memory_tool` | 查询 / 保存 / 列出记忆 | memory.py (MemoryStore) |
| `robot_tool` | 执行 move/pick/place/scan 动作 | 本地: robot.py (SimRobot)；ROS2: /ai_robot/action + /ai_robot/status |
| `vision_tool` | 读取最新视觉识别结果 | ROS2: /ai_robot/vision 快照；本地: 记忆中的物体信息 |
| `environment_tool` | 工作台布局、工位、里程计、环境记忆 | ROS2: /odom + status；本地: SimRobot.workspace |

## 5. 兼容性说明

- **不修改**：`llm.py`、`memory.py`、`robot.py`、`brain_node.py`、`robot_controller.py`、
  `vision_node.py`、`task_cli.py`、launch 文件、URDF/SDF、Gazebo 相关
- **复用（只读导入）**：`memory.py` 的 MemoryStore；`gui/ros2_client.py` 的 Ros2Client
  （GUI 与 agent 同进程，避免重复实现 ROS2 客户端）
- **双链路共存**：V3/V4 原链路（task_cli → ai_brain → robot_controller）保留不动；
  V5.2 的 Agent 走 GUI 对话区或 agent_cli，直接通过 robot_tool 驱动 robot_controller

## 6. 后续步骤

1. 第二步：实现 agent 层代码（core/planner/executor/context/tools）
2. 第三步：GUI 集成可解释 Plan 展示与工具执行结果
3. 第四步：测试（mock 离线 + ROS2 实机）+ 提交 + 打 tag `v5.2-agent`
