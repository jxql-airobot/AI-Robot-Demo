# -*- coding: utf-8 -*-
"""
test_app_tabs.py — GUI 集成测试 (V6.3)
=======================================
用 Streamlit AppTest 实际执行 gui/app.py，验证：
  - 页面无异常
  - 8 个 tab 全部渲染（原有 5 + 新增 3）

用法（WSL，需 ROS2 环境已 source）：
    source /opt/ros/humble/setup.bash
    source ~/ros2_ws/install/setup.bash
    python3 tests/test_app_tabs.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_DIR = os.path.join(REPO_ROOT, "gui")
for p in (REPO_ROOT, GUI_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit.testing.v1 import AppTest  # noqa: E402


def main():
    at = AppTest.from_file(os.path.join(GUI_DIR, "app.py"), default_timeout=180)
    at.run()
    if at.exception:
        for exc in at.exception:
            print("APP EXCEPTION:", exc.value)
        raise SystemExit(1)
    tabs = at.tabs
    print(f"tabs 数量: {len(tabs)}")
    for i, tab in enumerate(tabs, 1):
        print(f"  tab{i}: {tab.label}")
    assert len(tabs) == 8, f"期望 8 个 tab，实际 {len(tabs)}"
    print("APP TABS TEST PASSED")


if __name__ == "__main__":
    main()
