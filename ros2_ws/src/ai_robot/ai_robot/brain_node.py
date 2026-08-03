#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brain_node.py — AI 大脑节点 (ROS2)
==================================
V3 新增: 让 V1/V2 的 AI 大脑成为 ROS2 节点。

流程:
    订阅 /ai_robot/task (自然语言任务)
      -> 是"记住"指令? 保存到 SQLite, 并发布 learn_station 让机器人学新位置
      -> 否则: 查询记忆 -> DeepSeek/Mock 规划
      -> 发布 /ai_robot/action (JSON 动作指令)

复用 V1/V2 代码: llm.py (AI 大脑), memory.py (SQLite 记忆), 一行未改。
"""

import json
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from ai_robot import llm
from ai_robot import memory as memory_mod

# 记忆数据库和 .env 的固定位置
DB_PATH = os.path.expanduser("~/ros2_ws/database.db")
ENV_PATH = os.path.expanduser("~/.ai_robot/.env")


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


class BrainNode(Node):
    """AI 大脑节点: 任务 -> 记忆 -> 规划 -> 动作话题"""

    def __init__(self):
        super().__init__("ai_brain")

        # 加载 DeepSeek API Key
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)

        # 记忆系统 (SQLite)
        self.memory = memory_mod.MemoryStore(DB_PATH)

        # 规划器: 有有效 Key 用 DeepSeek, 否则离线 Mock
        cfg = llm.load_config()
        has_key = cfg["api_key"].startswith("sk-") and cfg["api_key"].isascii()
        self.planner = llm.build_planner(mock=not has_key)
        mode = "DeepSeek" if has_key else "Mock 离线"
        self.get_logger().info(f"AI Brain 启动, 规划器: {mode}")

        # 话题: 任务输入 / 动作输出 / 状态
        self.sub = self.create_subscription(
            String, "/ai_robot/task", self.on_task, 10
        )
        self.pub_action = self.create_publisher(String, "/ai_robot/action", 10)
        self.pub_status = self.create_publisher(String, "/ai_robot/status", 10)

    def on_task(self, msg):
        task = msg.data
        self.get_logger().info(f"[任务] {task}")

        # 1. "记住"指令: 存记忆 + 通知机器人学新位置
        parsed = parse_memory_command(task)
        if parsed:
            topic, content = parsed
            category = classify_memory(topic, content)
            self._safe_remember(topic, content, category)
            self.pub_status.publish(
                String(data=f"已保存记忆: {topic} -> {content} ({category})")
            )
            if category == "环境信息":
                self._publish_action(
                    {
                        "action": "learn_station",
                        "name": topic,
                        "description": content,
                    }
                )
            return

        # 2. 记忆查询
        rows = self._safe_search(task)
        memory_text = self.memory.format_prompt(rows)
        self.pub_status.publish(String(data=f"检索到 {len(rows)} 条相关记忆"))
        for topic, content, category in rows:
            self.get_logger().info(f"  记忆: {topic} -> {content}")

        # 3. AI 规划 (结合记忆)
        action = self.planner.plan_task(task, memory_text)
        self.get_logger().info(f"[AI 规划] {action}")

        # 4. 发布动作给机器人控制器
        self._publish_action(action)

    def _publish_action(self, action):
        self.pub_action.publish(String(data=json.dumps(action, ensure_ascii=False)))

    def _safe_remember(self, topic, content, category):
        """记忆写入(容错): 数据库文件被误删时自动重建再写"""
        try:
            self.memory.remember(topic, content, category)
        except Exception as exc:
            self.get_logger().warn(f"记忆写入失败({exc}), 自动重建数据库后重试")
            self.memory._init_db()
            self.memory.remember(topic, content, category)

    def _safe_search(self, task):
        """记忆查询(容错): 数据库文件被误删时自动重建再查"""
        try:
            return self.memory.search(task)
        except Exception as exc:
            self.get_logger().warn(f"记忆查询失败({exc}), 自动重建数据库后重试")
            self.memory._init_db()
            return self.memory.search(task)


def main(args=None):
    rclpy.init(args=args)
    node = BrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
