#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_backend.py — GUI 后端 + Agent 集成测试 (V5.2)
========================================================
验证 Ros2Backend.handle_task 走 Agent（可解释 Plan + 四工具），
复用同一个 ROS2 客户端驱动现有 robot_controller。

用法（WSL，仿真系统已启动）：
    python3 gui/test_agent_backend.py
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
    backend = Ros2Backend(planner=MockPlanPlanner())
    resp = backend.handle_task("把红色零件移动到检测区")

    assert resp["plan"]["steps"], "生成空步骤"
    assert any(r.get("ok") for r in resp["step_results"]), "工具执行未成功"
    print(f"任务分析：{resp['plan'].get('task_analysis', '')}")
    print(f"目标：{resp['plan'].get('goal', '')}")
    for index, step in enumerate(resp["plan"].get("steps", []), 1):
        print(f"  {index}. {step.get('purpose', '')}（工具：{step.get('tool')}）")
    print("--- 执行结果 ---")
    for r in resp["step_results"]:
        print(f"[步骤{r.get('step')}][{r.get('tool')}] ok={r.get('ok')} {r.get('message')}")
    print(f"当前状态：{resp.get('current_state')}")

    backend.close()
    print("test_agent_backend 通过")


if __name__ == "__main__":
    main()
