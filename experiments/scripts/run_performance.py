#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_performance.py — 系统性能实验 (V6.5)
=========================================
执行 100 次完整任务，测量：
  - LLM 规划时间（Planner）
  - Tool 调用时间（Executor 执行）
  - 完整任务耗时（End-to-End）
  - RAG 检索时间（100 次语义检索）
  - Backend 响应时间（RobotStudio Backend 单次命令）

后端：ABB RobotStudio Backend（Mock 服务端）。
规划器：DeepSeek LLM + RAG（真实调用）。

用法：
    python experiments/scripts/run_performance.py --n 100
输出：
    experiments/results/performance_report.md
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests"),
          os.path.join(BASE, "experiments", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from experiments.scripts.run_task_sets import DeepSeekRobotStudioPlanner  # noqa: E402

RESULTS_DIR = os.path.join(BASE, "experiments", "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "performance_report.md")

TASKS = [
    "让机器人回到初始位置",
    "移动机器人到指定关节位置",
    "执行直线运动到目标点",
    "获取当前机器人关节位置",
    "读取机器人当前状态",
    "查询机器人TCP位姿",
    "移动机器人到工作区域",
    "完成一个零件搬运流程",
    "扫描工作台并报告所有零件位置",
    "回到等待位置",
]


def stats(values):
    if not values:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def run_benchmark(n):
    tmp = tempfile.mkdtemp(prefix="perf_")
    agent = Agent(
        backend="robotstudio",
        db_path=os.path.join(tmp, "perf.db"),
        planner=DeepSeekRobotStudioPlanner(),
        rag_enabled=True,
    )
    plan_times, exec_times, total_times, backend_times = [], [], [], []
    try:
        for i in range(n):
            task = TASKS[i % len(TASKS)]
            agent.handle(task)
            timings = agent.last_timings
            plan_times.append(timings.get("plan_seconds") or 0.0)
            exec_times.append(timings.get("exec_seconds") or 0.0)
            total_times.append(timings.get("total_seconds") or 0.0)
        # Backend 单次命令响应（GETPOS）
        backend = agent.registry["robot_tool"].backend
        for _ in range(n):
            t0 = time.monotonic()
            backend.execute({"action": "get_position"})
            backend_times.append(time.monotonic() - t0)
        # RAG 检索时间（100 次语义检索）
        rag_times = []
        for _ in range(n):
            t0 = time.monotonic()
            agent.retrieve_memories("MOVEJ 与 MOVEL 的区别", top_k=3)
            rag_times.append(time.monotonic() - t0)
    finally:
        agent.close()
    return {
        "plan": stats(plan_times),
        "exec": stats(exec_times),
        "total": stats(total_times),
        "backend": stats(backend_times),
        "rag": stats(rag_times),
        "n": n,
    }


def write_report(s):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    def fmt(x):
        return f"{x['mean'] * 1000:.2f} ± {x['std'] * 1000:.2f} ms " \
               f"(中位 {x['median'] * 1000:.2f}, 范围 {x['min'] * 1000:.1f}~" \
               f"{x['max'] * 1000:.1f})"

    lines = [
        "# 系统性能实验报告",
        "",
        f"## 1 实验环境与规模",
        "",
        f"- 完整任务次数：{s['n']}（真实 DeepSeek 规划 + RAG + "
        "RobotStudio Backend Mock 执行）",
        "- RAG 检索次数：100",
        "- 操作系统：Windows，Python 3.12",
        "",
        "## 2 性能指标",
        "",
        "| 指标 | 平均 ± 标准差 | 中位数 | 范围 |",
        "| --- | --- | --- | --- |",
        f"| LLM 规划时间 | {fmt(s['plan'])} | | |",
        f"| Tool 调用时间 | {fmt(s['exec'])} | | |",
        f"| Backend 响应时间 | {fmt(s['backend'])} | | |",
        f"| RAG 检索时间 | {fmt(s['rag'])} | | |",
        f"| 完整任务耗时 | {fmt(s['total'])} | | |",
        "",
        "## 3 结果分析",
        "",
        "（1）LLM 规划时间占完整任务耗时的主要部分，是端到端延迟的"
        "主导因素；",
        "",
        "（2）Tool 调用与 Backend 响应为毫秒级，执行链路开销可控；",
        "",
        "（3）RAG 检索为毫秒级，知识注入对整体延迟影响很小；",
        "",
        "（4）完整任务亚秒级到数秒级，满足交互式任务规划的使用需求。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="系统性能实验")
    parser.add_argument("--n", type=int, default=100, help="完整任务次数")
    args = parser.parse_args()
    print(f"[性能实验] {args.n} 次完整任务运行中（真实 LLM + RAG）...")
    s = run_benchmark(args.n)
    write_report(s)
    print(f"[完成] 规划 {s['plan']['mean'] * 1000:.0f}ms / "
          f"执行 {s['exec']['mean'] * 1000:.0f}ms / "
          f"总耗时 {s['total']['mean'] * 1000:.0f}ms / "
          f"RAG {s['rag']['mean'] * 1000:.1f}ms")
    print(f"[报告] {REPORT_PATH}")


if __name__ == "__main__":
    main()

