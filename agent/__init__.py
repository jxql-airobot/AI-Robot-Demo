# -*- coding: utf-8 -*-
"""
agent — AI Robot 智能体层 (V5.2)
================================
新增的独立 Agent 层：
  用户输入 → 任务理解 → 可解释 Plan → 工具调用 → 已有模块执行 → 结果返回

V1-V4 零修改：只读复用 memory.py / robot.py / ROS2 话题。
"""

import os
import sys

# 保证仓库根目录与 gui/ 可被 import（memory.py / ros2_client.py 等）
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(AGENT_DIR)
GUI_DIR = os.path.join(REPO_ROOT, "gui")
for p in (REPO_ROOT, GUI_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.core import Agent  # noqa: E402

__all__ = ["Agent"]
