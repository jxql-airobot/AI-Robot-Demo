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
    if act in ("query_error", "get_error"):
        return "ERRINFO\n"
    raise ValueError(f"未知 RobotStudio 动作: {act}")


def _extract_rapid_error(message):
    """从错误消息中提取 (error_code, error_code_name)"""
    import re

    m = re.search(r"(\d{4,5})", message or "")
    code = m.group(1) if m else None
    lower = (message or "").lower()
    for name in ("position_unreachable", "joint_out_of_range", "short_distance",
                 "motion_execution_error"):
        if name in lower:
            return code, name
    if code:
        return code, "motion_execution_error"
    return code, None


def parse_reply(line):
    """解析服务端回复 -> {"ok", "message", "joints", 以及结构化错误字段}"""
    line = (line or "").strip()
    upper = line.upper()
    if upper.startswith("OK"):
        data = line[2:].strip()
        return {"ok": True, "message": data or "执行成功", "joints": _parse_joints(data)}
    if upper.startswith("ERROR_RAPID"):
        code, name = _extract_rapid_error(line)
        return {
            "ok": False,
            "message": f"RAPID error {code} ({name})" if code else line,
            "joints": None,
            "error_code": code,
            "error_type": "execution",
            "error_message": name or "motion_execution_error",
            "stage": "motion",
        }
    if upper.startswith("ERRINFO"):
        parts = line[7:].strip().split()
        errno = parts[0] if parts else "0"
        name = parts[1] if len(parts) > 1 else "none"
        return {
            "ok": True,
            "message": f"最近错误: {name} (error {errno})" if errno != "0" else "无错误",
            "joints": None,
            "error_code": None if errno == "0" else errno,
            "error_type": "execution" if errno != "0" else None,
            "error_message": None if errno == "0" else name,
        }
    if upper.startswith("ERROR"):
        message = line[5:].strip() or "未知错误"
        code, name = _extract_rapid_error(message)
        return {
            "ok": False,
            "message": message,
            "joints": None,
            "error_code": code,
            "error_type": "execution" if code else None,
            "error_message": name,
            "stage": "rapid",
        }
    return {"ok": False, "message": f"无法解析 RobotStudio 回复: {line}", "joints": None}


def _parse_joints(text):
    """从 'j1,j2,...' 解析关节角度列表，失败返回 None"""
    if not text:
        return None
    try:
        return [float(x) for x in text.split(",")]
    except ValueError:
        return None
