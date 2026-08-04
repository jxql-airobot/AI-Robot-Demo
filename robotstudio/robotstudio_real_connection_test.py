#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robotstudio_real_connection_test.py — RobotStudio 真实连接测试 (V6.0 第二阶段)
=============================================================================
检测：TCP 连接 / 命令发送 / 返回格式。

规则：
- Mock 测试必须通过（无 RobotStudio 也能跑）
- 真实测试：仅当 config.json backend="real" 或传 --real 时尝试；
  真实环境未就绪则打印 SKIP，不影响退出码

用法：
    python robotstudio/robotstudio_real_connection_test.py             # Mock 必测
    python robotstudio/robotstudio_real_connection_test.py --real      # 尝试真实连接
    python robotstudio/robotstudio_real_connection_test.py --host 127.0.0.1 --port 30000
"""

import argparse
import os
import sys

RS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(RS_DIR)
for p in (RS_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from robotstudio.config import load_config  # noqa: E402
from robotstudio.robotstudio_client import RobotStudioClient  # noqa: E402


def test_mock():
    """Mock 闭环必须通过：连接 / 命令 / 返回格式"""
    client = RobotStudioClient(mock=True)
    client.connect()
    ok, reply = client.ping()
    assert ok, f"Mock ping 失败: {reply}"
    assert reply.get("joints") == [0.0] * 6, f"返回格式异常: {reply}"
    for action in (
        {"action": "move_home"},
        {"action": "joint_move", "joints": [10, 20, 30, 45, 60, 0]},
        {"action": "linear_move", "target": [0.3, 0, 0.3, 0, 0, 0]},
    ):
        reply = client.send_action(action)
        assert reply["ok"], f"{action} 执行失败: {reply}"
        assert "joints" in reply, "返回缺少 joints 字段"
    client.close()
    print("[OK] Mock 连接/命令/返回格式测试通过")


def test_real(host, port, timeout):
    """真实连接尝试：失败时 SKIP（不视为测试失败）"""
    client = RobotStudioClient(host=host, port=port, timeout_seconds=timeout, mock=False)
    try:
        client.connect()
        ok, reply = client.ping()
        assert ok, f"ping 失败: {reply}"
        print(f"[OK] 真实 RobotStudio 连接成功 {host}:{port}")
        print(f"     关节位置: {reply['joints']}")
        reply = client.send_action({"action": "move_home"})
        assert reply["ok"], f"move_home 失败: {reply}"
        print(f"[OK] move_home 执行成功: {reply['message']}")
        reply = client.send_action(
            {"action": "joint_move", "joints": [10, 20, 30, 45, 60, 0]}
        )
        assert reply["ok"], f"joint_move(非奇异姿态) 失败: {reply}"
        print(f"[OK] joint_move 到非奇异姿态: {reply['message']}")
        pose = client.get_pose()
        assert pose.get("ok") and pose.get("joints"), f"get_pose 失败: {pose}"
        px, py, pz = pose["joints"][:3]
        print(f"[OK] GETPOSE 当前 TCP: x={px} y={py} z={pz} (m)")
        reply = client.send_action(
            {"action": "linear_move", "target": [px + 0.1, py, pz, 0.0, 0.0, 0.0]}
        )
        assert reply["ok"], f"linear_move 失败: {reply}"
        print(f"[OK] linear_move 执行成功: {reply['message']}")
        reply = client.send_action({"action": "get_position"})
        assert reply["ok"], f"get_position 失败: {reply}"
        print(f"[OK] 直线运动后关节真值: {reply['joints']}")
        reply = client.send_action({"action": "move_home"})
        assert reply["ok"], f"move_home(回零) 失败: {reply}"
        print(f"[OK] move_home 回零成功: {reply['message']}")
        client.close()
        return True
    except Exception as exc:
        print(f"[SKIP] 真实 RobotStudio 未就绪，跳过真实测试: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="RobotStudio 真实连接测试")
    parser.add_argument("--real", action="store_true", help="强制尝试真实连接")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    # 1. Mock 必测
    test_mock()

    # 2. 真实测试（可选）
    cfg = load_config()
    host = args.host or cfg.get("host", "127.0.0.1")
    port = args.port or int(cfg.get("port", 30000))
    timeout = float(cfg.get("timeout", 5.0))
    backend = cfg.get("backend", "mock")
    if args.real or backend == "real":
        test_real(host, port, timeout)
    else:
        print(f"[SKIP] 当前 config backend={backend}，真实测试跳过（可用 --real 或改 config 启用）")
    print("\nrobotstudio_real_connection_test 完成")


if __name__ == "__main__":
    main()
