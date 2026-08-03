# -*- coding: utf-8 -*-
"""
AI-Robot-Demo 主程序入口
========================
运行流程:
    用户输入自然语言任务
        -> LLM(llm.py) 理解任务并输出结构化 JSON 动作指令
        -> 模拟机器人(robot.py) 按指令执行动作

使用方式:
    python main.py                    # 交互模式(需要 .env 中配置 DEEPSEEK_API_KEY)
    python main.py --mock             # 离线演示模式(不调用 API，方便无 Key 测试)
    python main.py --task "把红色零件移动到检测区"   # 单次任务模式
"""

import argparse
import sys

from llm import build_planner
from robot import SimRobot


def run_once(planner, robot, task):
    """执行单次任务: 任务理解 -> 动作规划 -> 机器人执行"""
    print(f"\n[用户] {task}")

    # 1. 大语言模型: 把自然语言转换成结构化 JSON 机器人动作指令
    action = planner.plan_task(task)
    print(f"[AI 规划] {action}")

    # 2. 模拟机器人: 按 JSON 指令执行动作
    robot.execute(action)


def interactive(planner, robot):
    """交互式循环: 持续接收用户指令"""
    print("=" * 56)
    print("AI 机器人 Demo (DeepSeek 大脑 + 模拟机器人)")
    print("输入任务开始，输入 exit / quit / 退出 结束")
    print("示例: 把红色零件移动到检测区")
    print("=" * 56)
    while True:
        try:
            task = input("\n请下达任务: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break
        if not task:
            continue
        if task.lower() in ("exit", "quit", "退出"):
            print("再见!")
            break
        run_once(planner, robot, task)


def main():
    parser = argparse.ArgumentParser(
        description="AI 机器人 Demo: DeepSeek 大脑 + 模拟机器人"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用内置离线规划器(不调用 DeepSeek API)，便于无 Key 测试",
    )
    parser.add_argument(
        "--task",
        type=str,
        help='直接执行单条任务后退出，例如 --task "把红色零件移动到检测区"',
    )
    args = parser.parse_args()

    # 创建规划器(DeepSeek 或离线 Mock)
    try:
        planner = build_planner(mock=args.mock)
    except RuntimeError as exc:
        print(f"[配置错误] {exc}")
        sys.exit(1)

    # 创建模拟机器人
    robot = SimRobot()

    if args.task:
        run_once(planner, robot, args.task)
    else:
        interactive(planner, robot)


if __name__ == "__main__":
    main()
