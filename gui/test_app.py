#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_app.py — Streamlit 应用冒烟测试 (V5.1)
===========================================
用 streamlit 官方 AppTest 模拟运行 app.py，捕获运行时异常。

用法（WSL 内，需先 source ROS2 且仿真系统已启动）：
    python3 gui/test_app.py
"""

import os
import sys

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
if GUI_DIR not in sys.path:
    sys.path.insert(0, GUI_DIR)

from streamlit.testing.v1 import AppTest  # noqa: E402


def main():
    app_path = os.path.join(GUI_DIR, "app.py")
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    # 显式关闭后端（含 rclpy 后台线程），保证进程干净退出
    backend = at.session_state["backend"] if "backend" in at.session_state else None
    if backend is not None:
        backend.close()

    print(f"异常数量: {len(at.exception)}")
    for exc in at.exception:
        print(f"  [异常] {exc.value}")
    if at.exception:
        sys.exit(1)
    print("冒烟测试通过：页面渲染无异常")


if __name__ == "__main__":
    main()
