# -*- coding: utf-8 -*-
"""
experiment_dashboard.py — 实验数据看板 (V6.3)
==============================================
读取 experiments/results/ 下的统一实验日志与论文对比实验 CSV，在 GUI
中展示：
  - 实验总体统计（任务数 / 成功率 / 平均响应时间）
  - 规划器对比（Rule vs LLM）与 RAG 对比
  - 响应时间图（论文第五章截图素材）
  - 失败案例统计（失败案例分析）

只读展示，不修改任何实验数据与核心代码。
"""

import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(REPO_ROOT, "experiments", "results")
RUNTIME_LOG = os.path.join(RESULTS_DIR, "runtime_logs.json")
PLANNER_COMPARISON_CSV = os.path.join(
    RESULTS_DIR, "planner_comparison", "planner_comparison.csv"
)
RAG_CSV = os.path.join(RESULTS_DIR, "experiment2_rag.csv")
BACKEND_CSV = os.path.join(RESULTS_DIR, "experiment3_backend.csv")


def _setup_cn_font():
    """设置中文字体（WSL/Windows 自动探测，找不到时回退并提示）"""
    import matplotlib.font_manager as fm

    candidates = [
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "SimHei",
    ]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return True
    # WSL 可访问 Windows 字体目录：直接注册 Windows 中文字体
    for path, name in (
        ("/mnt/c/Windows/Fonts/simhei.ttf", "SimHei"),
        ("/mnt/c/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("/mnt/c/Windows/Fonts/simsun.ttc", "SimSun"),
    ):
        if os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
                matplotlib.rcParams["font.sans-serif"] = [name]
                matplotlib.rcParams["axes.unicode_minus"] = False
                return True
            except Exception:
                continue
    matplotlib.rcParams["axes.unicode_minus"] = False
    return False


def _load_records_impl(path):
    """读取 JSON Lines 实验日志（纯实现，便于测试）"""
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
    """读取 JSON Lines 实验日志（按文件修改时间缓存）"""
    return _load_records_impl(path)


def load_csv_rows(path):
    """读取 CSV 为 dict 列表（utf-8-sig 兼容带 BOM 的 Windows 生成文件）"""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def summarize(records):
    total = len(records)
    success = sum(1 for r in records if r.get("success"))
    times = [r.get("response_time") for r in records if r.get("response_time") is not None]
    return {
        "total": total,
        "success": success,
        "failed": total - success,
        "success_rate": round(success / total, 4) if total else 0.0,
        "avg_response_s": _mean(times),
    }


def _format_ms(seconds):
    if seconds is None:
        return "-"
    return f"{seconds * 1000:.0f} ms"


def _render_fig(fig, width=520):
    """把 matplotlib 图保存为 PNG bytes 后显示（固定尺寸，避免容器拉伸）"""
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    st.image(buf.getvalue(), width=width)


def render():
    st.subheader("实验数据看板")
    st.caption("数据来源：experiments/results/runtime_logs.json 与论文对比实验 CSV")

    records, _mtime = load_records(RUNTIME_LOG)
    if not records:
        st.info("暂无实验日志（experiments/results/runtime_logs.json 为空或不存在）。")
        return

    cn_ok = _setup_cn_font()

    # ---------- 1. 实验总体统计 ----------
    st.markdown("### 1. 实验总体统计")
    s = summarize(records)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("任务总数", s["total"])
    c2.metric("成功", s["success"])
    c3.metric("失败", s["failed"])
    c4.metric("成功率", f"{s['success_rate']:.1%}")
    c5.metric("平均响应", _format_ms(s["avg_response_s"]))

    # ---------- 2. 不同实验模式对比 ----------
    st.markdown("### 2. 实验模式对比")
    planner_rows = load_csv_rows(PLANNER_COMPARISON_CSV)
    if planner_rows:
        st.markdown("#### 规划器对比（Rule Planner vs LLM Agent）")
        agg = {}
        for row in planner_rows:
            method = row.get("method", "")
            agg.setdefault(method, []).append(row)
        table = []
        for method in ("rule", "llm"):
            rows = agg.get(method, [])
            if not rows:
                continue
            label = "Rule Planner" if method == "rule" else "LLM Agent"
            table.append(
                {
                    "方法": label,
                    "任务数": len(rows),
                    "标准任务成功率": f"{_mean([float(r['standard_success_rate']) for r in rows]):.1%}",
                    "语言变体成功率": f"{_mean([float(r['variant_success_rate']) for r in rows]):.1%}",
                    "平均响应": _format_ms(_mean([float(r['avg_response_s']) for r in rows])),
                }
            )
        st.table(table)
        st.caption("对应论文第五章：LLM Agent 与规则规划器在自然语言任务理解上的对比实验。")

    rag_rows = load_csv_rows(RAG_CSV)
    if rag_rows:
        st.markdown("#### RAG 知识增强对比（无 RAG vs 有 RAG）")
        rows = []
        for row in rag_rows:
            recall = row.get("recall_rate")
            rows.append(
                {
                    "模式": "无 RAG" if row.get("mode") == "no_rag" else "有 RAG",
                    "任务": row.get("task", ""),
                    "成功率": row.get("success_rate", ""),
                    "语义召回率": f"{float(recall):.0%}" if recall else "-",
                }
            )
        st.table(rows)

    backend_rows = load_csv_rows(BACKEND_CSV)
    if backend_rows:
        st.markdown("#### 系统执行稳定性（RobotStudio / Gazebo 后端）")
        rows = []
        for row in backend_rows:
            rows.append(
                {
                    "后端": row.get("backend", ""),
                    "任务": row.get("task", ""),
                    "执行成功率": row.get("exec_success_rate", ""),
                    "平均执行": _format_ms(float(row["avg_exec_s"]) if row.get("avg_exec_s") else None),
                    "平均响应": _format_ms(float(row["avg_response_s"]) if row.get("avg_response_s") else None),
                    "失败原因": row.get("failures", ""),
                }
            )
        st.table(rows)

    # ---------- 3. 响应时间图 ----------
    st.markdown("### 3. 响应时间分析")
    if not cn_ok:
        st.caption("提示：未检测到中文字体，图表中文可能显示为方块（可安装 fonts-noto-cjk）。")

    col_a, col_b = st.columns(2)

    with col_a:
        if planner_rows:
            fig, ax = plt.subplots(figsize=(5, 3.2), dpi=120)
            methods = ["rule", "llm"]
            labels = ["Rule", "LLM"]
            std = [
                _mean([float(r["standard_success_rate"]) for r in agg.get(m, [])])
                for m in methods
            ]
            var = [
                _mean([float(r["variant_success_rate"]) for r in agg.get(m, [])])
                for m in methods
            ]
            x = range(len(labels))
            ax.bar([i - 0.18 for i in x], std, width=0.36, label="标准任务")
            ax.bar([i + 0.18 for i in x], var, width=0.36, label="语言变体")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels)
            ax.set_ylabel("成功率")
            ax.set_ylim(0, 1.05)
            ax.legend(fontsize=8)
            ax.set_title("规划器任务成功率对比", fontsize=10)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            _render_fig(fig)

    with col_b:
        if planner_rows:
            fig, ax = plt.subplots(figsize=(5, 3.2), dpi=120)
            resp = [
                _mean([float(r["avg_response_s"]) for r in agg.get(m, [])])
                for m in methods
            ]
            ax.bar(labels, [v * 1000 for v in resp], color=["#8c8c8c", "#4c78a8"])
            ax.set_ylabel("平均响应时间 (ms)")
            ax.set_title("规划器平均响应时间对比", fontsize=10)
            for i, v in enumerate(resp):
                ax.text(i, v * 1000 + 20, f"{v * 1000:.0f} ms", ha="center", fontsize=8)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            _render_fig(fig)

    # 按动作类型的平均响应时间（runtime_logs）
    action_times = {}
    for r in records:
        calls = r.get("tool_calls") or []
        for call in calls:
            if call.get("tool") != "robot_tool":
                continue
            action = (call.get("args") or {}).get("action", "unknown")
            action_times.setdefault(action, []).append(r.get("response_time"))
    if action_times:
        st.markdown("#### 机器人指令平均响应时间")
        names = {
            "move_home": "HOME",
            "joint_move": "MOVEJ",
            "linear_move": "MOVEL",
            "get_position": "GETPOS",
            "get_pose": "GETPOSE",
            "move": "MOVE",
        }
        labels = [names.get(k, k) for k in action_times]
        values = [_mean(v) * 1000 for v in action_times.values()]
        fig, ax = plt.subplots(figsize=(8, 3.2), dpi=120)
        bars = ax.bar(labels, values, color="#4c78a8")
        for bar, v in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 5,
                f"{v:.0f} ms",
                ha="center",
                fontsize=8,
            )
        ax.set_ylabel("平均响应时间 (ms)")
        ax.set_title("机器人指令平均响应时间", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        _render_fig(fig, width=760)

    # ---------- 4. 失败案例统计 ----------
    st.markdown("### 4. 失败案例统计")
    failed = [r for r in records if not r.get("success")]
    if not failed:
        st.success("当前日志中无失败记录。")
    else:
        st.caption(f"共 {len(failed)} 条失败记录，展示最近 50 条（对应论文失败案例分析）。")
        rows = []
        for r in failed[-50:][::-1]:
            rows.append(
                {
                    "任务ID": r.get("task_id", ""),
                    "输入": r.get("input", ""),
                    "错误原因": (r.get("error") or "无错误信息")[:80],
                    "响应时间": _format_ms(r.get("response_time")),
                }
            )
        st.dataframe(rows, width="stretch")
