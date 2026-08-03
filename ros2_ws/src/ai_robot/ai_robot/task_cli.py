#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_cli.py — 任务输入终端 (ROS2)
=================================
V3 新增: 用户在终端输入自然语言任务,
发布到 /ai_robot/task, 并打印 /ai_robot/status 反馈。

每条任务发出后, 终端会等待状态反馈全部打印完(连续 1.5 秒无新状态),
再接收下一条命令, 保证显示顺序和任务一一对应。
"""

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TaskCli(Node):
    def __init__(self):
        super().__init__("task_cli")
        self.pub = self.create_publisher(String, "/ai_robot/task", 10)
        self.create_subscription(String, "/ai_robot/status", self.on_status, 10)
        print("AI Robot Demo V3 终端 (输入任务, exit 退出)")
        print("示例: 把红色零件移动到检测区 / 记住：A区域在生产线左侧")

    def on_status(self, msg):
        print(f"[状态] {msg.data}", flush=True)

    def run(self):
        while rclpy.ok():
            try:
                task = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见!")
                break
            if not task:
                continue
            if task.lower() in ("exit", "quit", "退出"):
                print("再见!")
                break
            self.pub.publish(String(data=task))
            # 等待状态反馈: 连续 1.5 秒没有新状态就认为本轮完成(最多等 20 秒)
            last_status_time = time.monotonic()
            deadline = time.monotonic() + 20
            while rclpy.ok() and time.monotonic() < deadline:
                got = rclpy.spin_once(self, timeout_sec=0.1)
                if got:
                    last_status_time = time.monotonic()
                if time.monotonic() - last_status_time > 1.5:
                    break


def main(args=None):
    rclpy.init(args=args)
    node = TaskCli()
    try:
        node.run()
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass
