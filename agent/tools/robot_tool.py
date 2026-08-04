# -*- coding: utf-8 -*-
"""
robot_tool.py — 机器人工具 (V5.2)
=================================
双后端：
  - LocalRobotBackend : 复用 V1/V2 robot.py 的 SimRobot（本地模式）
  - Ros2RobotBackend  : 发布 /ai_robot/action -> 现有 robot_controller 执行（ROS2 模式）
不修改任何 V1-V4 节点。
"""

import json
import time

from agent.tools.base import BaseTool


def parse_workspace(text):
    """从 '工作台: {json}' 状态文本中提取工位字典"""
    if not text or "工作台:" not in text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def format_workspace(ws):
    """把工作台字典格式化成文本，如 '上料区: 红色零件/蓝色零件; 检测区: 空'"""
    if not ws:
        return "未知"
    parts = []
    for station, items in ws.items():
        parts.append(f"{station}: {'/'.join(items) if items else '空'}")
    return "; ".join(parts)


class LocalRobotBackend:
    """本地模式：直接操作 SimRobot 世界模型"""

    def __init__(self):
        from robot import SimRobot  # 只读复用 V1/V2 代码

        self.robot = SimRobot()

    def execute(self, action):
        self.robot.execute(action)
        return {
            "ok": True,
            "messages": [f"动作执行完成: {action.get('action')}"],
            "workspace": {k: list(v) for k, v in self.robot.workspace.items()},
            "gripper": self.robot.gripper,
        }

    def get_state(self):
        return {
            "workspace": {k: list(v) for k, v in self.robot.workspace.items()},
            "gripper": self.robot.gripper,
        }


class Ros2RobotBackend:
    """ROS2 模式：发布 /ai_robot/action，等待 /ai_robot/status 回传"""

    QUIET_SECONDS = 1.5
    TIMEOUT_SECONDS = 20.0

    def __init__(self, ros2_client):
        self.ros2 = ros2_client

    def execute(self, action):
        baseline = self.ros2.get_status()
        baseline_ts = baseline[1] if baseline else None
        self.ros2.publish_action(action)

        msgs = []
        seen = set()
        last_seen_ts = None
        last = time.monotonic()
        deadline = time.monotonic() + self.TIMEOUT_SECONDS
        ws = None
        while time.monotonic() < deadline:
            status = self.ros2.get_status()
            if (
                status
                and status[1] != last_seen_ts
                and (baseline_ts is None or status[1] > baseline_ts)
            ):
                if status[0] not in seen:
                    msgs.append(status[0])
                    seen.add(status[0])
                    parsed = parse_workspace(status[0])
                    if parsed:
                        ws = parsed
                last_seen_ts = status[1]
                last = time.monotonic()
            if time.monotonic() - last > self.QUIET_SECONDS:
                break
            time.sleep(0.1)
        return {"ok": bool(msgs), "messages": msgs, "workspace": ws}

    def get_state(self):
        status = self.ros2.get_status()
        ws = parse_workspace(status[0]) if status else None
        return {"workspace": ws, "raw": status[0] if status else None}


class RobotTool(BaseTool):
    """机器人动作工具"""

    name = "robot_tool"
    description = (
        "执行机器人动作。"
        "args: {'action': 'move|pick|place|scan', 'object': '红色零件', 'target': '检测区'}"
    )

    def __init__(self, backend):
        self.backend = backend

    def run(self, args):
        action = dict(args)
        if "action" not in action:
            return {"ok": False, "message": "缺少 action 字段"}
        try:
            out = self.backend.execute(action)
        except Exception as exc:
            return {"ok": False, "message": f"机器人执行异常: {exc}"}
        messages = out.get("messages") or []
        message = messages[-1] if messages else f"动作执行完成: {action.get('action')}"
        return {
            "ok": out.get("ok", True),
            "result": {
                "workspace": out.get("workspace"),
                "gripper": out.get("gripper"),
            },
            "message": message,
        }
