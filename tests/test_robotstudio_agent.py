#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_robotstudio_agent.py — RobotStudio Agent 集成测试（迁移自并行实现）
=======================================================================
验证保留架构：Agent(backend="robotstudio") -> robot_tool(RobotStudioBackend)
-> Mock 服务端全链路。由 agent/test_agent_robotstudio.py 迁移并适配。

用法：
    python tests/test_robotstudio_agent.py
"""

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (REPO_ROOT, TESTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from mock_robotstudio_planner import RobotStudioMockPlanner  # noqa: E402


def main():
    tmp_dir = tempfile.mkdtemp(prefix="rs_agent_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    agent = Agent(backend="robotstudio", db_path=db_path, planner=RobotStudioMockPlanner())

    assert "robot_tool" in agent.registry, "缺少 robot_tool"
    cases = [
        ("回到Home位置", "move_home"),
        ("移动机器人到指定点", "joint_move"),
        ("执行直线移动到目标点", "linear_move"),
    ]
    for task, action in cases:
        resp = agent.handle(task)
        steps = resp["plan"].get("steps", [])
        assert steps and steps[0]["tool"] == "robot_tool", f"{task} 未规划 robot_tool"
        assert steps[0]["args"]["action"] == action, f"{task} 动作不匹配: {steps[0]['args']}"
        assert all(r.get("ok") for r in resp["step_results"]), f"{task} 执行失败"
        print(f"[OK] {task} -> {action} -> 执行成功")

    state = agent.registry["robot_tool"].backend.get_state()
    assert state.get("connected"), "Mock 连接状态异常"
    print(f"[OK] 最终状态: 关节={state['joints']} 最后动作={state['last_action']}")
    agent.close()
    print("\ntest_robotstudio_agent 全部通过")


if __name__ == "__main__":
    main()
