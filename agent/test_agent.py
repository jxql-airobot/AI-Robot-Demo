#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent.py — Agent 冒烟测试 (V5.2)
=====================================
本地模式 + Mock 规划器，不依赖 ROS2 和网络。
注意：使用临时数据库，不会污染真实记忆库。
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
    tmp_dir = tempfile.mkdtemp(prefix="agent_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    agent = Agent(backend="local", db_path=db_path, planner=MockPlanPlanner())

    tasks = [
        "扫描工作台",
        "红色零件在哪里",
        "把红色零件移动到检测区",
        "记住：A区域在生产线左侧",
    ]
    for task in tasks:
        resp = agent.handle(task)
        assert resp["plan"]["steps"], f"{task} 生成了空步骤"
        assert resp["plan"]["task_analysis"], f"{task} 缺少任务分析"
        print(f"[OK] {task} -> 目标: {resp['plan']['goal']} (步骤 {len(resp['plan']['steps'])} 个)")

    # 指代消解：上一轮操作对象是红色零件
    resp2 = agent.handle("把那个零件放到成品区")
    goal = resp2["plan"].get("goal", "")
    assert "红色零件" in goal, f"指代消解失败: {goal}"
    print(f"[OK] 指代消解 -> 目标: {goal}")

    # 多轮上下文
    resp3 = agent.handle("它在哪里")
    assert resp3["plan"].get("task_analysis"), "多轮上下文生成失败"
    print(f"[OK] 多轮上下文 -> {resp3['plan']['task_analysis']}")

    # 无法理解的指令应返回 error Plan
    resp4 = agent.handle("今天天气怎么样")
    assert resp4["plan"]["goal"] == "无法执行", "未返回 error Plan"
    print("[OK] 无法理解指令 -> 返回 error Plan")

    agent.close()
    print("\ntest_agent 全部通过")


if __name__ == "__main__":
    main()
