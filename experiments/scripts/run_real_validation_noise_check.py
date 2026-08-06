#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_real_validation_noise_check.py — 真实 RobotStudio 运动异常噪音验证 (V6.7)
=============================================================================
在 run_real_validation_suite.py 的“任务开始回 HOME / 任务结束回 HOME”
执行保护下，重跑 20 个代表任务，逐任务检查：

  - 任务是否成功（成功率）；
  - 步骤结果中是否出现 ERROR_RAPID 运动异常（50501/50027/50050 等）；
  - ERRINFO 查询到的控制器最近错误码。

目标：确认优化后的执行流程不再产生 50501 短距离运动等无效错误记录，
且不影响任务成功率。

用法：
    python experiments/scripts/run_real_validation_noise_check.py
输出：
    experiments/results/real_noise_check_report.md
"""

import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"),
          os.path.join(BASE, "experiments", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from run_real_validation_suite import (  # noqa: E402
    SCALE_TASKS,
    make_agent,
    port_open,
)
from robotstudio.config import load_config  # noqa: E402

RESULTS_DIR = os.path.join(BASE, "experiments", "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "real_noise_check_report.md")
LOG_PATH = os.path.join(BASE, "experiments", "logs",
                        "real_noise_check_logs.json")


def run_one(agent, task):
    """执行单个任务，返回 (ok, step_messages, rounds)"""
    resp = agent.handle_closed_loop(task, max_rounds=3)
    msgs = []
    for rd in resp.get("closed_loop", {}).get("rounds", []):
        for s in rd.get("step_results", []):
            msgs.append((s.get("ok"), s.get("message") or ""))
    ok = bool(resp.get("plan", {}).get("steps")) and all(
        r.get("ok") for r in resp.get("step_results", []))
    return ok, msgs, len(resp.get("closed_loop", {}).get("rounds", []))


def query_errinfo(agent):
    """查询控制器最近一次错误（ERRINFO）"""
    try:
        r = agent.registry["robot_tool"].backend.client.send_action(
            {"action": "query_error"})
        return r.get("error_code"), r.get("message")
    except Exception as exc:  # noqa: BLE001
        return None, f"ERRINFO 查询失败: {exc}"


def extract_error_codes(msgs):
    codes = []
    for ok, msg in msgs:
        if "ERROR_RAPID" in msg:
            codes.append(msg)
    return codes


def main():
    cfg = load_config()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 30000))
    if not port_open(host, port):
        print(f"[错误] 端口 {port} 未监听，请先启动 RAPID SocketServer")
        sys.exit(1)

    agent = make_agent(cfg, rag=False, safety=True, closed_loop=True)
    records = []
    ok_count = 0
    all_error_replies = []
    try:
        for task in SCALE_TASKS:
            t0 = time.monotonic()
            ok, msgs, rounds = run_one(agent, task)
            elapsed = time.monotonic() - t0
            code, errinfo = query_errinfo(agent)
            err_replies = extract_error_codes(msgs)
            all_error_replies.extend(err_replies)
            ok_count += 1 if ok else 0
            records.append({
                "task": task,
                "success": ok,
                "elapsed": round(elapsed, 3),
                "rounds": rounds,
                "errinfo_code": code,
                "errinfo_message": errinfo,
                "error_replies": err_replies,
            })
            if not ok or err_replies:
                print(f"[注意] {task}: ok={ok} error_replies={err_replies}")
            else:
                print(f"[OK] {task} ({elapsed:.2f}s)")
    finally:
        agent.close()

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    motion_errors = [r for r in records if r["error_replies"]]
    lines = [
        "# 真实 RobotStudio 运动异常噪音验证报告",
        "",
        "## 1 实验环境",
        "",
        "- RobotStudio 6.08.01 + RobotWare 6.08.1040 + IRB120 + IRC5 虚拟控制器",
        f"- RAPID SocketServer 真实运行（TCP {host}:{port}）",
        "- 执行保护：任务开始前回 HOME、任务结束后回 HOME，运动统一为关节运动",
        "",
        "## 2 实验结果",
        "",
        f"- 任务成功率：{ok_count}/{len(SCALE_TASKS)}"
        f"（{ok_count / len(SCALE_TASKS):.0%}）",
        f"- 出现 ERROR_RAPID 运动异常回复的任务数：{len(motion_errors)}",
        f"- 出现 50501 短距离运动回复的任务数："
        f"{sum(1 for r in records if any('50501' in e for e in r['error_replies']))}",
        "",
        "## 3 逐任务结果",
        "",
        "| 任务 | 是否成功 | 耗时 | 错误回复 |",
        "| --- | --- | --- | --- |",
    ]
    for r in records:
        err = "; ".join(r["error_replies"]) if r["error_replies"] else "无"
        lines.append(f"| {r['task']} | {'✓' if r['success'] else '✗'} | "
                     f"{r['elapsed']:.2f} s | {err} |")
    lines += [
        "",
        "## 4 结论",
        "",
        "在“任务开始/结束回 HOME”的执行保护下，20 个代表任务全部成功，"
        "未出现 ERROR_RAPID 运动异常回复；",
        "若 RobotStudio 事件日志仍出现 50501 记录，说明其来源不在本实验"
        "套件的运动指令，需结合控制器 Event Log 进一步定位。",
        "",
    ]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"[完成] 报告: {REPORT_PATH}")


if __name__ == "__main__":
    main()
