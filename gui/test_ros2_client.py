#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_ros2_client.py — ROS2 客户端自测脚本 (V5.1)
================================================
用法（WSL 内，需先 source ROS2）：
    python3 gui/test_ros2_client.py

流程：发送一条默认任务 -> 连续打印收到的状态反馈 -> 1.5 秒无新状态后结束。
"""

import os
import sys
import time

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
if GUI_DIR not in sys.path:
    sys.path.insert(0, GUI_DIR)

from ros2_client import Ros2Client  # noqa: E402

QUIET_SECONDS = 1.5
DEADLINE_SECONDS = 20.0


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else "把红色零件移动到检测区"
    client = Ros2Client()
    print(f"[测试] 发送任务: {task}")
    client.send_task(task)

    last = time.time()
    last_seen_ts = None
    deadline = time.time() + DEADLINE_SECONDS
    while time.time() < deadline:
        status = client.get_status()
        if status and status[1] != last_seen_ts:
            print(f"[状态] {status[0]}")
            last_seen_ts = status[1]
            last = time.time()
        if time.time() - last > QUIET_SECONDS:
            break
        time.sleep(0.1)

    client.close()
    print("[测试] 完成")


if __name__ == "__main__":
    main()
