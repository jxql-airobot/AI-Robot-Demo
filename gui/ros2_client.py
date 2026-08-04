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
"""

import json
import math
import os
import sys
import threading
import time

# 保证 config.py 可被 import（gui 目录加入 sys.path）
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
if GUI_DIR not in sys.path:
    sys.path.insert(0, GUI_DIR)

import rclpy  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402
from rclpy.node import Node  # noqa: E402
from std_msgs.msg import String  # noqa: E402

from config import (  # noqa: E402
    GUI_NODE_NAME,
    TOPIC_ODOM,
    TOPIC_STATUS,
    TOPIC_TASK,
    TOPIC_VISION,
)


class Ros2Client:
    """ROS2 客户端：发布任务 + 订阅状态/视觉/里程计"""

    def __init__(self):
        if not rclpy.ok():
            rclpy.init(args=[])
        self.node = Node(GUI_NODE_NAME)
        self.pub_task = self.node.create_publisher(String, TOPIC_TASK, 10)
        self.node.create_subscription(String, TOPIC_STATUS, self._on_status, 10)
        self.node.create_subscription(String, TOPIC_VISION, self._on_vision, 10)
        self.node.create_subscription(Odometry, TOPIC_ODOM, self._on_odom, 10)

        self._lock = threading.Lock()
        self._status = None   # (text, 时间戳)
        self._vision = None   # (dict, 时间戳)
        self._odom = None     # (dict, 时间戳)
        self._stop = False

        # 后台线程持续 spin，保证回调一直执行；主线程只读快照
        self._spin_thread = threading.Thread(
            target=self._spin, name="gui-rclpy-spin", daemon=True
        )
        self._spin_thread.start()

    # ---------- 后台 spin ----------

    def _spin(self):
        while not self._stop and rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.05)

    # ---------- 订阅回调（只更新快照，不做业务逻辑） ----------

    def _on_status(self, msg):
        with self._lock:
            self._status = (msg.data, time.time())

    def _on_vision(self, msg):
        try:
            data = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError):
            data = {"raw": msg.data}
        with self._lock:
            self._vision = (data, time.time())

    def _on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        v = msg.twist.twist
        snapshot = {
            "x": round(p.x, 3),
            "y": round(p.y, 3),
            "yaw": round(yaw, 3),
            "linear_x": round(v.linear.x, 3),
            "angular_z": round(v.angular.z, 3),
        }
        with self._lock:
            self._odom = (snapshot, time.time())

    # ---------- 对外接口 ----------

    def send_task(self, text):
        """发送一条自然语言任务到 /ai_robot/task"""
        self.pub_task.publish(String(data=text))

    def get_status(self):
        """返回最近一条状态反馈 (text, 时间戳)，无则 None"""
        with self._lock:
            return self._status

    def get_vision(self):
        """返回最近一次视觉识别结果 dict，无则 None"""
        with self._lock:
            return self._vision

    def get_odom(self):
        """返回最近一次里程计快照 dict，无则 None"""
        with self._lock:
            return self._odom

    def close(self):
        """释放节点资源"""
        self._stop = True
        if hasattr(self, "node"):
            self.node.destroy_node()
        # 等后台 spin 线程退出，避免进程结束时线程仍在 rclpy 上下文中
        if hasattr(self, "_spin_thread") and self._spin_thread.is_alive():
            self._spin_thread.join(timeout=2.0)
