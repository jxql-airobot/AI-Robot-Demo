#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — AI Robot Agent GUI 主入口 (V5.1)
=========================================
Streamlit 单页应用：
  - 任务对话区
  - 工作台状态区
  - 记忆查看区
  - 视觉感知区
  - 机器人状态区

【骨架阶段】完整界面在第三步实现。
"""

import os
import sys

# 保证 gui/ 与项目根目录都能被 import
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(GUI_DIR)
for p in (GUI_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="AI Robot Agent V5.1", page_icon="🤖", layout="wide")

st.title("AI Robot Agent V5.1")
st.info("GUI 骨架已就绪 — 完整界面在第三步实现。")
