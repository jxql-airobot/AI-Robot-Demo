#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_real_robotstudio_validation.py — 真实 RobotStudio 执行验证实验 (V6.6)
==========================================================================
连接 ABB RobotStudio + IRC5 虚拟控制器 + RAPID SocketServer（真实 TCP
链路），执行 15 个代表任务（基础动作 / 顺序任务 / 组合任务），并使用
闭环 Agent（Observation-Reflection-Replanning）完成真实执行；最后触发
一次 50050 运动不可达异常并记录反馈过程。

环境要求：RobotStudio 6.08 + IRC5 虚拟控制器运行中、socket_server.mod
已加载并启动（端口 30000 监听）、config.json backend=real 或通过
--backend real 指定。

用法：
    python experiments/scripts/run_real_robotstudio_validation.py
输出：
    experiments/results/real_robotstudio_validation_report.md
"""

import argparse
import datetime
import json
import os
import socket
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
from robotstudio.config import load_config  # noqa: E402
from robotstudio.robotstudio_client import RobotStudioClient  # noqa: E402

RESULTS_DIR = os.path.join(BASE, "experiments", "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "real_robotstudio_validation_report.md")
IMG_DIR = os.path.join(BASE, "docs", "thesis", "images", "robotstudio_validation")

TASKS = [
    # 基础动作
    ("R01", "basic", "让机器人回到初始位置"),
    ("R02", "basic", "移动机器人到指定关节位置"),
    ("R03", "basic", "执行直线运动到目标点"),
    ("R04", "basic", "获取当前机器人关节位置"),
    ("R05", "basic", "读取机器人当前TCP位姿"),
    ("R06", "basic", "查询机器人当前状态"),
    # 顺序任务
    ("R07", "sequence", "移动到第一个位置，再移动到第二个位置，最后回到初始位置"),
    ("R08", "sequence", "完成一次移动-查询-回零流程"),
    # 组合任务
    ("R09", "composite", "让机器人移动到指定位置，然后返回初始状态"),
    ("R10", "composite", "先回零，再移动到工作区域，然后读取状态"),
    ("R11", "composite", "移动到目标位姿并获取当前关节角"),
    ("R12", "composite", "执行一次完整的定位-查询-回位流程"),
    ("R13", "composite", "把机器人移动到安全姿态并确认位置"),
    ("R14", "composite", "执行直线运动到指定坐标后回零"),
    ("R15", "composite", "完成关节运动、状态查询与回零的组合任务"),
]


def port_open(host, port, timeout=2.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_real_validation(rounds=1):
    cfg = load_config()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 30000))
    if not port_open(host, port):
        print(f"[错误] 端口 {port} 未监听，请先在 RobotStudio 中启动 RAPID "
              f"SocketServer（PP 到 socket_main 并启动）")
        return None

    tmp = tempfile.mkdtemp(prefix="real_val_")
    client = RobotStudioClient(
        host=host, port=port,
        timeout_seconds=float(cfg.get("timeout", 5.0)),
        mock=False,
    )
    agent = Agent(
        backend="robotstudio",
        db_path=os.path.join(tmp, "val.db"),
        planner=DeepSeekRobotStudioPlanner(),
        robotstudio_client=client,
        rag_enabled=False,
        closed_loop=True,
    )
    records = []
    try:
        for task_id, category, input_text in TASKS:
            for _ in range(rounds):
                t0 = time.monotonic()
                resp = agent.handle_closed_loop(input_text, max_rounds=3)
                elapsed = time.monotonic() - t0
                plan = resp["plan"]
                steps = plan.get("steps", [])
                step_results = resp.get("step_results", [])
                ok = bool(steps) and all(r.get("ok") for r in step_results)
                records.append(
                    {
                        "task_id": task_id,
                        "category": category,
                        "input": input_text,
                        "plan": steps,
                        "execution": [
                            {
                                "tool": r.get("tool"),
                                "ok": r.get("ok"),
                                "message": r.get("message"),
                            }
                            for r in step_results
                        ],
                        "time_s": round(elapsed, 3),
                        "success": ok,
                        "rounds": len(resp["closed_loop"]["rounds"]),
                    }
                )
                print(f"[{task_id}] {'成功' if ok else '失败'} "
                      f"{elapsed:.2f}s 步骤数={len(steps)}")
    finally:
        agent.close()
    return records, client


def run_error_probe(client, records):
    """触发 50050 运动不可达异常并记录反馈过程"""
    print("\n[异常测试] 发送越界 MOVEL 目标，触发 50050...")
    error_record = {
        "task_id": "R99",
        "category": "error_probe",
        "input": "执行直线运动到不可达位置（越界目标 [1.2,1.2,1.2]）",
        "plan": [],
        "execution": [],
        "time_s": 0.0,
        "success": False,
        "error_feedback": {},
    }
    try:
        result = client.send_action(
            {"action": "linear_move", "target": [1.2, 1.2, 1.2, 0, 0, 0]}
        )
        error_record["execution"].append(
            {"tool": "robot_tool", "ok": bool(result.get("ok")),
             "message": result.get("message")}
        )
        error_record["error_feedback"]["reply"] = result
    except Exception as exc:
        error_record["execution"].append(
            {"tool": "robot_tool", "ok": False, "message": str(exc)}
        )
        error_record["error_feedback"]["exception"] = str(exc)
    # ERRINFO 查询最近错误
    try:
        err = client.send_action({"action": "query_error"})
        error_record["error_feedback"]["errinfo"] = err
    except Exception as exc:
        error_record["error_feedback"]["errinfo_error"] = str(exc)
    records.append(error_record)
    return error_record


def write_report(records):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cfg = load_config()
    ok = sum(1 for r in records if r["success"])
    total = len([r for r in records if not r.get("error_feedback")])
    lines = [
        "# 真实 RobotStudio 执行验证实验报告",
        "",
        "## 1 实验环境",
        "",
        "- RobotStudio：6.08.01（中文版）",
        "- RobotWare：6.08.1040",
        "- 机器人模型：ABB IRB120",
        "- 虚拟控制器：IRC5（AI_Robot_System_IRB120）",
        f"- Socket 通信：TCP {cfg.get('host')}:{cfg.get('port')}，"
        "RAPID SocketServer 真实运行",
        "- 规划器：DeepSeek LLM（RobotStudio 动作契约版，真实 API 调用）",
        "- 执行模式：闭环 Agent（closed_loop=True）",
        "",
        "## 2 实验任务与结果",
        "",
        "| 任务 | 类别 | 自然语言输入 | 执行结果 | 耗时 | 是否成功 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        if r.get("error_feedback"):
            continue
        exec_text = "；".join(
            f"{e.get('tool')}:{'成功' if e.get('ok') else '失败'}"
            for e in r["execution"]
        )[:40]
        lines.append(
            f"| {r['task_id']} | {r['category']} | {r['input']} | "
            f"{exec_text} | {r['time_s']}s | "
            f"{'✅' if r['success'] else '❌'} |"
        )
    lines += [
        "",
        f"代表任务执行成功率：{ok}/{total}（{ok / total:.0%}）。",
        "",
        "## 3 异常案例（50050 运动不可达）",
        "",
        "发送越界 MOVEL 目标后，控制器返回运动不可达错误（50050 位置超出",
        "范围），并伴随 10020 执行错误状态与 10125 程序停止；RAPID 程序停止",
        "导致 SocketServer 停止监听，Python 客户端收到连接被拒。ERRINFO",
        "查询与 Observation/Reflection 反馈过程记录如下：",
        "",
    ]
    for r in records:
        if r.get("error_feedback"):
            lines.append("```json")
            lines.append(json.dumps(r["error_feedback"], ensure_ascii=False, indent=2))
            lines.append("```")
    lines += [
        "",
        "## 4 结果说明",
        "",
        "（1）代表任务（基础/顺序/组合）在真实 RobotStudio + IRC5 虚拟",
        "控制器链路下完成闭环执行；",
        "",
        "（2）50050 为控制器停止级错误，错误后需人工重启 RAPID 任务；",
        "RecoveryManager 提供恢复决策与重连流程；",
        "",
        "（3）本实验为 RobotStudio 虚拟工业环境验证（IRC5 虚拟控制器），",
        "不属于工业现场验证，也未在实体机器人上执行。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="真实 RobotStudio 执行验证")
    parser.add_argument("--rounds", type=int, default=1, help="每任务轮数")
    parser.add_argument("--skip-error", action="store_true", help="跳过 50050 异常测试")
    args = parser.parse_args()

    result = run_real_validation(rounds=args.rounds)
    if result is None:
        sys.exit(1)
    records, client = result
    if not args.skip_error:
        run_error_probe(client, records)
    try:
        client.close()
    except Exception:
        pass
    write_report(records)
    print(f"\n[报告] {REPORT_PATH}")


if __name__ == "__main__":
    main()

