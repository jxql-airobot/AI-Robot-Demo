# -*- coding: utf-8 -*-
"""
plan_schema.py — Plan 数据结构 (V5.2)
=====================================
可解释任务规划的统一结构：
  task_analysis / goal / steps / current_state
"""


def normalize_plan(data):
    """把任意 dict 规范成标准 Plan 结构，字段缺失时给默认值"""
    if not isinstance(data, dict):
        data = {}
    plan = {
        "task_analysis": str(data.get("task_analysis", "")),
        "goal": str(data.get("goal", "")),
        "current_state": str(data.get("current_state", "未知")),
        "steps": [],
    }
    for step in data.get("steps", []):
        if isinstance(step, dict) and step.get("tool"):
            plan["steps"].append(
                {
                    "tool": str(step["tool"]),
                    "args": step.get("args", {}) or {},
                    "purpose": str(step.get("purpose", "")),
                }
            )
    return plan


def error_plan(reason, current_state="未知"):
    """无法理解任务时返回的 Plan"""
    return {
        "task_analysis": reason,
        "goal": "无法执行",
        "steps": [],
        "current_state": current_state,
    }
