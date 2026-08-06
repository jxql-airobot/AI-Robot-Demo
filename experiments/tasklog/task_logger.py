#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_logger.py — 统一实验日志系统 (V6.2)
========================================
Agent 每次任务执行结束后自动记录一条 JSON 记录，Gazebo / RobotStudio /
Local / Mock 各后端统一格式，供论文实验数据统计。

统一记录字段（论文实验 schema）：
    task_id, task_type, input, agent_enabled, rag_enabled, generated_plan,
    execution_result, success, response_time, error
扩展字段（保留以便深入分析）：
    timestamp, planner_output, tool_calls, backend,
    planning_time, execution_time

输出：experiments/results/runtime_logs.json（JSON Lines，每行一条记录）

用法：
    from experiments.tasklog import TaskLogger
    TaskLogger().log(**record)
    或命令行清空日志：python -m experiments.tasklog.task_logger --clear
"""

import argparse
import datetime
import json
import os
import threading
import uuid

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"
)
DEFAULT_LOG_PATH = os.path.join(RESULTS_DIR, "runtime_logs.json")


class TaskLogger:
    """追加式 JSON Lines 日志器（线程安全）"""

    def __init__(self, path=None):
        self.path = path or os.environ.get("AI_ROBOT_RUNTIME_LOG", DEFAULT_LOG_PATH)
        self._lock = threading.Lock()

    def log(self, **fields):
        """写入一条任务记录（任何字段缺失都补默认值，日志失败不影响 Agent）"""
        record = {
            "task_id": fields.get("task_id")
            or f"task-{int(datetime.datetime.now().timestamp() * 1000)}-{uuid.uuid4().hex[:6]}",
            "task_type": fields.get("task_type", "general"),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "input": fields.get("input", fields.get("user_input", "")),
            "agent_enabled": bool(fields.get("agent_enabled", True)),
            "rag_enabled": bool(fields.get("rag_enabled", False)),
            "planner_output": fields.get("planner_output"),
            "generated_plan": fields.get("generated_plan"),
            "tool_calls": fields.get("tool_calls") or [],
            "backend": fields.get("backend", ""),
            "execution_result": fields.get("execution_result")
            or fields.get("execution_steps")
            or [],
            "success": bool(fields.get("success", False)),
            "error": fields.get("error", fields.get("error_message", "")),
            "error_code": fields.get("error_code"),
            "response_time": fields.get("response_time"),
            "planning_time": fields.get("planning_time"),
            "execution_time": fields.get("execution_time"),
        }
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with self._lock:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # 日志失败绝不影响 Agent 主流程
            pass

    def clear(self):
        """清空日志文件"""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8"):
                pass
        except Exception:
            pass


def clear_runtime_log(path=None):
    """便捷清空函数"""
    TaskLogger(path=path).clear()


def main():
    parser = argparse.ArgumentParser(description="统一实验日志工具")
    parser.add_argument("--clear", action="store_true", help="清空 runtime_logs.json")
    parser.add_argument("--path", default=None, help="日志文件路径")
    args = parser.parse_args()
    logger = TaskLogger(path=args.path)
    if args.clear:
        logger.clear()
        print(f"[日志] 已清空: {logger.path}")
    else:
        print(f"[日志] 当前文件: {logger.path}")
        if os.path.exists(logger.path):
            count = sum(1 for _ in open(logger.path, encoding="utf-8"))
            print(f"[日志] 记录条数: {count}")


if __name__ == "__main__":
    main()
