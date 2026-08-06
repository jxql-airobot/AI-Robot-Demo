# -*- coding: utf-8 -*-
"""test_recovery_manager.py — RecoveryManager 错误分级与恢复测试 (V6.6)"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "agent"),
          os.path.join(REPO_ROOT, "robotstudio")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.recovery import ErrorLevel, RecoveryManager  # noqa: E402


def test_50050_restart_rapid():
    error = {
        "error_code": "50050",
        "error_type": "execution",
        "error_message": "position_unreachable",
        "raw_message": "ERROR_RAPID 50050 position_unreachable",
    }
    mgr = RecoveryManager()
    assert mgr.classify(error) == ErrorLevel.LEVEL2
    plan = mgr.analyze(error)
    assert plan["recoverable"] is True
    assert plan["action"] == "restart_rapid"
    assert plan["level"] == 2


def test_normal_error_auto_replan():
    error = {
        "error_code": None,
        "error_type": "action_param",
        "error_message": "动作参数错误：joint_move 需要 6 个关节角",
    }
    mgr = RecoveryManager()
    assert mgr.classify(error) == ErrorLevel.LEVEL1
    plan = mgr.analyze(error)
    assert plan["recoverable"] is True
    assert plan["action"] == "replan"


def test_safety_error_forbids_auto_recovery():
    error = {
        "error_code": None,
        "error_type": "safety",
        "error_message": "急停触发，安全保护生效",
        "raw_message": "emergency stop",
    }
    mgr = RecoveryManager()
    assert mgr.classify(error) == ErrorLevel.LEVEL3
    plan = mgr.analyze(error)
    assert plan["recoverable"] is False
    assert plan["action"] == "manual"
    assert plan["status"] == "need_manual"


def test_socket_recovery_via_backend():
    from agent.tools.robotstudio_tool import RobotStudioBackend

    backend = RobotStudioBackend()
    # 先建立连接
    backend.client.connect()
    assert backend.client.connected
    # 断开后通过 recover_error 重建连接
    backend.client.close()
    assert not backend.client.connected
    mgr = RecoveryManager(backend=backend)
    plan = mgr.recover({"error_code": "50050", "error_type": "execution"})
    assert plan["recoverable"] is True
    assert plan["status"] == "success"
    assert backend.client.connected
    backend.close()


if __name__ == "__main__":
    test_50050_restart_rapid()
    test_normal_error_auto_replan()
    test_safety_error_forbids_auto_recovery()
    test_socket_recovery_via_backend()
    print("test_recovery_manager PASSED")

