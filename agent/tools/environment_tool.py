# -*- coding: utf-8 -*-
"""
environment_tool.py — 环境工具 (V5.2)
=====================================
获取环境状态：工作台/工位、机器人里程计、环境记忆。
"""

from agent.tools.base import BaseTool


class EnvironmentTool(BaseTool):
    """环境状态工具"""

    name = "environment_tool"
    description = (
        "获取环境状态。args: {'status': true} 或 {'odom': true} 或 {'memories': true}"
    )

    def __init__(self, robot=None, ros2_client=None, memory=None):
        self.robot = robot
        self.ros2_client = ros2_client
        self.memory = memory

    def run(self, args):
        out = {}
        if args.get("status") or args.get("workspace"):
            if self.robot is not None:
                out["robot"] = self.robot.get_state()
        if args.get("odom") and self.ros2_client is not None:
            odom = self.ros2_client.get_odom()
            out["odom"] = odom[0] if odom else None
        if args.get("memories") and self.memory is not None:
            rows = [r for r in self.memory.all_memories() if r[2] == "环境信息"]
            out["memories"] = rows
        return {"ok": True, "result": out, "message": "环境状态已获取"}
