#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_robotstudio_tool.py — Agent + RobotStudio Mock 集成测试 (V6.0)
==================================================================
验证：用户自然语言 -> Agent 规划 -> robot_tool(RobotStudioBackend)
-> Mock 服务端 -> 返回执行结果。
不依赖 RobotStudio / RobotWare / ROS2。

用法：
    python agent/test_robotstudio_tool.py
"""

import os
import sys
import tempfile

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(AGENT_DIR)
for p in (AGENT_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402


def main():
    tmp_dir = tempfile.mkdtemp(prefix="rs_tool_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    agent = Agent(backend="robotstudio", db_path=db_path, planner=MockPlanPlanner())

    # 1. 回 Home
    resp = agent.handle("回到Home位置")
    assert resp["plan"]["steps"], "回 Home 计划为空"
    assert "home" in resp["plan"]["goal"].lower(), f"回 Home 目标错误: {resp['plan']['goal']}"
    assert any(r.get("ok") for r in resp["step_results"]), "回 Home 执行失败"
    print(f"[OK] 回Home -> {resp['plan']['goal']} | {resp['step_results'][0]['message']}")

    # 2. 移动到指定点（关节位置更新）
    resp2 = agent.handle("移动到点A")
    assert any(r.get("ok") for r in resp2["step_results"]), "移动到点失败"
    print(f"[OK] 移动到点A -> {resp2['step_results'][0]['message']}")

    # 3. 简单搬运动作（多步骤）
    resp3 = agent.handle("执行简单搬运动作")
    assert len(resp3["step_results"]) >= 2, "搬运动作应为多步骤"
    assert all(r.get("ok") for r in resp3["step_results"]), "搬运动作有步骤失败"
    print(f"[OK] 搬运动作 -> {len(resp3['step_results'])} 步全部成功")

    # 4. 状态查询（关节位置）
    state = agent.registry["robot_tool"].backend.get_state()
    assert state["connected"], "Mock 连接状态异常"
    print(f"[OK] 当前关节位置: {state['joints']}")

    agent.close()
    print("\ntest_robotstudio_tool 全部通过")


if __name__ == "__main__":
    main()
