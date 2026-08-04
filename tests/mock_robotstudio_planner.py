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
    """离线规划器：Home / 关节移动 / 直线移动"""

    def plan(self, task, context, memory_text=""):
        text = task
        current_state = context.current_state or "未知"

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
                            "target": [0.5, 0.0, 0.5, 0.0, 0.0, 0.0],
                        },
                        "purpose": "直线移动到指定点",
                    }
                ],
                "current_state": current_state,
            }
        if "移动" in text or "指定点" in text or "关节" in text or "位置" in text:
            return {
                "task_analysis": "用户要求机器人移动到指定关节位置",
                "goal": "移动到指定点",
                "steps": [
                    {
                        "tool": "robot_tool",
                        "args": {
                            "action": "joint_move",
                            "joints": [10.0, 20.0, 30.0, 0.0, 0.0, 0.0],
                        },
                        "purpose": "移动到指定关节位置",
                    }
                ],
                "current_state": current_state,
            }
        return error_plan(f"无法理解 RobotStudio 任务: {task}", current_state=current_state)
