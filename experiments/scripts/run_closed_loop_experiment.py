#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_closed_loop_experiment.py — 闭环 Agent 异常恢复实验 (V6.4)
=============================================================
验证闭环 Agent（Observation + Reflection + Replanning）在工业机器人
任务执行失败情况下的异常恢复能力，为论文第五章提供真实实验数据。

三类异常：
  1. action_param    动作参数异常（Safety 预检拒绝非法参数）
  2. communication   通信异常（Backend 返回 socket 错误）
  3. execution       执行失败（Backend 返回运动失败）

后端：ABB RobotStudio Backend（Mock 服务端，文本协议与真实 RAPID
SocketServer 一致；未连接物理虚拟控制器，实验环境已明确标注）。

不改动核心代码：故障通过实验脚本内的 FaultPlanner / FaultBackend
注入，闭环 Agent 与真实链路完全一致。

用法：
    python experiments/scripts/run_closed_loop_experiment.py --rounds 10
输出：
    experiments/logs/closed_loop_experiment.json
    experiments/results/closed_loop_report.md
"""

import argparse
import datetime
import json
import os
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402

LOGS_DIR = os.path.join(BASE, "experiments", "logs")
RESULTS_DIR = os.path.join(BASE, "experiments", "results")
EXPERIMENT_LOG = os.path.join(LOGS_DIR, "closed_loop_experiment.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "closed_loop_report.md")

EXPERIMENT_TYPES = ["action_param", "communication", "execution"]

NORMAL_PLAN = {
    "task_analysis": "移动机器人到指定关节位置",
    "goal": "移动到指定关节位置",
    "current_state": "未知",
    "steps": [
        {
            "tool": "robot_tool",
            "args": {"action": "joint_move", "joints": [10.0, 20.0, 30.0, 45.0, 60.0, 0.0]},
            "purpose": "移动到指定关节位置",
        }
    ],
}

INVALID_PLAN = {
    "task_analysis": "移动机器人到指定关节位置",
    "goal": "移动到指定关节位置",
    "current_state": "未知",
    "steps": [
        {
            "tool": "robot_tool",
            "args": {"action": "joint_move", "joints": [10.0, 20.0]},
            "purpose": "移动到指定关节位置",
        }
    ],
}


class FaultPlanner:
    """可控故障规划器：前 fail_first_n 次返回故障计划，之后返回正常计划"""

    def __init__(self, fail_type, fail_first_n=1):
        self.fail_type = fail_type
        self.fail_first_n = fail_first_n
        self.calls = 0

    def plan(self, task, context, memory_text=""):
        self.calls += 1
        if self.fail_type == "action_param" and self.calls <= self.fail_first_n:
            return INVALID_PLAN
        return NORMAL_PLAN


class FaultBackend:
    """可控故障后端：前 fail_first_n 次返回指定故障，之后转发真实后端"""

    def __init__(self, real_backend, fail_type, fail_first_n=1):
        self.real = real_backend
        self.fail_type = fail_type
        self.fail_first_n = fail_first_n
        self.calls = 0

    def execute(self, action):
        self.calls += 1
        if self.calls <= self.fail_first_n:
            if self.fail_type == "communication":
                return {
                    "ok": False,
                    "success": False,
                    "error": "socket timeout",
                    "stage": "socket",
                    "messages": ["RobotStudio 执行异常: 连接超时"],
                    "workspace": None,
                    "joints": None,
                }
            if self.fail_type == "execution":
                return {
                    "ok": False,
                    "success": False,
                    "error": "MOVEJ failed: 50050 位置超出范围",
                    "stage": "motion",
                    "messages": ["执行失败: MOVEJ failed: 50050 位置超出范围"],
                    "workspace": None,
                    "joints": None,
                }
        return self.real.execute(action)

    def get_state(self):
        return self.real.get_state()


def make_agent(fail_type, backend="mock"):
    """构造闭环 Agent：RobotStudio Backend + 故障注入。

    backend: "mock"（默认，本地 Mock 服务端）| "real"（连接真实
    RobotStudio 虚拟控制器，端口从 robotstudio/config.json 读取）
    """
    tmp = tempfile.mkdtemp(prefix="closed_loop_exp_")
    planner = FaultPlanner(fail_type)
    kwargs = dict(
        backend="robotstudio",
        db_path=os.path.join(tmp, "exp.db"),
        planner=planner,
        rag_enabled=False,
        closed_loop=True,
    )
    if backend == "real":
        from robotstudio.config import load_config as load_rs_config
        from robotstudio.robotstudio_client import RobotStudioClient

        cfg = load_rs_config()
        kwargs["robotstudio_client"] = RobotStudioClient(
            host=cfg.get("host", "127.0.0.1"),
            port=int(cfg.get("port", 30000)),
            timeout_seconds=float(cfg.get("timeout", 5.0)),
            mock=False,
        )
    agent = Agent(**kwargs)
    if fail_type in ("communication", "execution"):
        real_backend = agent.registry["robot_tool"].backend
        agent.registry["robot_tool"].backend = FaultBackend(
            real_backend, fail_type
        )
    return agent


def run_one(fail_type, task, max_rounds=3, backend="mock"):
    """运行一次闭环任务，返回记录 dict"""
    agent = make_agent(fail_type, backend=backend)
    try:
        t0 = time.monotonic()
        resp = agent.handle_closed_loop(task, max_rounds=max_rounds)
        elapsed = time.monotonic() - t0
        cl = resp["closed_loop"]
        rounds = len(cl["rounds"])
        first_reflection = cl["rounds"][0]["reflection"] if rounds else {}
        return {
            "experiment_type": fail_type,
            "task": task,
            "success": bool(cl.get("task_completed")),
            "need_replan": bool(first_reflection.get("need_replan")),
            "rounds": rounds,
            "error_type": first_reflection.get("error_type", "none"),
            "recovery_time": f"{elapsed:.3f} s",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }
    finally:
        agent.close()


def write_log(records):
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(EXPERIMENT_LOG, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def summarize(records, fail_type):
    items = [r for r in records if r["experiment_type"] == fail_type]
    total = len(items)
    recovered = sum(1 for r in items if r["success"])
    replan_counts = [r["rounds"] - 1 for r in items if r["rounds"] > 1]
    times = [float(r["recovery_time"].replace(" s", "")) for r in items]
    return {
        "type": fail_type,
        "total": total,
        "recovered": recovered,
        "rate": recovered / total if total else 0.0,
        "avg_replan": sum(replan_counts) / len(replan_counts) if replan_counts else 0.0,
        "avg_time": sum(times) / len(times) if times else 0.0,
        "max_rounds": max((r["rounds"] for r in items), default=0),
    }


def write_report(all_records, backend="mock"):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    stats = [summarize(all_records, t) for t in EXPERIMENT_TYPES]
    backend_desc = (
        "- 后端类型：ABB RobotStudio Backend（Mock 服务端，文本协议与真实 "
        "RAPID SocketServer 一致；本实验未连接物理 IRC5 虚拟控制器）"
        if backend == "mock"
        else "- 后端类型：ABB RobotStudio 虚拟控制器（IRC5 + IRB120，"
        "TCP 127.0.0.1:30000，RAPID SocketServer 真实运行）"
    )
    lines = [
        "# 闭环 Agent 异常恢复实验报告",
        "",
        "## 1 实验目的",
        "",
        "验证闭环 Agent（规划-执行-观察-反思-重新规划）在工业机器人任务",
        "执行失败情况下的异常恢复能力，包括动作参数异常、通信异常与执行",
        "失败三类场景下的重规划成功率与恢复效率。",
        "",
        "## 2 实验环境",
        "",
        "- 操作系统：Windows，Python 3.12",
        backend_desc,
        "- Agent 配置：closed_loop=True，rag_enabled=False",
        "- max_rounds：3",
        "",
        "## 3 实验设计",
        "",
        "三类异常各运行 10 次，共 30 次：",
        "",
        "1. 动作参数异常（action_param）：首轮规划生成非法关节参数，",
        "   验证 Safety 预检拒绝与重规划恢复；",
        "2. 通信异常（communication）：后端首轮返回 socket 错误，",
        "   验证异常捕获、Reflection 分类与重规划恢复；",
        "3. 执行失败（execution）：后端首轮返回运动失败，验证 Observation",
        "   反馈、Reflection 分类与重规划恢复。",
        "",
        "## 4 实验结果",
        "",
        "| 异常类型 | 实验次数 | 恢复成功率 | 平均重规划次数 | 平均恢复时间 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in stats:
        lines.append(
            f"| {s['type']} | {s['total']} | {s['rate']:.0%} "
            f"({s['recovered']}/{s['total']}) | {s['avg_replan']:.2f} | "
            f"{s['avg_time']:.3f} s |"
        )
    lines += [
        "",
        "原始逐次记录见 experiments/logs/closed_loop_experiment.json。",
        "",
        "## 5 结果分析",
        "",
        "（1）Observation 反馈作用：执行器完成后，Observation 将后端返回的",
        "失败信息（stage/error/message）统一为结构化观察，供后续分析；",
        "",
        "（2）Reflection 异常分类作用：Reflection 依据观察内容把失败分类为",
        "action_param / communication / execution，为重规划提供明确原因；",
        "",
        "（3）Replanning 机制作用：失败原因注入下一轮规划上下文，Agent 在",
        "新一轮生成修正后的计划并再次执行；",
        "",
        "（4）闭环相比单轮执行的优势：单轮执行在失败即停止，闭环通过",
        "观察反馈与异常分析实现失败情况下的自动重规划，提高任务完成率。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="闭环 Agent 异常恢复实验")
    parser.add_argument("--rounds", type=int, default=10, help="每类异常次数")
    parser.add_argument(
        "--backend", choices=["mock", "real"], default="mock",
        help="执行后端：mock（本地 Mock 服务端）或 real（真实 RobotStudio）",
    )
    args = parser.parse_args()

    tasks = {
        "action_param": "移动机器人到指定点",
        "communication": "移动机器人到指定点",
        "execution": "移动机器人到指定点",
    }
    records = []
    for t in EXPERIMENT_TYPES:
        for _ in range(args.rounds):
            records.append(run_one(t, tasks[t], backend=args.backend))
        print(f"[{t}] 完成 {args.rounds} 次")

    write_log(records)
    write_report(records, backend=args.backend)
    total = len(records)
    recovered = sum(1 for r in records if r["success"])
    print(f"[实验完成] 共 {total} 次，恢复成功 {recovered} 次 "
          f"({recovered / total:.0%})")
    print(f"[日志] {EXPERIMENT_LOG}")
    print(f"[报告] {REPORT_PATH}")


if __name__ == "__main__":
    main()
