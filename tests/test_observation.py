# -*- coding: utf-8 -*-
"""test_observation.py — Observation 模块测试 (V6.4)"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.observation import ObservationManager  # noqa: E402


def _ok_result(step=1, tool="robot_tool", message="ok", workspace=None):
    return {
        "step": step,
        "tool": tool,
        "ok": True,
        "message": message,
        "result": {"workspace": workspace or {"成品区": ["蓝色零件"]}},
    }


def test_all_success():
    obs = ObservationManager().get_observation(
        step_results=[_ok_result(1), _ok_result(2)]
    )
    assert obs["success"] is True
    assert obs["status"] == "completed"
    assert obs["need_replan"] is False
    assert obs["error"] is None


def test_has_failure():
    results = [
        _ok_result(1),
        {"step": 2, "tool": "robot_tool", "ok": False,
         "message": "MOVEJ failed", "result": None},
    ]
    obs = ObservationManager().get_observation(step_results=results)
    assert obs["success"] is False
    assert obs["status"] == "failed"
    assert obs["need_replan"] is True
    assert "MOVEJ failed" in (obs["error"] or "")


def test_empty_results_fails():
    obs = ObservationManager().get_observation(step_results=[])
    assert obs["success"] is False
    assert obs["status"] == "failed"


def test_robot_state_extracted():
    obs = ObservationManager().get_observation(
        step_results=[_ok_result(1, workspace={"成品区": ["蓝色零件"]})]
    )
    assert obs["robot_state"]["workspace"]["成品区"] == ["蓝色零件"]


if __name__ == "__main__":
    test_all_success()
    test_has_failure()
    test_empty_results_fails()
    test_robot_state_extracted()
    print("test_observation PASSED")

