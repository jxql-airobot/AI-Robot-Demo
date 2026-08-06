# -*- coding: utf-8 -*-
"""test_agent_loop.py — 闭环 Agent 执行循环测试 (V6.4)

覆盖：
  1. 成功执行（1 轮完成）
  2. Safety 拒绝非法动作后重新规划（≥2 轮完成）
  3. 后端执行失败后重新规划（≥2 轮完成）
  4. 持续失败达到 max_rounds（未完成，不崩溃）
"""

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402


VALID_PLAN = {
    "task_analysis": "移动机器人",
    "goal": "移动到指定关节位置",
    "current_state": "未知",
    "steps": [
        {
            "tool": "robot_tool",
            "args": {"action": "joint_move", "joints": [10, 20, 30, 45, 60, 0]},
            "purpose": "移动到指定关节位置",
        }
    ],
}

INVALID_PLAN = {
    "task_analysis": "移动机器人",
    "goal": "移动到指定关节位置",
    "current_state": "未知",
    "steps": [
        {
            "tool": "robot_tool",
            "args": {"action": "joint_move", "joints": [10, 20]},
            "purpose": "移动到指定关节位置",
        }
    ],
}


class FakePlanner:
    """按顺序返回预设计划的规划器"""

    def __init__(self, plan_sequence):
        self.plan_sequence = plan_sequence
        self.calls = 0

    def plan(self, task, context, memory_text=""):
        plan = self.plan_sequence[min(self.calls, len(self.plan_sequence) - 1)]
        self.calls += 1
        return plan


class SocketFailBackend:
    """第一次执行返回通信异常，之后正常"""

    def __init__(self):
        self.calls = 0

    def execute(self, action):
        self.calls += 1
        if self.calls == 1:
            return {
                "ok": False,
                "success": False,
                "error": "socket timeout",
                "stage": "socket",
                "messages": ["RobotStudio 执行异常: 连接超时"],
                "workspace": None,
                "joints": None,
            }
        return {
            "ok": True,
            "success": True,
            "error": "",
            "stage": "ok",
            "messages": ["ok"],
            "workspace": {"关节位置": ["10", "20", "30", "45", "60", "0"]},
            "joints": [10, 20, 30, 45, 60, 0],
        }

    def get_state(self):
        return {"workspace": None}


def _make_agent(planner):
    tmp = tempfile.mkdtemp(prefix="loop_test_")
    return Agent(
        backend="local",
        db_path=os.path.join(tmp, "test.db"),
        planner=planner,
        rag_enabled=False,
        closed_loop=True,
    )


def test_success_one_round():
    agent = _make_agent(FakePlanner([VALID_PLAN]))
    resp = agent.handle_closed_loop("移动机器人到指定点", max_rounds=3)
    assert resp["closed_loop"]["finished"] is True
    assert resp["closed_loop"]["task_completed"] is True
    assert len(resp["closed_loop"]["rounds"]) == 1
    agent.close()


def test_safety_reject_then_replan():
    agent = _make_agent(FakePlanner([INVALID_PLAN, VALID_PLAN]))
    resp = agent.handle_closed_loop("移动机器人到指定点", max_rounds=3)
    rounds = resp["closed_loop"]["rounds"]
    assert len(rounds) == 2
    assert resp["closed_loop"]["finished"] is True
    # 第一轮应包含 Safety 拒绝的失败步骤
    first_msgs = [r.get("message") for r in rounds[0]["step_results"]]
    assert any("Safety 拒绝" in m for m in first_msgs)
    agent.close()


def test_backend_failure_then_replan():
    agent = _make_agent(FakePlanner([VALID_PLAN, VALID_PLAN]))
    agent.registry["robot_tool"].backend = SocketFailBackend()
    resp = agent.handle_closed_loop("移动机器人到指定点", max_rounds=3)
    rounds = resp["closed_loop"]["rounds"]
    assert len(rounds) == 2
    assert rounds[0]["reflection"]["error_type"] == "communication"
    assert resp["closed_loop"]["finished"] is True
    agent.close()


def test_max_rounds_exhausted():
    agent = _make_agent(FakePlanner([INVALID_PLAN, INVALID_PLAN, INVALID_PLAN]))
    resp = agent.handle_closed_loop("移动机器人到指定点", max_rounds=3)
    assert len(resp["closed_loop"]["rounds"]) == 3
    assert resp["closed_loop"]["finished"] is False
    assert resp["closed_loop"]["task_completed"] is False
    agent.close()


if __name__ == "__main__":
    test_success_one_round()
    test_safety_reject_then_replan()
    test_backend_failure_then_replan()
    test_max_rounds_exhausted()
    print("test_agent_loop PASSED")

