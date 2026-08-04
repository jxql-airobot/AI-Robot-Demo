# -*- coding: utf-8 -*-
"""
robotstudio_agent.py — RobotStudio 后端 Agent (V6.0)
====================================================
通过子类复用 V5.2 Agent 核心（不修改 agent/core.py）：
  - 复用 memory / RAG / context / Plan 流程
  - 工具注册表替换为 RobotStudio 三件套：
    memory_tool / robotstudio_tool / vision_tool / environment_tool
"""

from agent import Agent
from agent.executor import PlanExecutor


class RobotStudioAgent(Agent):
    """RobotStudio 后端 Agent"""

    def __init__(self, db_path=None, planner=None, client=None):
        # 复用父类初始化（local 分支提供 memory/RAG/context 骨架）
        super().__init__(backend="local", db_path=db_path, planner=None)

        from agent.planner import build_plan_planner
        from agent.tools.environment_tool import EnvironmentTool
        from agent.tools.memory_tool import MemoryTool
        from agent.tools.robotstudio_tool import (
            RobotStudioStatusBackend,
            RobotStudioTool,
        )
        from agent.tools.vision_tool import VisionTool
        from robotstudio.robotstudio_client import RobotStudioClient

        self.backend = "robotstudio"
        self.robotstudio_client = client or RobotStudioClient()

        # 原地替换注册表（executor 共享同一 dict 引用）
        self.registry.clear()
        self.registry.update(
            {
                "memory_tool": MemoryTool(
                    self.memory,
                    vector_store=self.vector_store,
                    embedder=self.embedder,
                    retriever=self.retriever,
                ),
                "robotstudio_tool": RobotStudioTool(self.robotstudio_client),
                "vision_tool": VisionTool(memory=self.memory),
                "environment_tool": EnvironmentTool(
                    robot=RobotStudioStatusBackend(self.robotstudio_client),
                    memory=self.memory,
                ),
            }
        )
        # 工具集变化后重建规划器与执行器
        self.planner = planner or build_plan_planner(self.registry)
        self.executor = PlanExecutor(self.registry)

    def close(self):
        self.robotstudio_client.close()
        super().close()
