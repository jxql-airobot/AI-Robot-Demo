# -*- coding: utf-8 -*-
"""
system_info.py — 系统信息页 (V6.3)
===================================
展示项目定位、版本、技术栈与分层架构，对应论文第三章系统设计。
"""

import os

import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_NAME = "AI-Robot-Demo"
VERSION = "v6.2-thesis-stable"
THESIS_TITLE = "基于大语言模型智能体的工业机器人任务规划系统设计与实现"

TECH_STACK = [
    ("LLM", "DeepSeek 大语言模型，自然语言理解与任务生成"),
    ("Agent", "任务理解、拆解、工具调用与上下文管理"),
    ("RAG", "bge-small-zh-v1.5 向量检索 + 工业知识库增强"),
    ("ROS2", "节点通信框架（robot_controller / vision_node / ai_brain）"),
    ("Gazebo", "仿真机器人环境与视觉识别"),
    ("ABB RobotStudio", "IRC5 虚拟控制器 + IRB120 机器人模型"),
    ("RobotWare", "ABB 控制器软件 6.08.1040"),
    ("RAPID", "机器人程序语言，Socket 服务端"),
]

ARCH_TEXT = """User（自然语言任务）
    ↓
LLM Agent（理解 / 拆解 / 工具调用）
    ↓
Planner（任务规划 / 动作契约）
    ↓
Safety（安全约束层）
    ↓
RobotTool（统一工具接口）
    ↓
Backend（后端抽象）
    ↓
Gazebo 仿真  /  ABB RobotStudio（IRC5 + IRB120）"""

MODULES = [
    ("agent/", "LLM Agent 智能层：规划器、执行器、工具与 RAG 记忆"),
    ("agent/rag/", "RAG 语义记忆：Embedding、向量库、混合检索"),
    ("agent/tools/", "工具层：robot_tool / vision_tool / memory_tool / environment_tool"),
    ("robotstudio/", "ABB RobotStudio 通信：TCP Socket + RAPID 服务端"),
    ("ros2_ws/", "ROS2 工作区：机器人控制、视觉节点与仿真模型"),
    ("gui/", "Streamlit 交互界面：任务对话与论文展示层"),
    ("experiments/", "实验框架：任务集、运行脚本、日志与结果"),
    ("docs/thesis/", "毕业论文章节与实验报告"),
]


def render():
    st.subheader("系统信息")

    c1, c2 = st.columns(2)
    c1.metric("项目", PROJECT_NAME)
    c2.metric("版本", VERSION)

    st.markdown("### 论文题目")
    st.info(THESIS_TITLE)

    st.markdown("### 技术栈")
    for name, desc in TECH_STACK:
        st.markdown(f"- **{name}**：{desc}")

    st.markdown("### 系统架构")
    st.code(ARCH_TEXT, language="text")

    st.markdown("### 模块结构")
    for path, desc in MODULES:
        st.markdown(f"- `{path}` — {desc}")

    st.markdown("### 论文对应章节")
    st.markdown(
        "- 第 3 章 系统设计：分层架构、Agent 设计、RAG 设计、软件架构\n"
        "- 第 4 章 系统实现：开发环境、Agent 实现、ABB 通信、后端实现\n"
        "- 第 5 章 实验与结果分析：Agent 规划实验、RAG 增强实验、系统性能测试"
    )

