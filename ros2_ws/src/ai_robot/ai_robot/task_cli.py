#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_cli.py — 任务输入终端 (ROS2)
=================================
V3 新增: 用户在终端输入自然语言任务,
发布到 /ai_robot/task, 并打印 /ai_robot/status 反馈。
"""

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
                break
            if not task:
                continue
            if task.lower() in ("exit", "quit", "退出"):
                break
            self.pub.publish(String(data=task))
            rclpy.spin_once(self, timeout_sec=0.2)


def main(args=None):
    rclpy.init(args=args)
    node = TaskCli()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
