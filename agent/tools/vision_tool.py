# -*- coding: utf-8 -*-
"""
vision_tool.py — 视觉工具 (V5.2)
================================
读取最新视觉识别结果：
  - ROS2 模式：/ai_robot/vision 快照（vision_node 持续运行）
  - 本地模式：记忆库中的物体信息（视觉结果由 vision_node 写入）
"""

from agent.tools.base import BaseTool


class VisionTool(BaseTool):
    """视觉识别工具"""

    name = "vision_tool"
    description = "读取视觉识别结果。args: {'scan': true}"

    def __init__(self, memory=None, ros2_client=None):
        self.memory = memory
        self.ros2_client = ros2_client

    def run(self, args):
        if self.ros2_client is not None:
            vision = self.ros2_client.get_vision()
            parts = vision[0].get("parts", {}) if vision else {}
            return {
                "ok": True,
                "result": {"parts": parts},
                "message": f"识别到 {len(parts)} 个零件",
            }
        if self.memory is not None:
            rows = [r for r in self.memory.all_memories() if r[2] == "物体信息"]
            parts = {r[0]: r[1] for r in rows[-10:]}
            return {
                "ok": True,
                "result": {"parts": parts},
                "message": f"记忆中共 {len(parts)} 条物体信息",
            }
        return {"ok": False, "message": "无视觉数据源"}
