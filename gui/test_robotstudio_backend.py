#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_robotstudio_backend.py — GUI 后端 RobotStudio 模式测试 (V6.0)
=================================================================
验证 Ros2Backend(robot_backend="robotstudio")：Mock 闭环，
对话可执行「回到Home位置」并读取关节状态。

用法（WSL）：
    python3 gui/test_robotstudio_backend.py
"""

import os
import sys

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(GUI_DIR)
for p in (GUI_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.planner import MockPlanPlanner  # noqa: E402
from backend import Ros2Backend  # noqa: E402


def main():
    backend = Ros2Backend(planner=MockPlanPlanner(), robot_backend="robotstudio")
    resp = backend.handle_task("回到Home位置")

    assert resp["plan"]["steps"], "回 Home 计划为空"
    assert any(r.get("ok") for r in resp["step_results"]), "回 Home 执行失败"
    print(f"目标：{resp['plan']['goal']}")
    print(f"执行结果：{resp['step_results'][0]['message']}")

    odom = backend.get_odom()
    assert odom and odom[0].get("joints") is not None, "未读取到关节状态"
    print(f"关节位置：{odom[0]['joints']}")

    backend.close()
    print("test_robotstudio_backend 通过")


if __name__ == "__main__":
    main()
