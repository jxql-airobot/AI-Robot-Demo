# -*- coding: utf-8 -*-
"""test_robot_error_feedback.py — 真实机器人错误反馈闭环测试 (V6.5)

验证 RAPID 结构化错误 -> parse_reply -> Observation -> Reflection 链路：
  1. RAPID 50050 错误被解析为结构化 error；
  2. Observation 正确提取 error_code / error_source / raw_message；
  3. Reflection 识别 robot_unreachable 并触发重规划；
  4. MOVEJ 成功流程不受影响。
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "agent"),
          os.path.join(REPO_ROOT, "robotstudio")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.observation import ObservationManager  # noqa: E402
from agent.reflection import ReflectionAnalyzer  # noqa: E402
from robotstudio.command_schema import parse_reply  # noqa: E402


def test_parse_rapid_50050():
    reply = parse_reply("ERROR_RAPID 50050 position_unreachable")
    assert reply["ok"] is False
    assert reply["error_code"] == "50050"
    assert reply["error_type"] == "execution"
    assert reply["error_message"] == "position_unreachable"
    assert reply["stage"] == "motion"


def test_parse_ok_unchanged():
    reply = parse_reply("OK 10.0,20.0,30.0,45.0,60.0,0.0")
    assert reply["ok"] is True
    assert reply["joints"] == [10.0, 20.0, 30.0, 45.0, 60.0, 0.0]
    assert "error_code" not in reply or reply["error_code"] is None


def test_parse_errinfo_none():
    reply = parse_reply("ERRINFO 0 none")
    assert reply["ok"] is True
    assert reply["error_code"] is None
    assert "无错误" in reply["message"]


def test_parse_errinfo_error():
    reply = parse_reply("ERRINFO 50050 position_unreachable")
    assert reply["ok"] is True
    assert reply["error_code"] == "50050"
    assert reply["error_message"] == "position_unreachable"


def test_observation_extracts_error():
    step_results = [
        {
            "step": 1,
            "tool": "robot_tool",
            "ok": False,
            "message": "RAPID error 50050 (position_unreachable)",
            "result": {
                "workspace": None,
                "error": {
                    "code": "50050",
                    "type": "execution",
                    "message": "position_unreachable",
                    "raw_message": "RAPID error 50050 (position_unreachable)",
                },
                "stage": "motion",
            },
        }
    ]
    obs = ObservationManager().get_observation(step_results=step_results)
    assert obs["success"] is False
    assert obs["error_code"] == "50050"
    assert obs["error_source"] == "RobotStudio"
    assert "position_unreachable" in (obs["raw_message"] or "")
    assert obs["need_replan"] is True


def test_reflection_50050_replan():
    obs = {
        "success": False,
        "status": "failed",
        "error_code": "50050",
        "error_source": "RobotStudio",
        "raw_message": "RAPID error 50050 (position_unreachable)",
    }
    r = ReflectionAnalyzer().analyze(
        task="直线运动到目标点",
        step_results=[{"step": 1, "tool": "robot_tool", "ok": False,
                       "message": "RAPID error 50050", "result": None}],
        observation=obs,
    )
    assert r["task_completed"] is False
    assert r["need_replan"] is True
    assert r["error_type"] == "execution"
    assert "robot_unreachable" in r["reason"]


def test_reflection_socket_error_classified_communication():
    r = ReflectionAnalyzer().analyze(
        task="读取状态",
        step_results=[{"step": 1, "tool": "robot_tool", "ok": False,
                       "message": "socket_error", "result": None}],
        observation={
            "success": False,
            "status": "failed",
            "error_code": "41595",
            "error_source": "RobotStudio",
            "raw_message": "socket_error",
        },
    )
    assert r["need_replan"] is True
    assert r["error_type"] == "communication"
    assert "socket_error" in r["reason"]


def test_success_path_unaffected():
    step_results = [
        {"step": 1, "tool": "robot_tool", "ok": True,
         "message": "10.0,20.0,30.0,45.0,60.0,0.0",
         "result": {"workspace": {"关节位置": ["10", "20", "30", "45", "60", "0"]}}}
    ]
    obs = ObservationManager().get_observation(step_results=step_results)
    assert obs["success"] is True
    assert obs["need_replan"] is False
    r = ReflectionAnalyzer().analyze(
        task="移动机器人到指定点", step_results=step_results, observation=obs
    )
    assert r["task_completed"] is True
    assert r["need_replan"] is False


def test_query_error_via_mock_backend():
    from agent.tools.robotstudio_tool import RobotStudioBackend
    from robotstudio.mock_robotstudio import MockRobotStudioServer
    from robotstudio.robotstudio_client import RobotStudioClient

    server = MockRobotStudioServer(port=0)
    port = server.start()
    try:
        client = RobotStudioClient(
            host="127.0.0.1", port=port, timeout_seconds=5.0, mock=False
        )
        backend = RobotStudioBackend(client=client)
        # 无错误时查询
        reply = backend.query_error()
        assert reply["ok"] is True
        assert reply["error_code"] is None
        # 模拟一次 MOVEL 50050 后查询
        server.fail_next = (50050, "position_unreachable")
        exec_result = backend.execute({"action": "linear_move", "target": [1, 1, 1, 0, 0, 0]})
        assert exec_result["ok"] is False
        assert exec_result["error"]["code"] == "50050"
        reply2 = backend.query_error()
        assert reply2["error_code"] == "50050"
        assert reply2["error_message"] == "position_unreachable"
        client.close()
    finally:
        server.stop()


if __name__ == "__main__":
    test_parse_rapid_50050()
    test_parse_ok_unchanged()
    test_parse_errinfo_none()
    test_parse_errinfo_error()
    test_observation_extracts_error()
    test_reflection_50050_replan()
    test_reflection_socket_error_classified_communication()
    test_success_path_unaffected()
    test_query_error_via_mock_backend()
    print("test_robot_error_feedback PASSED")
