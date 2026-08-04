#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ros2_client.py — ROS2 客户端封装 (V5.1)
=======================================
Streamlit GUI 与 ROS2 仿真系统之间的通信桥：
  - 发布 /ai_robot/task   （用户自然语言任务 -> AI 大脑）
  - 订阅 /ai_robot/status （机器人状态反馈）
  - 订阅 /ai_robot/vision （视觉识别结果）
  - 订阅 /odom            （Gazebo 里程计 -> 机器人位置）

设计要点：
  - 独立线程 spin，主线程只读写线程安全的最新快照
  - 只做客户端，不修改任何现有节点/话题
  - 视觉第一版只取识别结果文本（/ai_robot/vision），不做实时视频流（后续迭代）

【骨架阶段】第二步实现完整通信逻辑。
"""

import threading


class Ros2Client:
    """ROS2 客户端：发布任务 + 订阅状态/视觉/里程计"""

    def __init__(self):
        self._lock = threading.Lock()
        # TODO(第二步): 创建 rclpy 节点、发布器/订阅器、后台 spin 线程

    def send_task(self, text):
        """发送一条自然语言任务到 /ai_robot/task"""
        raise NotImplementedError("第二步实现")

    def get_status(self):
        """返回最近一条状态反馈 (text, 时间戳)，无则 None"""
        raise NotImplementedError("第二步实现")

    def get_vision(self):
        """返回最近一次视觉识别结果 dict，无则 None"""
        raise NotImplementedError("第二步实现")

    def get_odom(self):
        """返回最近一次里程计快照 dict，无则 None"""
        raise NotImplementedError("第二步实现")

    def close(self):
        """释放节点资源"""
        raise NotImplementedError("第二步实现")
