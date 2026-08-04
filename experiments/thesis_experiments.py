#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thesis_experiments.py — 论文实验脚本 (V6.2)
===========================================
三组论文实验，输出 CSV 便于画图：

实验1：Agent 任务规划测试
    指标：任务成功率、平均响应时间（总耗时）

实验2：RAG 效果测试（无 RAG vs RAG）
    指标：知识召回率、任务成功率

实验3：机器人后端测试（Gazebo vs RobotStudio）
    指标：执行成功率、执行时间

用法：
    python experiments/thesis_experiments.py --experiment 1
    python experiments/thesis_experiments.py --experiment 2 --rounds 5
    python experiments/thesis_experiments.py --experiment 3 --backend robotstudio --real
    python experiments/thesis_experiments.py --experiment all --rounds 5
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

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
TASK_SET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks", "task_set.json")
TASK_SET_RS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tasks", "task_set_robotstudio.json"
)


def load_tasks(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def task_check(task, resp):
    """判定一轮是否成功，返回 (ok, reason)（与 robotstudio_benchmark 一致）"""
    plan = resp["plan"]
    steps = plan.get("steps", [])
    if not steps:
        return False, f"计划为空: {plan.get('goal', '')}"
    tools = {s.get("tool") for s in steps}
    if task.get("expected_tools_any") and not (set(task["expected_tools_any"]) & tools):
        return False, "工具不匹配"
    if task.get("expected_tool") or task.get("expected_action"):
        matched = False
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
            return False, "计划动作不匹配"
    for r in resp["step_results"]:
        if not r.get("ok"):
            return False, f"执行失败: {r.get('tool')}: {r.get('message')}"
    return True, ""


def recall_hit(agent, task):
    if not task.get("expected_recall"):
        return None
    rows = agent.retrieve_memories(task["task"], top_k=3)
    return any(task["expected_recall"] in r["topic"] for r in rows)


def make_db(seeds, tasks):
    tmp = tempfile.mkdtemp(prefix="thesis_")
    db_path = os.path.join(tmp, "exp.db")
    if seeds:
        sa = Agent(backend="local", db_path=db_path, planner=MockPlanPlanner())
        for seed in seeds:
            sa.registry["memory_tool"].run({"write": seed})
        sa.close()
    return db_path


def run_tasks(tasks, agent_factory, rounds):
    """通用运行器：返回每任务的 (success_rate, avg_total, avg_plan, avg_exec, recall_rate, failures)"""
    out = []
    for task in tasks:
        succ, totals, plans, execs, recalls = [], [], [], [], []
        failures = []
        for _ in range(rounds):
            agent = agent_factory()
            try:
                resp = agent.handle(task["task"])
                ok, reason = task_check(task, resp)
            except Exception as exc:
                ok, reason = False, f"异常: {exc}"
            finally:
                agent.close()
            succ.append(1 if ok else 0)
            timings = agent.last_timings
            totals.append(timings["total_seconds"])
            plans.append(timings["plan_seconds"])
            execs.append(timings["exec_seconds"])
            if not ok:
                failures.append(reason)
            r = recall_hit(agent, task) if not task.get("no_recall_check") else None
            if r is not None:
                recalls.append(1 if r else 0)
        out.append(
            {
                "id": task["id"],
                "category": task["category"],
                "task": task["task"],
                "rounds": rounds,
                "success_rate": round(sum(succ) / rounds, 4),
                "avg_total_s": mean(totals),
                "avg_plan_s": mean(plans),
                "avg_exec_s": mean(execs),
                "recall_rate": (round(sum(recalls) / rounds, 4) if recalls else None),
                "failures": sorted(set(failures))[:3],
            }
        )
    return out


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[实验] CSV 已保存: {path}")


# ---------------- 实验1：Agent 任务规划测试 ----------------


def experiment1(rounds):
    rows = []
    # 任务集 × 对应规划器：V5.4 任务用 MockPlanPlanner，RobotStudio 任务用 RobotStudioMockPlanner
    for tasks_path, planner_name, planner, backend in (
        (TASK_SET, "mock", MockPlanPlanner(), "local"),
        (TASK_SET_RS, "robotstudio", RobotStudioMockPlanner(), "robotstudio"),
    ):
        tasks = load_tasks(tasks_path)
        results = run_tasks(
            tasks,
            lambda p=planner, b=backend: Agent(backend=b, planner=p),
            rounds,
        )
        for r in results:
            rows.append(
                {
                    "experiment": "E1_planning",
                    "planner": planner_name,
                    "task_id": r["id"],
                    "category": r["category"],
                    "task": r["task"],
                    "success_rate": r["success_rate"],
                    "avg_response_s": r["avg_total_s"],
                    "avg_plan_s": r["avg_plan_s"],
                    "avg_exec_s": r["avg_exec_s"],
                    "failures": ";".join(r["failures"]) or "",
                }
            )
    write_csv(
        os.path.join(RESULTS_DIR, "experiment1_planning.csv"),
        rows,
        [
            "experiment", "planner", "task_id", "category", "task",
            "success_rate", "avg_response_s", "avg_plan_s", "avg_exec_s", "failures",
        ],
    )
    overall = round(sum(r["success_rate"] for r in rows) / len(rows), 4)
    avg_rt = round(sum(r["avg_response_s"] for r in rows) / len(rows), 4)
    print(f"[实验1] 总体成功率={overall:.1%} 平均响应={avg_rt}s")


# ---------------- 实验2：RAG 效果测试 ----------------


def experiment2(rounds):
    # 只跑 RAG 相关任务（记忆/语义查询类），用各自任务集的规划器
    tasks = [t for t in load_tasks(TASK_SET) if t.get("expected_recall") or "记忆" in t.get("category", "")]
    seeds = [t["seed_memory"] for t in tasks if t.get("seed_memory")]
    db_path = make_db(seeds, tasks)

    rows = []
    for mode, rag in (("no_rag", False), ("rag", True)):
        results = run_tasks(
            tasks,
            lambda r=rag: Agent(
                backend="local",
                db_path=db_path,
                planner=MockPlanPlanner(),
                rag_enabled=r,
            ),
            rounds,
        )
        for r in results:
            rows.append(
                {
                    "experiment": "E2_rag",
                    "mode": mode,
                    "task_id": r["id"],
                    "category": r["category"],
                    "task": r["task"],
                    "success_rate": r["success_rate"],
                    "recall_rate": r["recall_rate"] if r["recall_rate"] is not None else "",
                    "failures": ";".join(r["failures"]) or "",
                }
            )
    write_csv(
        os.path.join(RESULTS_DIR, "experiment2_rag.csv"),
        rows,
        ["experiment", "mode", "task_id", "category", "task", "success_rate", "recall_rate", "failures"],
    )
    for mode in ("no_rag", "rag"):
        subset = [r for r in rows if r["mode"] == mode]
        if subset:
            sr = round(sum(float(r["success_rate"]) for r in subset) / len(subset), 4)
            rr = [
                float(r["recall_rate"]) for r in subset if r["recall_rate"] != ""
            ]
            rr = round(sum(rr) / len(rr), 4) if rr else None
            rr_text = f"{rr:.1%}" if rr is not None else "-"
            print(f"[实验2] {mode}: 成功率={sr:.1%} 召回率={rr_text}")


# ---------------- 实验3：机器人后端测试 ----------------


def experiment3(rounds, backend, real=False, host="127.0.0.1", port=30000):
    rows = []

    if backend in ("robotstudio", "all"):
        tasks = load_tasks(TASK_SET_RS)
        seeds = [t["seed_memory"] for t in tasks if t.get("seed_memory")]
        db_path = make_db(seeds, tasks)

        if real:
            # 预检：真实 RobotStudio 必须在线，否则明确提示
            try:
                from robotstudio.robotstudio_client import RobotStudioClient

                probe = RobotStudioClient(
                    host=host, port=port, timeout_seconds=5.0, mock=False
                )
                probe.connect()
                ok, _ = probe.ping()
                probe.close()
                if not ok:
                    raise RuntimeError("RobotStudio ping 失败")
                print(f"[实验3] 预检通过：{host}:{port} 已连接")
            except Exception as exc:
                print(
                    f"[实验3] 预检失败：真实 RobotStudio 未就绪（{exc}）。\n"
                    f"        请先在 RobotStudio 中重载 socket_server.mod 并启动 "
                    f"PROC socket_main，再重新运行。"
                )
                return

        def rs_factory():
            if real:
                from robotstudio.robotstudio_client import RobotStudioClient

                client = RobotStudioClient(
                    host=host, port=port, timeout_seconds=20.0, mock=False
                )
                return Agent(
                    backend="robotstudio",
                    db_path=db_path,
                    planner=RobotStudioMockPlanner(),
                    robotstudio_client=client,
                )
            return Agent(
                backend="robotstudio",
                db_path=db_path,
                planner=RobotStudioMockPlanner(),
            )

        results = run_tasks(tasks, rs_factory, rounds)
        for r in results:
            rows.append(
                {
                    "experiment": "E3_backend",
                    "backend": "RobotStudio" + ("(real)" if real else "(mock)"),
                    "task_id": r["id"],
                    "category": r["category"],
                    "task": r["task"],
                    "exec_success_rate": r["success_rate"],
                    "avg_exec_s": r["avg_exec_s"],
                    "avg_response_s": r["avg_total_s"],
                    "failures": ";".join(r["failures"]) or "",
                }
            )
        sr = round(sum(r["exec_success_rate"] for r in rows) / len(rows), 4)
        et = round(sum(r["avg_exec_s"] for r in rows) / len(rows), 4)
        print(f"[实验3] RobotStudio: 执行成功率={sr:.1%} 平均执行={et}s")

    if backend in ("gazebo", "all"):
        tasks = load_tasks(TASK_SET)
        db_path = make_db([], tasks)

        def gazebo_factory():
            return Agent(backend="ros2", db_path=db_path, planner=MockPlanPlanner())

        try:
            probe = gazebo_factory()
            probe.close()
            gazebo_ok = True
        except Exception as exc:
            gazebo_ok = False
            rows.append(
                {
                    "experiment": "E3_backend",
                    "backend": "Gazebo(ros2)",
                    "task_id": "-",
                    "category": "-",
                    "task": "-",
                    "exec_success_rate": "",
                    "avg_exec_s": "",
                    "avg_response_s": "",
                    "failures": f"SKIP: ROS2/Gazebo 未启动 ({exc})",
                }
            )
            print(f"[实验3] Gazebo: SKIP（ROS2/Gazebo 未启动）: {exc}")
        if gazebo_ok:
            results = run_tasks(tasks, gazebo_factory, rounds)
            for r in results:
                rows.append(
                    {
                        "experiment": "E3_backend",
                        "backend": "Gazebo(ros2)",
                        "task_id": r["id"],
                        "category": r["category"],
                        "task": r["task"],
                        "exec_success_rate": r["success_rate"],
                        "avg_exec_s": r["avg_exec_s"],
                        "avg_response_s": r["avg_total_s"],
                        "failures": ";".join(r["failures"]) or "",
                    }
                )

    write_csv(
        os.path.join(RESULTS_DIR, "experiment3_backend.csv"),
        rows,
        [
            "experiment", "backend", "task_id", "category", "task",
            "exec_success_rate", "avg_exec_s", "avg_response_s", "failures",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="论文实验脚本")
    parser.add_argument("--experiment", default="all", choices=["1", "2", "3", "all"])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--backend", default="all", choices=["robotstudio", "gazebo", "all"])
    parser.add_argument("--real", action="store_true", help="实验3 RobotStudio 用真实后端")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[实验] 开始 {ts} rounds={args.rounds}")
    if args.experiment in ("1", "all"):
        experiment1(args.rounds)
    if args.experiment in ("2", "all"):
        experiment2(args.rounds)
    if args.experiment in ("3", "all"):
        experiment3(args.rounds, args.backend, real=args.real)
    print("[实验] 全部完成")


if __name__ == "__main__":
    main()
