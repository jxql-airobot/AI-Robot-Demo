#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_cli.py — Agent 终端入口 (V5.2)
====================================
与 GUI 共用同一个 Agent，方便独立测试。

用法：
  python agent/agent_cli.py            # ROS2 模式（需仿真系统已启动）
  python agent/agent_cli.py --local    # 本地模式（复用 SimRobot，不需要 ROS2）
  python agent/agent_cli.py --mock     # 强制离线 Mock 规划器
"""

import argparse
import sys

sys.path.insert(0, __file__.rsplit("agent", 1)[0].rstrip("\\/"))

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402


def print_response(resp):
    """把 AgentResponse 格式化成可读文本（任务分析/目标/执行步骤/当前状态）"""
    plan = resp["plan"]
    print(f"任务分析：{plan.get('task_analysis', '')}")
    print(f"目标：{plan.get('goal', '')}")
    print("执行步骤：")
    for index, step in enumerate(plan.get("steps", []), 1):
        purpose = step.get("purpose", "")
        tool = step.get("tool", "")
        print(f"  {index}. {purpose}（工具：{tool}）")
    print(f"当前状态：{plan.get('current_state', '')}")
    print("--- 执行结果 ---")
    for r in resp["step_results"]:
        print(f"[步骤{r.get('step')}][{r.get('tool')}] {r.get('message', '')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="AI Robot 智能体 Agent 终端")
    parser.add_argument("--local", action="store_true", help="本地模式（SimRobot，不需要 ROS2）")
    parser.add_argument("--mock", action="store_true", help="强制离线 Mock 规划器")
    args = parser.parse_args()

    backend = "local" if args.local else "ros2"
    planner = MockPlanPlanner() if args.mock else None
    agent = Agent(backend=backend, planner=planner)
    mode = f"{backend} 模式" + (" + Mock 规划器" if args.mock else "")
    print(f"AI Robot 智能体 Agent 终端 (V5.2, {mode})")
    print("输入任务开始，输入 exit / quit / 退出 结束")
    try:
        while True:
            task = input("> ").strip()
            if not task:
                continue
            if task.lower() in ("exit", "quit", "退出"):
                print("再见!")
                break
            resp = agent.handle(task)
            print_response(resp)
    except (EOFError, KeyboardInterrupt):
        print("\n再见!")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
