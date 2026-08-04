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

# 把 gui/ 与项目根目录加入 sys.path，便于复用 config.py 和根目录的 llm.py / memory.py / robot.py
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (GUI_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from config import ROS2_DB_PATH  # noqa: E402


class AgentBackend:
    """GUI 后端接口：界面层只依赖这组方法"""

    name = "base"

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

    def close(self):
        """释放资源"""
        pass


class Ros2Backend(AgentBackend):
    """ROS2 模式后端：通过 Ros2Client 与仿真系统通信"""

    name = "ROS2"

    def __init__(self):
        # 延迟导入：rclpy 只在 source 过 ROS2 的环境可用；
        # memory.py 复用仓库根目录的 V2 记忆系统（不修改原文件）
        from ros2_client import Ros2Client
        from memory import MemoryStore

        self.client = Ros2Client()
        self.memory = MemoryStore(ROS2_DB_PATH)

    def send_task(self, text):
        self.client.send_task(text)

    def get_status(self):
        return self.client.get_status()

    def get_vision(self):
        return self.client.get_vision()

    def get_odom(self):
        return self.client.get_odom()

    def list_memories(self):
        """查看全部记忆（V5.1 只做查看和查询，不做删除）"""
        return self.memory.all_memories()

    def search_memories(self, query):
        """按关键词查询记忆"""
        query = (query or "").strip()
        if not query:
            return self.memory.all_memories()
        return self.memory.search(query, limit=50)

    def close(self):
        self.client.close()


class LocalBackend(AgentBackend):
    """本地模式后端（规划中，后续实现）：复用 V1/V2 的 llm/memory/robot"""

    name = "Local"

    def __init__(self):
        raise NotImplementedError("本地模式为后续版本功能，V5.1 暂未开放")
