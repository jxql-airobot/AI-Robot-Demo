# -*- coding: utf-8 -*-
"""
task_replay.py — 任务执行回放 (V6.3)
=====================================
从统一实验日志中读取历史任务，按时间线展示：
  用户任务 → Agent 规划 → 工具调用 → 机器人执行 → 完成状态
用于论文第五章案例展示与答辩 Demo。
"""

import json
import os

import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_LOG = os.path.join(REPO_ROOT, "experiments", "results", "runtime_logs.json")


def _load_records_impl(path):
    records = []
    if not os.path.exists(path):
        return records, 0.0
    mtime = os.path.getmtime(path)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records, mtime


@st.cache_data(ttl=120, show_spinner=False)
def load_records(path):
    return _load_records_impl(path)


def _fmt_ms(value):
    if value is None:
        return "-"
    return f"{value * 1000:.0f} ms"


def _step_icon(ok):
    return "✅" if ok else "❌"


def render():
    st.subheader("任务执行回放")
    st.caption("从实验日志中选择一条任务，按时间线查看 Agent 完整执行过程。")

    records, _mtime = load_records(RUNTIME_LOG)
    if not records:
        st.info("暂无实验日志可回放。")
        return

    options = list(reversed(records))
    labels = [
        f"[{r.get('timestamp', '')}] {r.get('input', '')[:40]} "
        f"({'✅' if r.get('success') else '❌'})"
        for r in options
    ]
    selected = st.selectbox("选择任务", range(len(options)), format_func=lambda i: labels[i])
    r = options[selected]

    # ---------- 总体信息 ----------
    st.markdown("### 执行总览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("任务状态", "成功" if r.get("success") else "失败")
    c2.metric("响应时间", _fmt_ms(r.get("response_time")))
    c3.metric("规划时间", _fmt_ms(r.get("planning_time")))
    c4.metric("执行时间", _fmt_ms(r.get("execution_time")))

    if r.get("error"):
        st.warning(f"错误信息：{r['error']}")

    # ---------- 时间线 ----------
    st.markdown("### 执行时间线")

    st.markdown("**① 用户任务**")
    st.info(r.get("input", ""))

    plan = r.get("generated_plan") or r.get("planner_output") or {}
    st.markdown("**② Agent 规划**")
    if plan:
        st.markdown(f"- 任务分析：{plan.get('task_analysis', '')}")
        st.markdown(f"- 目标：{plan.get('goal', '')}")
        steps = plan.get("steps") or []
        if steps:
            st.markdown("- 执行步骤：")
            for i, step in enumerate(steps, 1):
                args = json.dumps(step.get("args", {}), ensure_ascii=False)
                st.markdown(f"  `{i}. {step.get('tool')} {args}` — {step.get('purpose', '')}")
    else:
        st.markdown("（无规划输出）")

    st.markdown("**③ 工具调用与执行结果**")
    results = r.get("execution_result") or []
    if not results:
        st.markdown("（无执行步骤）")
    else:
        for step in results:
            args = ""
            calls = r.get("tool_calls") or []
            if step.get("step") is not None and 1 <= step["step"] <= len(calls):
                args = json.dumps(calls[step["step"] - 1].get("args", {}), ensure_ascii=False)
            code = ""
            if not step.get("ok"):
                result = step.get("result")
                structured = result.get("error") if isinstance(result, dict) else None
                if isinstance(structured, dict) and structured.get("code"):
                    code = f" ⚠️ 错误码 {structured['code']}"
            st.markdown(
                f"{_step_icon(step.get('ok'))} **第 {step.get('step')} 步** "
                f"[{step.get('tool')}] {args} — {step.get('message', '')}{code}"
            )

    st.markdown("**④ 完成**")
    if r.get("success"):
        st.success(f"任务成功完成，总耗时 {_fmt_ms(r.get('response_time'))}。")
    else:
        st.error(f"任务失败：{r.get('error') or '无错误信息'}")

    # ---------- 流程示意 ----------
    st.markdown("### Agent 处理流程")
    st.code(
        "用户任务\n    ↓\nLLM Agent 理解与规划\n    ↓\n工具调用（RobotTool / VisionTool ...）\n"
        "    ↓\n机器人执行\n    ↓\n结果反馈",
        language="text",
    )
