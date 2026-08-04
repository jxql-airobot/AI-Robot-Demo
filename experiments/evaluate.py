#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate.py — Agent 自动评测脚本 (V5.4)
========================================
按任务集运行 Agent，采集：
  - 成功率（计划匹配 + 步骤执行全部成功）
  - 响应时间（total）、AI 规划时间（plan）、工具执行时间（exec）
  - RAG 召回情况（recalled + 来源）

结果输出到 experiments/results/（JSON 摘要 + CSV 明细/汇总）。

用法（WSL，RAG 已配置）：
    python3 experiments/evaluate.py                 # 本地模式 + 自动规划器（DeepSeek/Mock）
    python3 experiments/evaluate.py --rounds 5
    python3 experiments/evaluate.py --planner mock
    python3 experiments/evaluate.py --mode ros2     # 需仿真系统已启动
"""

import argparse
import csv
import datetime
import json
import os
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (BASE, os.path.join(BASE, "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402

DEFAULT_TASKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks", "task_set.json")
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def task_success(task, resp):
    """根据任务的期望字段判定本轮是否成功"""
    plan = resp["plan"]
    steps = plan.get("steps", [])
    if not steps:
        return False
    if task.get("expected_in_goal") and task["expected_in_goal"] not in plan.get("goal", ""):
        return False
    if task.get("min_steps") and len(steps) < task["min_steps"]:
        return False
    tools = {s.get("tool") for s in steps}
    if task.get("expected_tools_any") and not (set(task["expected_tools_any"]) & tools):
        return False
    if task.get("expected_tool") or task.get("expected_action"):
        matched = False
        for s in steps:
            if task.get("expected_tool") and s.get("tool") != task["expected_tool"]:
                continue
            if task.get("expected_action") and s.get("args", {}).get("action") != task["expected_action"]:
                continue
            if task.get("expected_object") and s.get("args", {}).get("object") != task["expected_object"]:
                continue
            matched = True
            break
        if not matched:
            return False
    return all(r.get("ok") for r in resp["step_results"])


def run_round(agent, task):
    """在给定 Agent 会话中执行一轮（可选 setup_task 建立上下文）"""
    if task.get("setup_task"):
        agent.handle(task["setup_task"])
    resp = agent.handle(task["task"])
    steps_detail = " | ".join(
        f"{r.get('tool')}({'ok' if r.get('ok') else 'fail'})"
        for r in resp["step_results"]
    )
    record = {
        "success": task_success(task, resp),
        "goal": resp["plan"].get("goal", ""),
        "steps": len(resp["plan"].get("steps", [])),
        "steps_detail": steps_detail,
        "timings": agent.last_timings,
        "recall": None,
    }
    if task.get("expected_recall"):
        rows = agent.retrieve_memories(task["task"], top_k=3)
        record["recall"] = {
            "recalled": any(task["expected_recall"] in r["topic"] for r in rows),
            "sources": sorted({r["source"] for r in rows}),
        }
    return record


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def main():
    parser = argparse.ArgumentParser(description="Agent 自动评测")
    parser.add_argument("--mode", default="local", choices=["local", "ros2"])
    parser.add_argument("--planner", default="auto", choices=["auto", "mock"])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    with open(args.tasks, encoding="utf-8") as fh:
        tasks = json.load(fh)
    os.makedirs(args.out, exist_ok=True)

    # 临时记忆库（避免污染真实记忆）
    tmp_dir = tempfile.mkdtemp(prefix="eval_")
    db_path = os.path.join(tmp_dir, "eval.db")

    # 预置 RAG 记忆（通过 memory_tool 写入，同步向量）
    seeds = [t["memory"] for t in tasks if t.get("memory")]
    if seeds:
        seed_agent = Agent(backend=args.mode, db_path=db_path, planner=MockPlanPlanner())
        for seed in seeds:
            seed_agent.registry["memory_tool"].run({"write": seed})
        seed_agent.close()
        print(f"[评测] 已预置 {len(seeds)} 条 RAG 记忆")

    planner = MockPlanPlanner() if args.planner == "mock" else None
    summary_tasks = []
    detail_rows = []
    print(f"[评测] mode={args.mode} planner={args.planner} rounds={args.rounds}")

    for task in tasks:
        successes, totals, plans, execs, recalls = [], [], [], [], []
        for _ in range(args.rounds):
            agent = Agent(backend=args.mode, db_path=db_path, planner=planner)
            try:
                rec = run_round(agent, task)
            finally:
                agent.close()
            timings = rec["timings"]
            totals.append(timings["total_seconds"])
            plans.append(timings["plan_seconds"])
            execs.append(timings["exec_seconds"])
            successes.append(1 if rec["success"] else 0)
            recall = rec.get("recall")
            recalls.append(1 if recall and recall["recalled"] else 0)
            detail_rows.append(
                {
                    "id": task["id"],
                    "category": task["category"],
                    "round": len(totals),
                    "success": rec["success"],
                    "total_s": timings["total_seconds"],
                    "plan_s": timings["plan_seconds"],
                    "exec_s": timings["exec_seconds"],
                    "goal": rec["goal"],
                    "steps": rec["steps"],
                    "steps_detail": rec["steps_detail"],
                    "recall": (recall["recalled"] if recall else ""),
                    "recall_sources": (";".join(recall["sources"]) if recall else ""),
                }
            )
        summary_tasks.append(
            {
                "id": task["id"],
                "category": task["category"],
                "rounds": args.rounds,
                "success_rate": round(sum(successes) / args.rounds, 4),
                "avg_total_s": mean(totals),
                "avg_plan_s": mean(plans),
                "avg_exec_s": mean(execs),
                "rag_recall_rate": round(sum(recalls) / args.rounds, 4) if recalls else None,
            }
        )
        print(
            f"  [{task['id']}] 成功率={summary_tasks[-1]['success_rate']:.0%} "
            f"总耗时={summary_tasks[-1]['avg_total_s']}s "
            f"规划={summary_tasks[-1]['avg_plan_s']}s "
            f"执行={summary_tasks[-1]['avg_exec_s']}s"
        )

    overall_success = mean([t["success_rate"] for t in summary_tasks])
    overall_total = mean([t["avg_total_s"] for t in summary_tasks])
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "generated_at": ts,
        "mode": args.mode,
        "planner": args.planner,
        "rounds": args.rounds,
        "overall_success_rate": overall_success,
        "overall_avg_total_s": overall_total,
        "tasks": summary_tasks,
    }

    summary_path = os.path.join(args.out, f"{ts}_summary.json")
    summary_csv = os.path.join(args.out, f"{ts}_summary.csv")
    detail_csv = os.path.join(args.out, f"{ts}_detail.csv")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    with open(summary_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_tasks[0].keys()))
        writer.writeheader()
        writer.writerows(summary_tasks)
    with open(detail_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    print(f"\n[评测] 总体成功率={overall_success:.1%} 平均响应={overall_total}s")
    print(f"[评测] 结果已保存: {summary_path}")
    print(f"       汇总 CSV: {summary_csv}")
    print(f"       明细 CSV: {detail_csv}")


if __name__ == "__main__":
    main()
