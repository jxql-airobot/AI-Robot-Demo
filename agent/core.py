# -*- coding: utf-8 -*-
"""
core.py — Agent 主类 (V5.2)
===========================
流程：
  用户输入 → 指代消解 + 上下文更新 → 生成可解释 Plan → 按步骤调工具
  → 汇总结果 + 更新当前状态 → 返回 AgentResponse
"""

import os

from agent.context import AgentContext
from agent.executor import PlanExecutor
from agent.plan_schema import normalize_plan
from agent.planner import build_plan_planner
from agent.tools.environment_tool import EnvironmentTool
from agent.tools.memory_tool import MemoryTool
from agent.tools.robot_tool import (
    LocalRobotBackend,
    RobotTool,
    Ros2RobotBackend,
    format_workspace,
)
from agent.tools.vision_tool import VisionTool

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_db_path():
    """默认记忆库：ROS2 工作区库存在则用它，否则用仓库根目录库"""
    ros2_db = os.path.expanduser("~/ros2_ws/database.db")
    local_db = os.path.join(REPO_ROOT, "database.db")
    return ros2_db if os.path.exists(ros2_db) else local_db


class Agent:
    """AI Robot 智能体：任务理解 → 计划 → 工具调用 → 结果返回"""

    def __init__(self, backend="ros2", db_path=None, planner=None, ros2_client=None):
        """
        backend: "ros2"（主模式，驱动现有 robot_controller）| "local"（SimRobot）
        planner: 传入规划器实例；默认自动选择 DeepSeek 或 Mock
        ros2_client: 复用外部 ROS2 客户端（GUI 场景避免创建第二个节点）
        """
        from memory import MemoryStore  # 只读复用 V2 记忆系统

        self.backend = backend
        self.db_path = db_path or _default_db_path()
        self.memory = MemoryStore(self.db_path)
        self.ros2_client = None

        if backend == "ros2":
            if ros2_client is None:
                from gui.ros2_client import Ros2Client  # 复用 V5.1 GUI 客户端

                ros2_client = Ros2Client()
            self.ros2_client = ros2_client
            robot_backend = Ros2RobotBackend(self.ros2_client)
            vision = VisionTool(memory=self.memory, ros2_client=self.ros2_client)
            environment = EnvironmentTool(
                robot=robot_backend,
                ros2_client=self.ros2_client,
                memory=self.memory,
            )
        else:
            robot_backend = LocalRobotBackend()
            vision = VisionTool(memory=self.memory)
            environment = EnvironmentTool(robot=robot_backend, memory=self.memory)

        self.registry = {
            "memory_tool": MemoryTool(self.memory),
            "robot_tool": RobotTool(robot_backend),
            "vision_tool": vision,
            "environment_tool": environment,
        }
        self.context = AgentContext()
        self.planner = planner or build_plan_planner(self.registry)
        self.executor = PlanExecutor(self.registry)

    def handle(self, task):
        """处理一条自然语言任务，返回 AgentResponse"""
        resolved = self.context.resolve_reference(task)
        self.context.update_task(resolved)
        plan = normalize_plan(self.planner.plan(resolved, self.context))
        step_results = self.executor.execute(plan)
        final_message = self._summarize(plan, step_results)
        current_state = self._extract_state(step_results)
        self.context.update_result(plan, final_message, current_state)
        return {
            "plan": plan,
            "step_results": step_results,
            "final_message": final_message,
            "current_state": current_state,
        }

    def _summarize(self, plan, results):
        if not results:
            return "计划为空，无法执行"
        parts = [r.get("message") or ("成功" if r.get("ok") else "失败") for r in results]
        return "；".join(parts)

    def _extract_state(self, results):
        """从执行结果中提取最新工作台状态文本"""
        for r in reversed(results):
            result = r.get("result")
            if isinstance(result, dict) and result.get("workspace"):
                return format_workspace(result["workspace"])
        return None

    def close(self):
        """释放资源（ROS2 客户端等）"""
        if self.ros2_client is not None:
            self.ros2_client.close()
