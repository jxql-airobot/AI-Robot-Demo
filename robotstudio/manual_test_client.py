#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manual_test_client.py — RobotStudio 手动测试客户端 (V6.0 第二阶段)
==================================================================
不经过 Agent，直接测试 Python -> RobotStudio 通信：
HOME / MOVEJ / MOVEL / GETPOS。

用法：
    python robotstudio/manual_test_client.py                # Mock（默认）
    python robotstudio/manual_test_client.py --real         # 真实 RobotStudio
    python robotstudio/manual_test_client.py --host 127.0.0.1 --port 30000
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


def main():
    parser = argparse.ArgumentParser(description="RobotStudio 手动测试客户端")
    parser.add_argument("--real", action="store_true", help="连接真实 RobotStudio")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    cfg = load_config()
    host = args.host or cfg.get("host", "127.0.0.1")
    port = args.port or int(cfg.get("port", 30000))
    timeout = float(cfg.get("timeout", 5.0))
    real = args.real or cfg.get("backend", "mock") == "real"
    mode = "REAL" if real else "MOCK"
    print(f"=== RobotStudio 手动测试（{mode}） {host}:{port} ===")

    client = RobotStudioClient(
        host=host, port=port, timeout_seconds=timeout, mock=not real
    )
    try:
        client.connect()
        print(f"[连接] 成功 {host}:{port}")
    except Exception as exc:
        print(f"[连接] 失败: {exc}")
        sys.exit(1)

    steps = [
        ("GETPOS", {"action": "get_position"}),
        ("HOME", {"action": "move_home"}),
        ("MOVEJ", {"action": "joint_move", "joints": [10, 20, 30, 45, 60, 0]}),
        ("MOVEL", {"action": "linear_move", "target": [0.3, 0.0, 0.3, 0.0, 0.0, 0.0]}),
        ("STATUS", {"action": "status"}),
        ("GETPOS", {"action": "get_position"}),
        ("HOME", {"action": "move_home"}),
    ]
    all_ok = True
    for name, action in steps:
        try:
            reply = client.send_action(action)
            status = "OK" if reply.get("ok") else "ERROR"
            print(f"[{name}] {status}: {reply.get('message')}")
            all_ok = all_ok and reply.get("ok")
        except Exception as exc:
            print(f"[{name}] 异常: {exc}")
            all_ok = False

    client.close()
    print("\n=== 结果:", "全部成功" if all_ok else "存在失败", "===")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
