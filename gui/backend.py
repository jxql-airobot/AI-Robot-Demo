# -*- coding: utf-8 -*-
"""
backend.py — GUI 后端抽象 (V5.1)
================================
统一的后端接口，让 Streamlit 界面不关心底层是 ROS2 还是本地模拟：
  - AgentBackend：接口定义
  - Ros2Backend：连接 ROS2 仿真系统（主模式）
  - LocalBackend：直接复用 V1/V2 的 llm/memory/robot（规划中，后续实现）
"""

import os
import sys
import time

# 把 gui/ 与项目根目录加入 sys.path，便于复用 config.py 和根目录的 llm.py / memory.py / robot.py
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (GUI_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from config import resolve_gui_db_path  # noqa: E402


class AgentBackend:
    """GUI 后端接口：界面层只依赖这组方法"""

    name = "base"

    def handle_task(self, task):
        """V5.2: 用 Agent 处理任务，返回 {plan, step_results, final_message, current_state}"""
        raise NotImplementedError

    def send_task(self, text):
        """发送自然语言任务"""
        raise NotImplementedError

    def get_status(self):
        """返回 (状态文本, 时间戳) 或 None"""
        raise NotImplementedError

    def get_vision(self):
        """返回最近一次视觉识别 dict 或 None"""
        raise NotImplementedError

    def get_odom(self):
        """返回最近一次里程计 dict 或 None"""
        raise NotImplementedError

    def list_memories(self):
        """返回全部记忆 [(topic, content, category), ...]"""
        raise NotImplementedError

    def search_memories(self, query):
        """按关键词查询记忆 [(topic, content, category), ...]"""
        raise NotImplementedError

    def semantic_search(self, query):
        """V5.3: 混合检索记忆 [{"topic", "content", "category", "source"}, ...]"""
        raise NotImplementedError

    def close(self):
        """释放资源"""
        pass


class Ros2Backend(AgentBackend):
    """ROS2 模式后端：通过 Ros2Client 与仿真系统通信"""

    name = "ROS2"

    def __init__(self, planner=None, robot_backend="gazebo"):
        # 延迟导入：rclpy 只在 source 过 ROS2 的环境可用；
        # memory.py 复用仓库根目录的 V2 记忆系统（不修改原文件）
        from memory import MemoryStore
        from agent import Agent

        self.memory = MemoryStore(resolve_gui_db_path())
        self.robot_backend = robot_backend
        self.last_result_message = ""
        self.last_task = ""
        self.last_success = None
        self.last_exec_s = None
        self.client = None
        if robot_backend == "gazebo":
            from ros2_client import Ros2Client

            self.client = Ros2Client()
            agent_backend = "ros2"
        else:
            # V6.0: RobotStudio 后端（Mock 可测，无需 ROS2 节点）
            agent_backend = "robotstudio"
        # V5.2: GUI 对话走 Agent（可解释 Plan + 四工具），Gazebo 模式复用 ROS2 客户端
        self.agent = Agent(
            backend=agent_backend,
            ros2_client=self.client,
            db_path=resolve_gui_db_path(),
            planner=planner,
        )

    def handle_task(self, task):
        """Agent 处理任务：生成可解释 Plan 并调用工具执行"""
        resp = self.agent.handle(task)
        self.last_result_message = resp.get("final_message", "")
        self.last_task = task
        steps = resp["plan"].get("steps", [])
        self.last_success = bool(steps) and all(r.get("ok") for r in resp["step_results"])
        # 最近一次机器人错误码（如 50050），供界面展示
        self.last_error_code = None
        for r in resp["step_results"]:
            if not r.get("ok"):
                result = r.get("result")
                structured = result.get("error") if isinstance(result, dict) else None
                if isinstance(structured, dict) and structured.get("code"):
                    self.last_error_code = str(structured["code"])
                    break
        timings = getattr(self.agent, "last_timings", {})
        self.last_exec_s = timings.get("exec_seconds")
        return resp

    def system_status(self):
        """V6.2: 返回 {llm, rag, robot} 系统状态，供侧边栏显示"""
        from agent.planner import DeepSeekPlanPlanner

        llm = "OK" if isinstance(self.agent.planner, DeepSeekPlanPlanner) else "MOCK"
        rag = "OK" if self.agent.retriever is not None else "DEGRADED"
        robot = "CONNECTED"
        try:
            state = self.agent.registry["robot_tool"].backend.get_state()
            if state is None or state.get("connected") is False:
                robot = "OFF"
        except Exception:
            robot = "OFF"
        return {"llm": llm, "rag": rag, "robot": robot}

    def send_task(self, text):
        self.client.send_task(text)

    def get_status(self):
        return self.client.get_status()

    def get_vision(self):
        return self.client.get_vision()

    def get_odom(self):
        if self.client is not None:
            return self.client.get_odom()
        # V6.0: RobotStudio 模式返回关节位置快照
        try:
            state = self.agent.registry["robot_tool"].backend.get_state()
            if state and state.get("joints") is not None:
                return (
                    {
                        "joints": state["joints"],
                        "connected": state.get("connected", False),
                        "last_action": state.get("last_action"),
                        "last_result": self.last_result_message,
                    },
                    time.time(),
                )
        except Exception:
            pass
        return None

    def list_memories(self):
        """查看全部记忆（V5.1 只做查看和查询，不做删除）"""
        return self.memory.all_memories()

    def search_memories(self, query):
        """按关键词查询记忆"""
        query = (query or "").strip()
        if not query:
            return self.memory.all_memories()
        return self.memory.search(query, limit=50)

    def semantic_search(self, query):
        """V5.3: 走 Agent 的 RAG 混合检索，结果带来源"""
        return self.agent.retrieve_memories(query, top_k=20)

    def close(self):
        self.agent.close()
        if self.client is not None:
            self.client.close()


class LocalBackend(AgentBackend):
    """本地模式后端（规划中，后续实现）：复用 V1/V2 的 llm/memory/robot"""

    name = "Local"

    def __init__(self):
        raise NotImplementedError("本地模式为后续版本功能，V5.1 暂未开放")
