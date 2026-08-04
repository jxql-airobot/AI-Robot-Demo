# -*- coding: utf-8 -*-
"""
core.py — Agent 主类 (V5.2)
===========================
流程：
  用户输入 → 指代消解 + 上下文更新 → 生成可解释 Plan → 按步骤调工具
  → 汇总结果 + 更新当前状态 → 返回 AgentResponse
"""

import os
import logging
import time

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
logger = logging.getLogger(__name__)


def _default_db_path():
    """默认记忆库：ROS2 工作区库存在则用它，否则用仓库根目录库"""
    ros2_db = os.path.expanduser("~/ros2_ws/database.db")
    local_db = os.path.join(REPO_ROOT, "database.db")
    return ros2_db if os.path.exists(ros2_db) else local_db


class Agent:
    """AI Robot 智能体：任务理解 → 计划 → 工具调用 → 结果返回"""

    def __init__(
        self,
        backend="ros2",
        db_path=None,
        planner=None,
        ros2_client=None,
        robotstudio_client=None,
        rag_enabled=True,
    ):
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
        self.robotstudio_client = None
        self.embedder = None
        self.vector_store = None
        self.retriever = None
        self.rag_enabled = rag_enabled
        self._init_rag()

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
        elif backend == "robotstudio":
            # V6.0: ABB RobotStudio 工业机器人仿真后端（Mock 可测）
            from agent.tools.robotstudio_tool import RobotStudioBackend

            robot_backend = RobotStudioBackend(client=robotstudio_client)
            self.robotstudio_client = robot_backend.client
            vision = VisionTool(memory=self.memory)
            environment = EnvironmentTool(robot=robot_backend, memory=self.memory)
        else:
            robot_backend = LocalRobotBackend()
            vision = VisionTool(memory=self.memory)
            environment = EnvironmentTool(robot=robot_backend, memory=self.memory)

        self.registry = {
            "memory_tool": MemoryTool(
                self.memory,
                vector_store=self.vector_store,
                embedder=self.embedder,
                retriever=self.retriever,
            ),
            "robot_tool": RobotTool(robot_backend),
            "vision_tool": vision,
            "environment_tool": environment,
        }
        self.context = AgentContext()
        self.planner = planner or build_plan_planner(self.registry)
        self.executor = PlanExecutor(self.registry)

    def _init_rag(self):
        """初始化 RAG（模型可用时）；失败自动降级为关键词检索"""
        if not self.rag_enabled:
            return  # 实验用：禁用 RAG，仅关键词检索
        try:
            import importlib.util

            if importlib.util.find_spec("sentence_transformers") is None:
                return  # 未安装 RAG 依赖，跳过
            from agent.rag.embedder import Embedder
            from agent.rag.model_download import ensure_model
            from agent.rag.retriever import HybridRetriever
            from agent.rag.vector_store import VectorStore

            ensure_model()
            self.embedder = Embedder()
            self.vector_store = VectorStore(self.db_path)
            self.vector_store.rebuild(self.memory, self.embedder)
            self.retriever = HybridRetriever(
                self.vector_store, self.memory, self.embedder
            )
        except Exception as exc:
            logger.warning("RAG 初始化失败，降级为关键词检索: %s", exc)
            self.embedder = None
            self.vector_store = None
            self.retriever = None

    def handle(self, task, task_type=None):
        """处理一条自然语言任务，返回 AgentResponse

        task_type: 实验用可选字段（如 basic_motion / planning / rag / vision），
                   用于运行时日志分类统计；不传则记 "general"。
        """
        t0 = time.monotonic()
        resolved = self.context.resolve_reference(task)
        self.context.update_task(resolved)
        memory_text = self._retrieve_memories(resolved)
        raw_plan = self.planner.plan(resolved, self.context, memory_text)
        plan = normalize_plan(raw_plan)
        t_plan = time.monotonic()
        step_results = self.executor.execute(plan)
        t_exec = time.monotonic()
        final_message = self._summarize(plan, step_results)
        current_state = self._extract_state(step_results)
        self.context.update_result(plan, final_message, current_state)
        # V5.4: 评测用计时数据
        self.last_timings = {
            "total_seconds": round(t_exec - t0, 4),
            "plan_seconds": round(t_plan - t0, 4),
            "exec_seconds": round(t_exec - t_plan, 4),
        }
        # V6.2: 统一实验日志（自动记录，日志失败不影响主流程）
        self._log_task(task, raw_plan, plan, step_results, task_type)
        return {
            "plan": plan,
            "step_results": step_results,
            "final_message": final_message,
            "current_state": current_state,
        }

    def _log_task(self, task, raw_plan, plan, step_results, task_type=None):
        """V6.2: 写入统一实验日志（JSON Lines -> experiments/results/runtime_logs.json）"""
        try:
            from experiments.tasklog.task_logger import TaskLogger

            steps = plan.get("steps", [])
            tool_calls = [
                {
                    "tool": s.get("tool"),
                    "args": s.get("args", {}),
                    "purpose": s.get("purpose", ""),
                }
                for s in steps
            ]
            errors = [r.get("message") for r in step_results if not r.get("ok")]
            timings = self.last_timings
            TaskLogger().log(
                task_type=task_type or "general",
                input=task,
                agent_enabled=True,
                rag_enabled=self.rag_enabled,
                planner_output=raw_plan,
                generated_plan=plan,
                tool_calls=tool_calls,
                backend=self.backend,
                execution_result=step_results,
                success=bool(steps) and all(r.get("ok") for r in step_results),
                error="; ".join(errors) if errors else "",
                response_time=timings.get("total_seconds"),
                planning_time=timings.get("plan_seconds"),
                execution_time=timings.get("exec_seconds"),
            )
        except Exception:
            pass

    def retrieve_memories(self, query, top_k=10):
        """供 GUI 记忆页使用：返回带来源的混合检索结果"""
        if self.retriever is not None:
            try:
                return self.retriever.retrieve(query, top_k=top_k)
            except Exception:
                pass
        return [
            {"topic": t, "content": c, "category": cat, "source": "关键词检索"}
            for t, c, cat in self.memory.search(query, limit=top_k)
        ]

    def _retrieve_memories(self, query):
        """规划时注入相关记忆文本（RAG 优先，关键词兜底）"""
        rows = self.retrieve_memories(query, top_k=5)
        if not rows:
            return "（无相关记忆）"
        lines = [
            f"- {r['topic']}：{r['content']}（{r['category']}）[来源：{r['source']}]"
            for r in rows
        ]
        return "\n".join(lines)

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
        if self.robotstudio_client is not None:
            self.robotstudio_client.close()
