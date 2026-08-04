# Agent 设计说明

## 1. 功能介绍

Agent 层（`agent/`）是系统的"新大脑"，实现：

```
用户输入 → 任务理解 → 可解释 Plan → 工具调用 → 已有模块执行 → 结果返回
```

核心能力：

- **可解释 Plan**：统一输出 `task_analysis / goal / steps / current_state`，
  不展示 LLM 完整思考链，科研演示可观测
- **四工具**：memory_tool / robot_tool / vision_tool / environment_tool
- **多轮上下文**：会话历史 + 指代消解（"那个零件"→ 上一操作对象）
- **双后端**：本地模式（SimRobot）/ ROS2 模式（驱动现有 robot_controller）

## 2. 技术选择原因

- **工具化（BaseTool 接口）**：Agent 与底层解耦，新增工具只需实现 `run()` 并注册
- **Plan 结构化**：LLM 输出可校验、可展示、可执行的计划，而不是自由文本
- **不修改 V1-V4**：Agent 只读复用 `memory.py` / `robot.py` / ROS2 话题，
  双链路共存（task_cli → ai_brain 原链路保留）
- **复用 ROS2 客户端**：Agent 可注入外部 `ros2_client`，GUI 全程只有一个 rclpy 节点

## 3. 数据流程

```
用户输入
  → AgentContext.resolve_reference()   # 指代消解
  → AgentContext.update_task()         # 记录会话
  → Planner.plan(task, context)        # DeepSeek/Mock 生成 Plan
  → PlanExecutor.execute(plan)         # 按步骤调用 TOOL_REGISTRY 中的工具
      ├─ memory_tool      → SQLite
      ├─ vision_tool      → /ai_robot/vision
      ├─ environment_tool → 工作台/工位/里程计
      └─ robot_tool       → /ai_robot/action → robot_controller
  → 汇总结果 + 更新当前状态 → AgentResponse
```

### Plan 结构

```json
{
  "task_analysis": "用户想把红色零件移动到检测区",
  "goal": "把 红色零件 移动到 检测区",
  "steps": [
    {"tool": "robot_tool", "args": {"action": "move", "object": "红色零件", "target": "检测区"},
     "purpose": "把 红色零件 从当前位置移动到 检测区"}
  ],
  "current_state": "上料区: 蓝色零件/绿色零件; 检测区: 红色零件; 成品区: 空"
}
```

## 4. 当前实现状态

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `agent/core.py` | ✅ | Agent 主类（handle 流程） |
| `agent/planner.py` | ✅ | DeepSeekPlanPlanner + MockPlanPlanner |
| `agent/executor.py` | ✅ | 按步骤执行，失败即停 |
| `agent/context.py` | ✅ | 会话上下文 + 指代消解 |
| `agent/plan_schema.py` | ✅ | Plan 结构规范化 |
| `agent/tools/` | ✅ | 四工具 |
| `agent/agent_cli.py` | ✅ | 终端入口（--local / --mock） |
| 测试 | ✅ | test_agent / test_agent_ros2 / test_agent_backend 全通过 |

## 5. 未来扩展方向

- RAG 检索结果注入 Planner 上下文（V5.3 集成）
- 工具并行执行与任务队列
- 复杂任务多步分解（一个任务多个动作序列）
- 记忆驱动的个性化（长期用户偏好）
