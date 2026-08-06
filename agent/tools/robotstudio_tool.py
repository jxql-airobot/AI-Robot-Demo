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
            timeout_seconds=float(cfg.get("timeout", 5.0)),
            mock=mock,
        )

    def execute(self, action):
        """执行一条动作（move_home / joint_move / linear_move）

        V6.2 统一错误格式：返回含 success/error/stage
        stage: "socket"（连接/通信失败）| "rapid"（RAPID 协议错误）
               | "motion"（机器人运动错误）| "ok"
        """
        try:
            self.client.connect()
            reply = self.client.send_action(action)
            self.last_action = action.get("action") or action.get("type")
            message = reply.get("message") or (
                "执行成功" if reply.get("ok") else "执行失败"
            )
            if reply.get("ok"):
                stage, error = "ok", ""
            else:
                # 结构化错误：RAPID 运动错误（如 50050）带 code/type/message，
                # 供 ObservationManager / ReflectionAnalyzer 解析
                stage = reply.get("stage") or "rapid"
                error = {
                    "code": reply.get("error_code"),
                    "type": reply.get("error_type") or "execution",
                    "message": reply.get("error_message") or message,
                    "raw_message": message,
                }
            return {
                "ok": bool(reply.get("ok")),
                "success": bool(reply.get("ok")),
                "error": error,
                "stage": stage,
                "messages": [message],
                "workspace": {"关节位置": [str(j) for j in (reply.get("joints") or [])]},
                "joints": reply.get("joints"),
                "last_action": self.last_action,
            }
        except Exception as exc:
            return {
                "ok": False,
                "success": False,
                "error": str(exc),
                "stage": "socket",
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

    def query_error(self):
        """主动读取控制器最近一次机器人错误（RAPID ERRINFO）。

        返回: {"ok", "error_code", "error_message", "message"}
        通信失败时不抛异常，返回 ok=False。
        """
        try:
            self.client.connect()
            return self.client.send_action({"action": "query_error"})
        except Exception as exc:
            return {
                "ok": False,
                "message": f"查询控制器错误失败: {exc}",
                "error_code": None,
                "error_message": None,
            }

    def recover_error(self, error_code=None):
        """针对停止级错误尝试恢复（V6.6 RecoveryManager 调用）。

        恢复流程：
          1. 关闭旧连接（并释放 Mock 服务端）；
          2. 重建客户端并重新连接（Mock 环境模拟 RAPID 重启后重新监听）；
          3. 返回恢复结果。

        注意：真实 RobotStudio 停止级错误（如 50050）会导致 RAPID 程序
        停止，Python 侧无法直接重启虚拟控制器中的 RAPID 任务；本方法在
        真实环境下会尝试重连，若服务端已停止则返回 recover=False，
        需要外部（人工或 RobotStudio API）重启 RAPID。
        """
        try:
            self.client.close()
            self.client = self._build_client()
            self.client.connect()
            return {
                "recover": True,
                "message": "rapid restarted and socket reconnected",
                "error_code": error_code,
            }
        except Exception as exc:
            return {
                "recover": False,
                "message": f"恢复失败: {exc}",
                "error_code": error_code,
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
