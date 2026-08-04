# -*- coding: utf-8 -*-
"""
command_schema.py — RobotStudio 统一动作格式 (V6.0)
===================================================
把 Agent 的统一动作 dict 翻译成 RAPID Socket 文本命令，
并解析服务端回复。Mock 与真实 RAPID 共用同一协议。

动作格式：
    {"action": "move_home"}                                    -> HOME
    {"action": "joint_move", "joints": [0,0,0,0,0,0]}          -> MOVEJ j1,...,j6
    {"action": "linear_move", "target": [x,y,z,rx,ry,rz]}       -> MOVEL x,y,z,rx,ry,rz
    {"action": "get_position"}                                  -> GETPOS
    {"action": "get_pose"}                                      -> GETPOSE（x,y,z,rx,ry,rz）
    {"action": "status"}                                        -> STATUS（同 GETPOS，返回当前关节）

回复格式（服务端 -> 客户端）：
    OK j1,j2,j3,j4,j5,j6       成功（附带当前关节角度）
    ERROR <message>            失败
"""


def build_command(action):
    """把动作 dict 转成 RAPID 文本命令（含换行）"""
    act = action.get("action") or action.get("type")
    if act == "move_home":
        return "HOME\n"
    if act == "joint_move":
        joints = action.get("joints", [0.0] * 6)
        text = ",".join(str(float(j)) for j in joints)
        return f"MOVEJ {text}\n"
    if act == "linear_move":
        target = action.get("target", [0.0] * 6)
        if isinstance(target, (list, tuple)):
            text = ",".join(str(float(v)) for v in target)
        else:
            text = str(target)
        return f"MOVEL {text}\n"
    if act in ("get_position", "get_state"):
        return "GETPOS\n"
    if act == "get_pose":
        return "GETPOSE\n"
    if act == "status":
        return "STATUS\n"
    raise ValueError(f"未知 RobotStudio 动作: {act}")


def parse_reply(line):
    """解析服务端回复 -> {"ok": bool, "message": str, "joints": list|None}"""
    line = (line or "").strip()
    upper = line.upper()
    if upper.startswith("OK"):
        data = line[2:].strip()
        return {"ok": True, "message": data or "执行成功", "joints": _parse_joints(data)}
    if upper.startswith("ERROR"):
        return {"ok": False, "message": line[5:].strip() or "未知错误", "joints": None}
    return {"ok": False, "message": f"无法解析 RobotStudio 回复: {line}", "joints": None}


def _parse_joints(text):
    """从 'j1,j2,...' 解析关节角度列表，失败返回 None"""
    if not text:
        return None
    try:
        return [float(x) for x in text.split(",")]
    except ValueError:
        return None
