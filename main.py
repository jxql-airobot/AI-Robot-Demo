# -*- coding: utf-8 -*-
"""
AI-Robot-Demo 主程序入口 (V2: 加入 Memory 记忆系统)
===================================================
V2 运行流程:
    用户输入
        -> 是"记住"指令? 直接保存到 SQLite，不调用 AI
        -> 否则: Memory 查询相关记忆
        -> 相关记忆 + 用户任务一起发给 LLM(llm.py)
        -> LLM 输出结构化 JSON 动作指令
        -> 模拟机器人(robot.py) 按指令执行动作

使用方式:
    python main.py                    # 交互模式(需要 .env 中配置 DEEPSEEK_API_KEY)
    python main.py --mock             # 离线演示模式(不调用 API，方便无 Key 测试)
    python main.py --task "把零件送到A区域"   # 单次任务模式
"""

import argparse
import sys

from llm import build_planner, load_config
from memory import MemoryStore
from robot import SimRobot


def classify_memory(topic, content):
    """根据关键词给记忆分类: 环境信息 / 物体信息 / 用户知识"""
    text = topic + content
    if any(k in text for k in ("区域", "位置", "车间", "工位", "侧", "线", "台")):
        return "环境信息"
    if any(k in text for k in ("零件", "物体", "物品", "工具", "材料")):
        return "物体信息"
    return "用户知识"


def parse_memory_command(text):
    """解析"记住"指令: 记住：A区域在生产线左侧 -> (A区域, 生产线左侧)"""
    if not (text.startswith("记住") or text.startswith("记忆")):
        return None
    body = text[2:].lstrip("：:，, ")
    for sep in ("=", "是", "在", "位于"):
        if sep in body:
            topic, content = body.split(sep, 1)
            topic = topic.strip()
            content = content.strip()
            if topic and content:
                return topic, content
    return None


def run_once(planner, robot, memory, task):
    """执行单次任务: 记忆 -> 任务理解 -> 动作规划 -> 机器人执行"""
    print(f"\n[用户] {task}")

    # 1. "记住"指令: 直接写入记忆，不调用 AI
    parsed = parse_memory_command(task)
    if parsed:
        topic, content = parsed
        category = classify_memory(topic, content)
        memory.remember(topic, content, category)
        if category == "环境信息":
            robot.add_station(topic, description=content)
        print(f"[记忆] 已保存: {topic} -> {content}（{category}）")
        return

    # 2. Memory 查询: 找出与任务相关的记忆
    rows = memory.search(task)
    memory_text = memory.format_prompt(rows)
    print(f"[记忆] 检索到 {len(rows)} 条相关记忆")
    for topic, content, category in rows:
        print(f"        {topic} -> {content}（{category}）")

    # 3. 大语言模型: 结合记忆把自然语言转换成 JSON 动作指令
    action = planner.plan_task(task, memory_text)
    print(f"[AI 规划] {action}")

    # 4. 模拟机器人: 按 JSON 指令执行动作
    robot.execute(action)


def interactive(planner, robot, memory):
    """交互式循环: 持续接收用户指令"""
    print("=" * 56)
    print("AI 机器人 Demo V2 (DeepSeek 大脑 + Memory + 模拟机器人)")
    print("输入任务开始，输入 exit / quit / 退出 结束")
    print("示例: 记住：A区域在生产线左侧 / 把零件送到A区域")
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
        run_once(planner, robot, memory, task)


def choose_mode(force_mock):
    """决定运行模式:
    - 命令行加了 --mock，强制离线演示模式
    - 否则自动检测 .env 里是否有有效 API Key:
      有 -> DeepSeek 真实模式；没有 -> 自动降级为离线演示模式
    """
    if force_mock:
        return True, "离线演示模式(Mock，不调用 API)"
    key = load_config().get("api_key", "")
    if key.startswith("sk-") and key.isascii():
        return False, "DeepSeek 真实模式"
    return True, "离线演示模式(未检测到有效 API Key，自动降级)"


def main():
    parser = argparse.ArgumentParser(
        description="AI 机器人 Demo V2: DeepSeek 大脑 + Memory + 模拟机器人"
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

    # 自动选择模式(也可用 --mock 强制离线)
    mock, mode_text = choose_mode(args.mock)
    print(f"[模式] {mode_text}")

    # 创建规划器(DeepSeek 或离线 Mock)
    try:
        planner = build_planner(mock=mock)
    except RuntimeError as exc:
        print(f"[配置错误] {exc}")
        sys.exit(1)

    # 创建模拟机器人和记忆系统
    robot = SimRobot()
    memory = MemoryStore()

    # V2: 启动时把记忆中学到的环境位置教给机器人(跨会话记忆)
    for topic, content, category in memory.all_memories():
        if category == "环境信息":
            robot.add_station(topic, description=content)

    if args.task:
        run_once(planner, robot, memory, args.task)
    else:
        interactive(planner, robot, memory)


if __name__ == "__main__":
    main()
