# -*- coding: utf-8 -*-
"""
robotstudio_backend.py — GUI RobotStudio 模式后端 (V6.0)
========================================================
复用 V5.1 的 AgentBackend 接口（backend.py 未修改），
内部使用 RobotStudioAgent（Mock / 真实双模式）。
"""

import time

from backend import AgentBackend


class RobotStudioBackend(AgentBackend):
    """RobotStudio 模式后端"""

    name = "RobotStudio"

    def __init__(self, planner=None):
        from config import ROS2_DB_PATH
        from memory import MemoryStore
        from robotstudio.robotstudio_agent import RobotStudioAgent

        self.memory = MemoryStore(ROS2_DB_PATH)
        self.agent = RobotStudioAgent(db_path=ROS2_DB_PATH, planner=planner)

    def handle_task(self, task):
        return self.agent.handle(task)

    def send_task(self, text):
        pass  # 对话已走 Agent（handle_task），兼容接口保留

    def get_status(self):
        st = self.agent.robotstudio_client.get_status()
        joints = st.get("joints") or []
        text = f"RobotStudio: 关节={[round(j, 3) for j in joints]} 最后动作={st.get('last_action')}"
        return (text, time.time())

    def get_robot_status(self):
        return self.agent.robotstudio_client.get_status()

    def get_vision(self):
        return None  # RobotStudio 模式暂无非标相机

    def get_odom(self):
        return None

    def list_memories(self):
        return self.memory.all_memories()

    def search_memories(self, query):
        query = (query or "").strip()
        return self.memory.all_memories() if not query else self.memory.search(query, limit=50)

    def semantic_search(self, query):
        return self.agent.retrieve_memories(query, top_k=20)

    def close(self):
        self.agent.close()
