# -*- coding: utf-8 -*-
"""
robotstudio_tool.py — RobotStudio 执行后端 (V6.0)
=================================================
RobotTool 的第三种 backend（Gazebo/本地之外），负责与 ABB RobotStudio
虚拟控制器通信，执行 Home / MoveJ / MoveL 等简单工业机器人动作。

两种用法：
  1. RobotStudioBackend：作为 RobotTool 的 backend（主链路，AI 决策层不直接
     接触 RobotStudio 代码）
  2. RobotStudioTool：独立 BaseTool，供直接调用/未来扩展

Mock 模式：无 RobotStudio 时自动使用本地 Mock 服务端，协议完全一致。
"""

from agent.tools.base import BaseTool
from robotstudio.config import load_config as load_rs_config
from robotstudio.robotstudio_client import RobotStudioClient


class RobotStudioBackend:
    """RobotTool 的 RobotStudio backend（与 Local/Ros2 backend 同接口）"""

    def __init__(self, client=None):
        self.client = client or self._build_client()
        self.last_action = None

    @staticmethod
    def _build_client():
        cfg = load_rs_config()
        mock = cfg.get("backend", "mock") == "mock"
        return RobotStudioClient(
            host=cfg.get("host", "127.0.0.1"),
            port=int(cfg.get("port", 30000)),
            timeout_seconds=float(cfg.get("timeout_seconds", 5.0)),
            mock=mock,
        )

    def execute(self, action):
        """执行一条动作（move_home / joint_move / linear_move）"""
        try:
            self.client.connect()
            reply = self.client.send_action(action)
            self.last_action = action.get("action") or action.get("type")
            message = reply.get("message") or (
                "执行成功" if reply.get("ok") else "执行失败"
            )
            return {
                "ok": bool(reply.get("ok")),
                "messages": [message],
                "workspace": {"关节位置": [str(j) for j in (reply.get("joints") or [])]},
                "joints": reply.get("joints"),
                "last_action": self.last_action,
            }
        except Exception as exc:
            return {
                "ok": False,
                "messages": [f"RobotStudio 执行异常: {exc}"],
                "workspace": None,
                "joints": None,
                "last_action": self.last_action,
            }

    def get_state(self):
        """返回当前关节位置与连接状态"""
        try:
            self.client.connect()
            reply = self.client.get_position()
            return {
                "workspace": {"关节位置": [str(j) for j in (reply.get("joints") or [])]},
                "joints": reply.get("joints"),
                "connected": self.client.connected,
                "last_action": self.last_action,
            }
        except Exception:
            return {
                "workspace": None,
                "joints": None,
                "connected": False,
                "last_action": self.last_action,
            }

    def close(self):
        self.client.close()


class RobotStudioTool(BaseTool):
    """独立 RobotStudio 工具（统一接口 run(args)）"""

    name = "robotstudio_tool"
    description = (
        "控制 ABB RobotStudio 虚拟机器人。"
        "args: {'action': 'move_home|joint_move|linear_move', 'joints': [...], 'target': [...]}"
    )

    def __init__(self, backend=None):
        self.backend = backend or RobotStudioBackend()

    def run(self, args):
        action = {
            "action": args.get("action") or args.get("type"),
            "joints": args.get("joints"),
            "target": args.get("target"),
        }
        out = self.backend.execute(action)
        return {
            "ok": out.get("ok", False),
            "result": {"joints": out.get("joints"), "last_action": out.get("last_action")},
            "message": (out.get("messages") or [""])[-1],
        }
