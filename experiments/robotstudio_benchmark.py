#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robotstudio_benchmark.py — RobotStudio 实验基准 (V6.2)
======================================================
面向论文实验的 RobotStudio 任务集评测，覆盖四类任务：
  1. 基础运动（HOME / 关节移动 / 直线移动 / 状态）
  2. Agent 规划任务（自然语言 -> 机器人动作）
  3. 视觉任务（感知 -> 定位）
  4. 记忆任务（记忆召回 -> 规划 -> 执行）

采集指标（论文用）：
  - 任务成功率（计划匹配 + 步骤执行全部成功）
  - 平均响应时间（total）、AI 规划时间（plan）、工具执行时间（exec）
  - RAG 召回率（语义/关键词）
  - 失败原因（每轮失败样本自动分类记录）

用法：
    python experiments/robotstudio_benchmark.py                  # Mock + 确定性规划器
    python experiments/robotstudio_benchmark.py --backend real   # 真实 RobotStudio（需已重载模块）
    python experiments/robotstudio_benchmark.py --planner deepseek
    python experiments/robotstudio_benchmark.py --rounds 5

输出：experiments/results/ 下 JSON 汇总 + CSV 明细/汇总 + Markdown 论文数据报告。
"""

import argparse
import csv
import datetime
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402
from mock_robotstudio_planner import RobotStudioMockPlanner  # noqa: E402

DEFAULT_TASKS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tasks", "task_set_robotstudio.json"
)
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def build_agent(backend, db_path, planner, robotstudio_client=None):
    """按参数构造 Agent（robotstudio backend）"""
    if backend == "real":
        from robotstudio.robotstudio_client import RobotStudioClient

        client = robotstudio_client or RobotStudioClient(
            host="127.0.0.1", port=30000, timeout_seconds=15.0, mock=False
        )
        return Agent(
            backend="robotstudio",
            db_path=db_path,
            planner=planner,
            robotstudio_client=client,
        )
    return Agent(backend="robotstudio", db_path=db_path, planner=planner)


def make_planner(name):
    if name == "robotstudio":
        return RobotStudioMockPlanner()
    if name == "mock":
        return MockPlanPlanner()
    if name == "deepseek":
        # 返回 None：由 Agent 自动装配（带完整工具描述；有 DeepSeek Key 用真实规划器）
        return None
    raise ValueError(f"未知规划器: {name}")


def task_check(task, resp):
    """判定一轮成功并给出失败原因，返回 (success, reason)"""
    plan = resp["plan"]
    steps = plan.get("steps", [])
    if not steps:
        return False, f"计划为空或无法理解任务: {plan.get('goal', '')}"

    tools = {s.get("tool") for s in steps}
    if task.get("expected_tools_any") and not (
        set(task["expected_tools_any"]) & tools
    ):
        return False, f"工具不匹配，期望之一 {task['expected_tools_any']}，实际 {sorted(tools)}"

    matched = False
    if task.get("expected_tool") or task.get("expected_action"):
        for s in steps:
            if task.get("expected_tool") and s.get("tool") != task["expected_tool"]:
                continue
            if task.get("expected_action") and s.get("args", {}).get("action") != task[
                "expected_action"
            ]:
                continue
            matched = True
            break
        if not matched:
            detail = " | ".join(
                f"{s.get('tool')}:{s.get('args', {}).get('action', '-')}" for s in steps
            )
            return False, (
                f"计划动作不匹配（期望 {task.get('expected_tool')}/"
                f"{task.get('expected_action')}）: {detail}"
            )

    for r in resp["step_results"]:
        if not r.get("ok"):
            return False, f"步骤执行失败: {r.get('tool')}: {r.get('message')}"
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="RobotStudio 实验基准")
    parser.add_argument("--backend", default="mock", choices=["mock", "real"])
    parser.add_argument(
        "--planner", default="robotstudio", choices=["robotstudio", "mock", "deepseek"]
    )
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    with open(args.tasks, encoding="utf-8") as fh:
        tasks = json.load(fh)
    os.makedirs(args.out, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="rs_bench_")
    db_path = os.path.join(tmp_dir, "bench.db")

    # 预置 RAG 记忆（物体信息），供视觉/记忆任务召回
    seeds = [t["seed_memory"] for t in tasks if t.get("seed_memory")]
    if seeds:
        seed_agent = build_agent(args.backend, db_path, RobotStudioMockPlanner())
        for seed in seeds:
            seed_agent.registry["memory_tool"].run({"write": seed})
        seed_agent.close()
        print(f"[实验] 已预置 {len(seeds)} 条物体信息记忆")

    print(
        f"[实验] backend={args.backend} planner={args.planner} "
        f"rounds={args.rounds} tasks={len(tasks)}"
    )

    summary_tasks = []
    detail_rows = []
    for task in tasks:
        successes, totals, plans, execs, recalls = [], [], [], [], []
        failure_reasons = []
        for _ in range(args.rounds):
            agent = build_agent(args.backend, db_path, make_planner(args.planner))
            try:
                resp = agent.handle(task["task"])
                ok, reason = task_check(task, resp)
            except Exception as exc:
                resp = {"plan": {"steps": [], "goal": ""}, "step_results": []}
                ok, reason = False, f"Agent 执行异常: {exc}"
            finally:
                agent.close()

            timings = agent.last_timings
            totals.append(timings["total_seconds"])
            plans.append(timings["plan_seconds"])
            execs.append(timings["exec_seconds"])
            successes.append(1 if ok else 0)
            if not ok:
                failure_reasons.append(reason)

            recalled = None
            if task.get("expected_recall"):
                rows = agent.retrieve_memories(task["task"], top_k=3)
                recalled = any(task["expected_recall"] in r["topic"] for r in rows)
                recalls.append(1 if recalled else 0)
                if not recalled:
                    failure_reasons.append("RAG 召回失败（期望记忆未进入 top-3）")

            steps_detail = " | ".join(
                f"{r.get('tool')}({'ok' if r.get('ok') else 'fail'})"
                for r in resp["step_results"]
            )
            detail_rows.append(
                {
                    "id": task["id"],
                    "category": task["category"],
                    "round": len(totals),
                    "success": ok,
                    "total_s": timings["total_seconds"],
                    "plan_s": timings["plan_seconds"],
                    "exec_s": timings["exec_seconds"],
                    "goal": resp["plan"].get("goal", ""),
                    "steps_detail": steps_detail,
                    "recall": recalled if recalled is not None else "",
                    "failure_reason": reason or "",
                }
            )

        def mean(values):
            return round(sum(values) / len(values), 4) if values else 0.0

        summary_tasks.append(
            {
                "id": task["id"],
                "category": task["category"],
                "task": task["task"],
                "rounds": args.rounds,
                "success_rate": round(sum(successes) / args.rounds, 4),
                "avg_total_s": mean(totals),
                "avg_plan_s": mean(plans),
                "avg_exec_s": mean(execs),
                "rag_recall_rate": (
                    round(sum(recalls) / args.rounds, 4) if recalls else None
                ),
                "failure_reasons": sorted(set(failure_reasons))[:5],
            }
        )
        s = summary_tasks[-1]
        print(
            f"  [{task['id']}] 成功率={s['success_rate']:.0%} "
            f"响应={s['avg_total_s']}s 规划={s['avg_plan_s']}s "
            f"执行={s['avg_exec_s']}s"
            + (f" 召回={s['rag_recall_rate']:.0%}" if s["rag_recall_rate"] is not None else "")
            + (f"  失败: {'; '.join(s['failure_reasons'])}" if s["failure_reasons"] else "")
        )

    overall_success = round(
        sum(t["success_rate"] for t in summary_tasks) / len(summary_tasks), 4
    )
    overall_total = round(
        sum(t["avg_total_s"] for t in summary_tasks) / len(summary_tasks), 4
    )
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "generated_at": ts,
        "backend": args.backend,
        "planner": args.planner,
        "rounds": args.rounds,
        "overall_success_rate": overall_success,
        "overall_avg_total_s": overall_total,
        "tasks": summary_tasks,
    }

    summary_path = os.path.join(args.out, f"{ts}_robotstudio_summary.json")
    summary_csv = os.path.join(args.out, f"{ts}_robotstudio_summary.csv")
    detail_csv = os.path.join(args.out, f"{ts}_robotstudio_detail.csv")
    report_path = os.path.join(args.out, f"{ts}_robotstudio_report.md")
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

    # 论文 Markdown 报告
    lines = [
        "# RobotStudio 实验数据报告（论文用）",
        "",
        f"- 生成时间：{ts}",
        f"- 后端：{args.backend}（mock=本地模拟 / real=ABB RobotStudio 真实联调）",
        f"- 规划器：{args.planner}",
        f"- 每任务轮数：{args.rounds}",
        "",
        f"**总体成功率：{overall_success:.1%}，平均响应时间：{overall_total}s**",
        "",
        "## 分任务统计",
        "",
        "| 任务 | 类别 | 指令 | 成功率 | 平均响应(s) | 规划(s) | 执行(s) | RAG召回率 | 失败原因 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for t in summary_tasks:
        recall_cell = (
            f"{t['rag_recall_rate']:.0%}"
            if t["rag_recall_rate"] is not None
            else "-"
        )
        lines.append(
            f"| {t['id']} | {t['category']} | {t['task']} | "
            f"{t['success_rate']:.0%} | {t['avg_total_s']} | "
            f"{t['avg_plan_s']} | {t['avg_exec_s']} | {recall_cell} | "
            f"{'; '.join(t['failure_reasons']) or '-'} |"
        )
    lines += ["", "## 指标定义", "",
              "- 成功率：计划匹配任务期望（工具/动作/目标）且所有步骤执行 ok",
              "- 响应时间：Agent 处理总耗时（规划 + 执行）",
              "- 规划时间：planner.plan 耗时（DeepSeek API / 离线规划器）",
              "- 执行时间：工具链执行耗时（RobotStudio TCP 命令为主）",
              "- RAG 召回率：期望记忆是否进入查询 top-3（来源：语义检索/关键词检索）",
              "- 失败原因：自动分类记录（计划不匹配 / 步骤执行失败 / RAG 召回失败）", ""]
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"\n[实验] 总体成功率={overall_success:.1%} 平均响应={overall_total}s")
    print(f"[实验] 结果已保存: {summary_path}")
    print(f"       汇总 CSV: {summary_csv}")
    print(f"       明细 CSV: {detail_csv}")
    print(f"       论文报告: {report_path}")


if __name__ == "__main__":
    main()
