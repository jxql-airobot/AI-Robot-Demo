# -*- coding: utf-8 -*-
"""
test_panels.py — V6.3 论文展示层面板测试
==========================================
验证三个新面板的数据加载、统计与图表逻辑（不依赖 Streamlit 运行上下文）。

用法（WSL，需 streamlit/matplotlib）：
    cd AI-Robot-Demo && python3 tests/test_panels.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_DIR = os.path.join(REPO_ROOT, "gui")
for p in (REPO_ROOT, GUI_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from panels import experiment_dashboard as ed  # noqa: E402
from panels import system_info as si  # noqa: E402
from panels import task_replay as tr  # noqa: E402


def test_load_records():
    records, mtime = ed._load_records_impl(ed.RUNTIME_LOG)
    assert records, "runtime_logs 应为非空"
    assert mtime > 0
    first = records[0]
    for key in (
        "task_id",
        "input",
        "success",
        "response_time",
        "generated_plan",
        "tool_calls",
        "execution_result",
    ):
        assert key in first, f"记录缺少字段 {key}"
    print(f"[1] runtime_logs: {len(records)} 条记录, 字段完整")


def test_summarize():
    records, _ = ed._load_records_impl(ed.RUNTIME_LOG)
    s = ed.summarize(records)
    assert s["total"] == len(records)
    assert 0 <= s["success_rate"] <= 1
    assert s["success"] + s["failed"] == s["total"]
    print(
        f"[2] 总体统计 OK: 总数={s['total']} 成功={s['success']} "
        f"成功率={s['success_rate']:.1%} 平均响应={s['avg_response_s']}s"
    )


def test_csv_loads():
    for name, path in (
        ("planner", ed.PLANNER_COMPARISON_CSV),
        ("rag", ed.RAG_CSV),
        ("backend", ed.BACKEND_CSV),
    ):
        rows = ed.load_csv_rows(path)
        assert rows, f"{name} CSV 为空"
        print(f"[3] {name} CSV: {len(rows)} 行")


def test_chart():
    cn_ok = ed._setup_cn_font()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 2.5))
    ax.bar(["Rule", "LLM"], [0.16, 0.82])
    ax.set_title("规划器成功率对比", fontsize=10)
    fig.canvas.draw()
    plt.close(fig)
    print(f"[4] matplotlib 图表渲染 OK（中文字体可用: {cn_ok}）")


def test_replay():
    records, _ = tr._load_records_impl(tr.RUNTIME_LOG)
    assert records
    print(f"[5] 任务回放数据源 OK: {len(records)} 条")


def test_system_info():
    assert si.VERSION and si.TECH_STACK and si.ARCH_TEXT and si.MODULES
    print(f"[6] 系统信息内容 OK: {si.PROJECT_NAME} {si.VERSION}")


if __name__ == "__main__":
    test_load_records()
    test_summarize()
    test_csv_loads()
    test_chart()
    test_replay()
    test_system_info()
    print("ALL PANEL TESTS PASSED")
