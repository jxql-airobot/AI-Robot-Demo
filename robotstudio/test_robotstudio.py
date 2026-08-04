#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_robotstudio.py — RobotStudio 模块测试 (V6.0)
==================================================
Mock 模式闭环测试：命令构造 -> TCP 客户端 -> Mock 服务端 -> 回复解析。
不依赖 RobotStudio / RobotWare。

用法：
    python robotstudio/test_robotstudio.py
"""

import os
import sys

RS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(RS_DIR)
for p in (RS_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from robotstudio.command_schema import build_command, parse_reply  # noqa: E402
from robotstudio.mock_robotstudio import MockRobotStudioServer  # noqa: E402
from robotstudio.robotstudio_client import RobotStudioClient  # noqa: E402


def test_schema():
    assert build_command({"action": "move_home"}) == "HOME\n"
    assert build_command({"action": "joint_move", "joints": [1, 2, 3, 4, 5, 6]}) == (
        "MOVEJ 1.0,2.0,3.0,4.0,5.0,6.0\n"
    )
    assert build_command({"action": "get_position"}) == "GETPOS\n"
    ok = parse_reply("OK 0.0,0.0,0.0,0.0,0.0,0.0")
    assert ok["ok"] and ok["joints"] == [0.0] * 6
    err = parse_reply("ERROR 未知命令: XXX")
    assert not err["ok"] and "未知命令" in err["message"]
    print("[OK] command_schema 测试通过")


def test_client_mock_loop():
    client = RobotStudioClient(mock=True)
    client.connect()
    assert client.connected

    reply = client.send_action({"action": "move_home"})
    assert reply["ok"], reply
    assert reply["joints"] == [0.0] * 6

    reply = client.send_action({"action": "joint_move", "joints": [10, 20, 30, 0, 0, 0]})
    assert reply["ok"], reply
    assert reply["joints"] == [10.0, 20.0, 30.0, 0.0, 0.0, 0.0]

    reply = client.get_position()
    assert reply["ok"] and reply["joints"] == [10.0, 20.0, 30.0, 0.0, 0.0, 0.0]
    client.close()
    assert not client.connected
    print("[OK] 客户端 + Mock 服务端闭环测试通过")


def test_backend():
    from agent.tools.robotstudio_tool import RobotStudioBackend

    backend = RobotStudioBackend()
    out = backend.execute({"action": "move_home"})
    assert out["ok"], out
    assert out["joints"] == [0.0] * 6
    state = backend.get_state()
    assert state["connected"] and state["joints"] == [0.0] * 6
    backend.close()
    print("[OK] RobotStudioBackend 测试通过")


def main():
    test_schema()
    test_client_mock_loop()
    test_backend()
    print("\ntest_robotstudio 全部通过")


if __name__ == "__main__":
    main()
