# -*- coding: utf-8 -*-
"""
mock_robotstudio_planner.py — RobotStudio 离线规划器（测试用途）
==============================================================
由 robotstudio/mock_planner.py 迁移而来（V6.0 并行实现清理），
适配保留的 Backend 插件架构：动作通过 robot_tool 执行
（RobotStudioBackend 是 robot_tool 的第三种后端）。

仅用于离线测试，不作为正式运行模块。
"""

from agent.plan_schema import error_plan


class RobotStudioMockPlanner:
    """离线规划器：Home / 关节移动 / 直线移动 / 状态 / 视觉 / 记忆搬运

    覆盖 RobotStudio 实验基准（experiments/task_set_robotstudio.json）的
    四类任务：基础运动、Agent 规划、视觉、记忆。
    """

    def plan(self, task, context, memory_text=""):
        text = task
        current_state = context.current_state or "未知"

        # 记住指令 -> 写入记忆
        if text.startswith("记住") or text.startswith("记忆"):
            body = text[2:].lstrip("：:，, ")
            for sep in ("=", "是", "在", "位于"):
                if sep in body:
                    topic, content = body.split(sep, 1)
                    topic = topic.strip()
                    content = content.strip()
                    if topic and content:
                        return {
                            "task_analysis": "用户希望保存一条记忆",
                            "goal": f"保存记忆: {topic} -> {content}",
                            "steps": [
                                {
                                    "tool": "memory_tool",
                                    "args": {
                                        "write": {
                                            "topic": topic,
                                            "content": content,
                                            "category": "物体信息",
                                        }
                                    },
                                    "purpose": f"保存新记忆 {topic}",
                                }
                            ],
                            "current_state": current_state,
                        }

        # 视觉/查找任务
        if "找到" in text or "哪里" in text or "找" in text or "看见" in text:
            steps = [
                {
                    "tool": "vision_tool",
                    "args": {"scan": True},
                    "purpose": "扫描视觉识别结果，定位目标",
                }
            ]
            if "零件" in text:
                steps.append(
                    {
                        "tool": "environment_tool",
                        "args": {"status": True},
                        "purpose": "核对工作台/零件状态",
                    }
                )
            return {
                "task_analysis": "用户要求查找目标位置",
                "goal": "定位目标位置",
                "steps": steps,
                "current_state": current_state,
            }

        if "回家" in text or "home" in text.lower():
            return {
                "task_analysis": "用户要求机器人回到 Home 位置",
                "goal": "机器人回到 Home 位置",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {"action": "move_home"},
                        "purpose": "回到 Home 位置",
                    }
                ],
                "current_state": current_state,
            }
        if "直线" in text or "linear" in text.lower():
            return {
                "task_analysis": "用户要求机器人直线移动到目标点",
                "goal": "直线移动到指定点",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {
                            "action": "linear_move",
                            "target": [0.3, 0.0, 0.3, 0.0, 0.0, 0.0],
                        },
                        "purpose": "直线移动到指定点",
                    }
                ],
                "current_state": current_state,
            }
        if "读取" in text or "状态" in text or "当前" in text:
            return {
                "task_analysis": "用户要求读取机器人当前状态",
                "goal": "读取机器人当前状态（关节真值）",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {"action": "get_position"},
                        "purpose": "读取当前关节位置（CJointT 真值）",
                    }
                ],
                "current_state": current_state,
            }
        # 记忆驱动的搬运：任务含零件名 + 移动 -> 用记忆定位后执行直线搬运
        parts = ["红色零件", "蓝色零件", "绿色零件"]
        part = next((p for p in parts if p in text), None)
        if part and ("移动" in text or "搬运" in text or "送" in text):
            location = ""
            for line in memory_text.splitlines():
                if part in line and "：" in line:
                    location = line.split("：", 1)[1].split("（")[0].strip()
                    break
            return {
                "task_analysis": f"用户要求搬运 {part}（基于记忆定位）",
                "goal": f"把 {part} 移动到目标位置（记忆：{location or '未知'}）",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {
                            "action": "linear_move",
                            "target": [0.3, 0.0, 0.3, 0.0, 0.0, 0.0],
                        },
                        "purpose": f"执行 MoveL 搬运 {part} 到目标位姿",
                    }
                ],
                "current_state": current_state,
            }
        if "移动" in text or "指定点" in text or "关节" in text or "位置" in text or "区域" in text:
            return {
                "task_analysis": "用户要求机器人移动到指定关节位置",
                "goal": "移动到指定点",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {
                            "action": "joint_move",
                            "joints": [10.0, 20.0, 30.0, 45.0, 60.0, 0.0],
                        },
                        "purpose": "移动到指定关节位置",
                    }
                ],
                "current_state": current_state,
            }
        return error_plan(f"无法理解 RobotStudio 任务: {task}", current_state=current_state)
