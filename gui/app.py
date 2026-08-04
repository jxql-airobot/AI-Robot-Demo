#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — AI Robot Agent GUI 主入口 (V5.1)
=========================================
Streamlit 单页应用（ROS2 模式为主）：
  1. 任务对话区   ：下发自然语言任务，实时展示状态反馈
  2. 工作台状态区 ：解析 /ai_robot/status 成工位表格
  3. 记忆查看区   ：查看/查询 SQLite 记忆（V5.1 只读，不做删除）
  4. 视觉感知区   ：展示最近一次 /ai_robot/vision 识别结果（第一版不做实时视频）
  5. 机器人状态区 ：展示 /odom 位置与速度

运行（WSL，需先 source ROS2）：
  streamlit run gui/app.py
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
from config import STATUS_QUIET_SECONDS, STATUS_WAIT_TIMEOUT_SECONDS  # noqa: E402

st.set_page_config(page_title="AI Robot Agent V5.1", page_icon="🤖", layout="wide")


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


def execute_task(backend, task):
    """发送任务并收集本轮新增的状态反馈（去重；静默 1.5s 结束，最多 20s）"""
    baseline = backend.get_status()
    baseline_ts = baseline[1] if baseline else None
    backend.send_task(task)

    collected = []
    seen = set()
    last_seen_ts = None
    last = time.monotonic()
    deadline = time.monotonic() + STATUS_WAIT_TIMEOUT_SECONDS

    with st.spinner("AI 大脑规划与机器人执行中..."):
        while time.monotonic() < deadline:
            status = backend.get_status()
            if (
                status
                and status[1] != last_seen_ts
                and (baseline_ts is None or status[1] > baseline_ts)
            ):
                text = status[0]
                if text not in seen:
                    collected.append(text)
                    seen.add(text)
                last_seen_ts = status[1]
                last = time.monotonic()
            if time.monotonic() - last > STATUS_QUIET_SECONDS:
                break
            time.sleep(0.1)

    return collected if collected else ["（未收到状态反馈，请确认仿真系统已启动）"]


# ---------- 侧边栏：模式与连接 ----------

with st.sidebar:
    st.title("🤖 AI Robot Agent")
    st.caption("V5.1 · Streamlit 客户端")

    mode = st.radio("后端模式", ["ROS2（主模式）", "Local（暂未开放）"], index=0)

    if st.button("连接 / 重连"):
        if st.session_state.get("backend"):
            st.session_state["backend"].close()
            st.session_state["backend"] = None

    if mode.startswith("Local"):
        if st.session_state.get("backend"):
            st.session_state["backend"].close()
            st.session_state["backend"] = None
        st.info("Local 模式为后续版本功能，V5.1 暂未开放。")
        backend = None
    else:
        if st.session_state.get("backend") is None:
            try:
                st.session_state["backend"] = Ros2Backend()
            except Exception as exc:
                st.error(f"ROS2 连接失败：{exc}")
                st.caption("请确认：① 在 WSL 中 source 过 ROS2；② 仿真系统已启动。")
        backend = st.session_state.get("backend")

    if backend:
        st.success(f"已连接：{backend.name} 模式")
        st.caption("仿真系统需已启动（ros2 launch ai_robot demo_v4.launch.py）")

# ---------- 主界面 ----------

st.title("AI Robot Agent V5.1")
st.caption("Streamlit 独立客户端 · 不修改 V1-V4 任何代码与节点")

if backend is None:
    st.stop()

tab_chat, tab_ws, tab_mem, tab_vis, tab_robot = st.tabs(
    ["💬 任务对话", "🗂 工作台状态", "🧠 记忆查看", "👁 视觉感知", "🤖 机器人状态"]
)


# 1) 任务对话区
with tab_chat:
    st.subheader("任务对话")
    st.caption("输入自然语言任务，AI 大脑规划后由机器人执行。")

    if "history" not in st.session_state:
        st.session_state["history"] = []

    with st.expander("示例指令"):
        examples = [
            "扫描工作台",
            "红色零件在哪里",
            "把蓝色零件放到成品区",
            "记住：A区域在生产线左侧",
        ]
        cols = st.columns(len(examples))
        for col, ex in zip(cols, examples):
            if col.button(ex, key=f"ex_{ex}"):
                st.session_state["pending_task"] = ex

    for role, text in st.session_state["history"]:
        with st.chat_message(role):
            st.markdown(text)

    prompt = st.chat_input("下达任务，例如：把红色零件移动到检测区")
    pending = st.session_state.pop("pending_task", None)
    if prompt or pending:
        task = prompt or pending
        st.session_state["history"].append(("user", task))
        with st.chat_message("user"):
            st.markdown(task)
        for reply in execute_task(backend, task):
            st.session_state["history"].append(("assistant", reply))
            with st.chat_message("assistant"):
                st.markdown(reply)


# 2) 工作台状态区
with tab_ws:
    st.subheader("工作台状态")
    if st.button("刷新", key="ws_refresh"):
        st.rerun()

    status = backend.get_status()
    if not status:
        st.info("暂无状态数据。发送任务或等待仿真系统输出。")
    else:
        text, ts = status
        st.caption(f"最近更新：{time.strftime('%H:%M:%S', time.localtime(ts))}")
        ws = extract_workspace(text)
        if ws:
            st.write("各工位零件分布：")
            for station, parts in ws.items():
                left, right = st.columns([1, 3])
                left.markdown(f"**{station}**")
                right.write("、".join(parts) if parts else "（空）")
            with st.expander("原始状态文本"):
                st.code(text)
        else:
            st.write(text)


# 3) 记忆查看区（只读）
with tab_mem:
    st.subheader("记忆查看（只读）")
    st.caption("查看和查询 SQLite 记忆；V5.1 暂不提供删除功能。")

    query = st.text_input("关键词查询", placeholder="例如：零件 / 区域 / 检测区")
    categories = st.multiselect(
        "分类筛选", ["环境信息", "物体信息", "用户知识"], default=[]
    )

    rows = backend.search_memories(query) if query.strip() else backend.list_memories()
    if categories:
        rows = [r for r in rows if r[2] in categories]

    if not rows:
        st.info("暂无记忆。")
    else:
        st.caption(f"共 {len(rows)} 条")
        st.dataframe(
            [
                {"主题": topic, "内容": content, "分类": category}
                for topic, content, category in rows
            ],
            width="stretch",
            hide_index=True,
        )


# 4) 视觉感知区（识别结果，第一版不做实时视频流）
with tab_vis:
    st.subheader("视觉感知（识别结果）")
    st.caption("第一版仅展示识别结果；实时视频流在后续迭代中实现。")
    if st.button("刷新", key="vis_refresh"):
        st.rerun()

    vision = backend.get_vision()
    if not vision:
        st.info("暂无视觉识别结果（需要 Gazebo 相机 + vision_node 运行）。")
    else:
        data, ts = vision
        st.caption(f"最近更新：{time.strftime('%H:%M:%S', time.localtime(ts))}")
        parts = data.get("parts", {})
        if parts:
            st.write("识别到的零件与位置：")
            for name, zone in parts.items():
                st.markdown(f"- **{name}**：{zone}")
        else:
            st.write("当前画面未识别到零件。")
        with st.expander("原始识别结果"):
            st.json(data)


# 5) 机器人状态区（里程计）
with tab_robot:
    st.subheader("机器人状态（里程计）")
    if st.button("刷新", key="odom_refresh"):
        st.rerun()

    odom = backend.get_odom()
    if not odom:
        st.info("暂无里程计数据（需要 Gazebo 仿真运行）。")
    else:
        data, ts = odom
        st.caption(f"最近更新：{time.strftime('%H:%M:%S', time.localtime(ts))}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("X 坐标", f"{data['x']:.2f} m")
        c2.metric("Y 坐标", f"{data['y']:.2f} m")
        c3.metric("朝向 Yaw", f"{data['yaw']:.2f} rad")
        c4.metric("线速度", f"{data['linear_x']:.2f} m/s")
        c5.metric("角速度", f"{data['angular_z']:.2f} rad/s")
