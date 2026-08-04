#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats.py — 实验日志统计脚本
============================
读取统一实验日志（experiments/results/runtime_logs.json，JSON Lines），输出：
  - 总任务数 / 成功率
  - 平均响应时间（可含规划/执行分解）
  - 错误次数与错误信息 TOP
  - 可按 task_type / backend 分组统计

用法：
    python experiments/scripts/stats.py
    python experiments/scripts/stats.py --log experiments/results/runtime_logs.json
    python experiments/scripts/stats.py --group task_type
    python experiments/scripts/stats.py --group backend
"""

import argparse
import json
import os

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"
)
DEFAULT_LOG = os.path.join(RESULTS_DIR, "runtime_logs.json")


def load_records(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def summarize(records):
    total = len(records)
    success = sum(1 for r in records if r.get("success"))
    errors = [r.get("error", "") for r in records if not r.get("success") and r.get("error")]
    times = [
        r.get("response_time") for r in records if r.get("response_time") is not None
    ]
    plan_times = [
        r.get("planning_time") for r in records if r.get("planning_time") is not None
    ]
    exec_times = [
        r.get("execution_time") for r in records if r.get("execution_time") is not None
    ]

    def mean(vals):
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "total": total,
        "success_rate": round(success / total, 4) if total else 0.0,
        "avg_response_s": mean(times),
        "avg_plan_s": mean(plan_times),
        "avg_exec_s": mean(exec_times),
        "error_count": total - success,
        "errors": errors,
    }


def print_summary(tag, s):
    print(f"[{tag}] 任务数={s['total']} 成功率={s['success_rate']:.1%} "
          f"平均响应={s['avg_response_s']}s "
          f"(规划 {s['avg_plan_s']}s / 执行 {s['avg_exec_s']}s) "
          f"错误={s['error_count']} 次")
    if s["errors"]:
        from collections import Counter

        for msg, cnt in Counter(s["errors"]).most_common(5):
            print(f"    错误×{cnt}: {msg[:90]}")


def main():
    parser = argparse.ArgumentParser(description="实验日志统计")
    parser.add_argument("--log", default=DEFAULT_LOG, help="runtime_logs.json 路径")
    parser.add_argument("--group", default=None, choices=["task_type", "backend", "none"],
                        help="分组维度")
    args = parser.parse_args()

    records = load_records(args.log)
    if not records:
        print(f"[统计] 日志为空或不存在: {args.log}")
        return
    print(f"[统计] 日志: {args.log}（共 {len(records)} 条）")
    print_summary("全部", summarize(records))

    if args.group and args.group != "none":
        groups = {}
        for r in records:
            key = r.get(args.group, "-")
            groups.setdefault(key, []).append(r)
        for key in sorted(groups):
            print_summary(f"{args.group}={key}", summarize(groups[key]))


if __name__ == "__main__":
    main()
