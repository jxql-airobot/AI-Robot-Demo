#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_ros2.py — Agent ROS2 集成测试 (V5.2)
================================================
验证 agent 通过 robot_tool 发布 /ai_robot/action 驱动现有 robot_controller，
并收到 /ai_robot/status 回传（V3/V4 节点零修改）。

用法（WSL，仿真系统已启动）：
    python3 agent/test_agent_ros2.py
"""

import os
import sys

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(AGENT_DIR)
for p in (AGENT_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402


def main():
    agent = Agent(backend="ros2", planner=MockPlanPlanner())
    resp = agent.handle("把红色零件移动到检测区")

    print(f"任务分析：{resp['plan'].get('task_analysis', '')}")
    print(f"目标：{resp['plan'].get('goal', '')}")
    print("执行步骤：")
    for index, step in enumerate(resp["plan"].get("steps", []), 1):
        print(f"  {index}. {step.get('purpose', '')}（工具：{step.get('tool')}）")
    print("--- 执行结果 ---")
    for r in resp["step_results"]:
        print(f"[步骤{r.get('step')}][{r.get('tool')}] ok={r.get('ok')} {r.get('message')}")

    assert resp["plan"]["steps"], "生成空步骤"
    assert any(r.get("ok") for r in resp["step_results"]), "机器人动作未成功"
    print(f"当前状态：{resp.get('current_state')}")
    agent.close()
    print("test_agent_ros2 通过")


if __name__ == "__main__":
    main()
