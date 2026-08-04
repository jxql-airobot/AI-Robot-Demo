#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — AI Robot 智能体 GUI 主入口 (V5.1)
==========================================
Streamlit 单页应用（ROS2 模式为主）：
  1. 任务对话区   ：下发自然语言任务，实时展示状态反馈
  2. 工作台状态区 ：解析 /ai_robot/status 成工位表格
  3. 记忆查看区   ：查看/查询 SQLite 记忆（V5.1 只读，不做删除）
  4. 视觉感知区   ：展示最近一次 /ai_robot/vision 识别结果（第一版不做实时视频）
  5. 机器人状态区 ：展示 /odom 位置与速度

界面文字统一在 language.py 管理（V5.1 中文化）。
运行（WSL，需先 source ROS2）：
  python3 -m streamlit run gui/app.py
"""

import json
import os
import sys
import time

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(GUI_DIR)
for p in (GUI_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st  # noqa: E402

from backend import Ros2Backend  # noqa: E402
import language as L  # noqa: E402

st.set_page_config(
    page_title=L.TITLE_WITH_VERSION, page_icon="🤖", layout="wide"
)


# ---------- 工具函数 ----------

def extract_workspace(text):
    """从 '工作台: {json}' 状态文本中提取工位字典，失败返回 None"""
    if "工作台:" not in text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def format_agent_plan(resp):
    """把 AgentResponse 的可解释 Plan 格式化成聊天文本"""
    plan = resp["plan"]
    lines = [
        f"**{L.AGENT_PLAN_TASK_ANALYSIS}**：{plan.get('task_analysis', '')}",
        f"**{L.AGENT_PLAN_GOAL}**：{plan.get('goal', '')}",
        f"**{L.AGENT_PLAN_STEPS}**：",
    ]
    for index, step in enumerate(plan.get("steps", []), 1):
        purpose = step.get("purpose", "")
        tool = step.get("tool", "")
        lines.append(f"{index}. {purpose}（{L.AGENT_PLAN_TOOL}：{tool}）")
    lines.append(f"**{L.AGENT_PLAN_CURRENT_STATE}**：{plan.get('current_state', '')}")
    return "\n".join(lines)


def format_agent_results(resp):
    """把工具执行结果格式化成聊天文本"""
    lines = [f"**{L.AGENT_RESULT_TITLE}**"]
    for r in resp["step_results"]:
        mark = "✅" if r.get("ok") else "❌"
        lines.append(f"{mark} [{r.get('tool')}] {r.get('message', '')}")
    if resp.get("final_message"):
        lines.append(f"**{L.AGENT_FINAL}**：{resp['final_message']}")
    return "\n".join(lines)


# ---------- 侧边栏：模式与连接 ----------

with st.sidebar:
    st.title(L.SIDEBAR_TITLE)
    st.caption(L.SIDEBAR_CAPTION)

    mode_idx = st.radio(L.MODE_LABEL, [L.MODE_ROS2, L.MODE_LOCAL], index=0)
    is_local = mode_idx == 1

    if st.button(L.BUTTON_CONNECT):
        if st.session_state.get("backend"):
            st.session_state["backend"].close()
            st.session_state["backend"] = None

    if is_local:
        if st.session_state.get("backend"):
            st.session_state["backend"].close()
            st.session_state["backend"] = None
        st.info(L.INFO_LOCAL_NOT_AVAILABLE)
        backend = None
    else:
        if st.session_state.get("backend") is None:
            try:
                st.session_state["backend"] = Ros2Backend()
            except Exception as exc:
                st.error(L.ERROR_CONNECT_FAILED.format(error=exc))
                st.caption(L.HINT_CHECK_ENV)
        backend = st.session_state.get("backend")

    if backend:
        mode_name = L.MODE_NAMES.get(backend.name, backend.name)
        st.success(L.STATUS_CONNECTED.format(mode=mode_name))
        st.caption(L.HINT_SIM_REQUIRED)

# ---------- 主界面 ----------

st.title(L.TITLE_WITH_VERSION)
st.caption(L.MAIN_CAPTION)

if backend is None:
    st.stop()

tab_chat, tab_ws, tab_mem, tab_vis, tab_robot = st.tabs(
    [L.TAB_CHAT, L.TAB_WORKSPACE, L.TAB_MEMORY, L.TAB_VISION, L.TAB_ROBOT]
)


# 1) 任务对话区
with tab_chat:
    st.subheader(L.CHAT_SUBHEADER)
    st.caption(L.CHAT_CAPTION)

    if "history" not in st.session_state:
        st.session_state["history"] = []

    with st.expander(L.CHAT_EXAMPLES_TITLE):
        cols = st.columns(len(L.CHAT_EXAMPLE_TASKS))
        for col, ex in zip(cols, L.CHAT_EXAMPLE_TASKS):
            if col.button(ex, key=f"ex_{ex}"):
                st.session_state["pending_task"] = ex

    for role, text in st.session_state["history"]:
        with st.chat_message(role):
            st.markdown(text)

    prompt = st.chat_input(L.CHAT_INPUT_PLACEHOLDER)
    pending = st.session_state.pop("pending_task", None)
    if prompt or pending:
        task = prompt or pending
        st.session_state["history"].append(("user", task))
        with st.chat_message("user"):
            st.markdown(task)
        with st.spinner(L.AGENT_SPINNER):
            resp = backend.handle_task(task)
        plan_text = format_agent_plan(resp)
        st.session_state["history"].append(("assistant", plan_text))
        with st.chat_message("assistant"):
            st.markdown(plan_text)
        if resp["step_results"]:
            result_text = format_agent_results(resp)
            st.session_state["history"].append(("assistant", result_text))
            with st.chat_message("assistant"):
                st.markdown(result_text)


# 2) 工作台状态区
with tab_ws:
    st.subheader(L.WS_SUBHEADER)
    if st.button(L.BUTTON_REFRESH, key="ws_refresh"):
        st.rerun()

    status = backend.get_status()
    if not status:
        st.info(L.WS_NO_DATA)
    else:
        text, ts = status
        st.caption(L.WS_LAST_UPDATE.format(time=time.strftime("%H:%M:%S", time.localtime(ts))))
        ws = extract_workspace(text)
        if ws:
            st.write(L.WS_TABLE_TITLE)
            for station, parts in ws.items():
                left, right = st.columns([1, 3])
                left.markdown(f"**{station}**")
                right.write("、".join(parts) if parts else L.WS_EMPTY)
            with st.expander(L.WS_RAW_EXPANDER):
                st.code(text)
        else:
            st.write(text)


# 3) 记忆查看区（只读）
with tab_mem:
    st.subheader(L.MEM_SUBHEADER)
    st.caption(L.MEM_CAPTION)

    query = st.text_input(L.MEM_SEARCH_LABEL, placeholder=L.MEM_SEARCH_PLACEHOLDER)
    categories = st.multiselect(L.MEM_FILTER_LABEL, L.MEM_CATEGORIES, default=[])

    if query.strip():
        rows = backend.semantic_search(query)
    else:
        rows = [
            {"topic": t, "content": c, "category": cat, "source": "记忆库"}
            for t, c, cat in backend.list_memories()
        ]
    if categories:
        rows = [r for r in rows if r.get("category") in categories]

    if not rows:
        st.info(L.MEM_EMPTY)
    else:
        st.caption(L.MEM_COUNT.format(count=len(rows)))
        has_source = any(r.get("source") for r in rows)
        table_rows = [
            {
                L.MEM_COL_TOPIC: r.get("topic", ""),
                L.MEM_COL_CONTENT: r.get("content", ""),
                L.MEM_COL_CATEGORY: r.get("category", ""),
                **({L.MEM_COL_SOURCE: r.get("source", "")} if has_source else {}),
            }
            for r in rows
        ]
        st.dataframe(
            table_rows,
            width="stretch",
            hide_index=True,
        )


# 4) 视觉感知区（识别结果，第一版不做实时视频流）
with tab_vis:
    st.subheader(L.VIS_SUBHEADER)
    st.caption(L.VIS_CAPTION)
    if st.button(L.BUTTON_REFRESH, key="vis_refresh"):
        st.rerun()

    vision = backend.get_vision()
    if not vision:
        st.info(L.VIS_NO_DATA)
    else:
        data, ts = vision
        st.caption(L.WS_LAST_UPDATE.format(time=time.strftime("%H:%M:%S", time.localtime(ts))))
        parts = data.get("parts", {})
        if parts:
            st.write(L.VIS_PARTS_TITLE)
            for name, zone in parts.items():
                st.markdown(f"- **{name}**：{zone}")
        else:
            st.write(L.VIS_NONE)
        with st.expander(L.VIS_RAW_EXPANDER):
            st.json(data)


# 5) 机器人状态区（里程计）
with tab_robot:
    st.subheader(L.ROB_SUBHEADER)
    if st.button(L.BUTTON_REFRESH, key="odom_refresh"):
        st.rerun()

    odom = backend.get_odom()
    if not odom:
        st.info(L.ROB_NO_DATA)
    else:
        data, ts = odom
        st.caption(L.WS_LAST_UPDATE.format(time=time.strftime("%H:%M:%S", time.localtime(ts))))
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(L.ROB_METRIC_X, f"{data['x']:.2f} m")
        c2.metric(L.ROB_METRIC_Y, f"{data['y']:.2f} m")
        c3.metric(L.ROB_METRIC_YAW, f"{data['yaw']:.2f} rad")
        c4.metric(L.ROB_METRIC_LINEAR, f"{data['linear_x']:.2f} m/s")
        c5.metric(L.ROB_METRIC_ANGULAR, f"{data['angular_z']:.2f} rad/s")
