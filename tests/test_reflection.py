# -*- coding: utf-8 -*-
"""test_reflection.py — Reflection 模块测试 (V6.4)"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.reflection import ReflectionAnalyzer  # noqa: E402


def _failed_step(message):
    return {"step": 1, "tool": "robot_tool", "ok": False, "message": message,
            "result": None}


def test_success():
    r = ReflectionAnalyzer().analyze(
        task="移动零件",
        step_results=[{"step": 1, "tool": "robot_tool", "ok": True,
                       "message": "ok", "result": None}],
        observation={"success": True, "status": "completed"},
    )
    assert r["task_completed"] is True
    assert r["need_replan"] is False


def test_execution_failure():
    r = ReflectionAnalyzer().analyze(
        task="移动零件",
        step_results=[_failed_step("执行失败: 50050 位置超出范围")],
        observation={"success": False, "status": "failed", "error": "执行失败"},
    )
    assert r["task_completed"] is False
    assert r["need_replan"] is True
    assert r["error_type"] == "action_param"
    assert "50050" in r["reason"]


def test_communication_failure():
    r = ReflectionAnalyzer().analyze(
        task="移动零件",
        step_results=[_failed_step("RobotStudio 执行异常: 连接超时")],
        observation={"success": False, "status": "failed",
                     "error": "连接超时"},
    )
    assert r["error_type"] == "communication"


def test_unknown_failure():
    r = ReflectionAnalyzer().analyze(
        task="移动零件",
        step_results=[_failed_step("动作执行完成: move")],
        observation={"success": False, "status": "failed"},
    )
    assert r["error_type"] == "execution"


if __name__ == "__main__":
    test_success()
    test_execution_failure()
    test_communication_failure()
    test_unknown_failure()
    print("test_reflection PASSED")

