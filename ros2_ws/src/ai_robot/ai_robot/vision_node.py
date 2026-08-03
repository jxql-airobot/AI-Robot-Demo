#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_node.py — 视觉感知节点 (V4)
==================================
订阅 /camera/image_raw (Gazebo 相机图像)
  -> OpenCV HSV 颜色识别 红色/蓝色/绿色零件
  -> 发布 /ai_robot/vision (JSON 检测结果)
  -> 检测结果写入记忆库 (物体信息), 供 AI 大脑查询

依赖: opencv-python-headless, cv_bridge (ROS2 自带)
"""

import json
import os

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from ai_robot import memory as memory_mod

DB_PATH = os.path.expanduser("~/ros2_ws/database.db")

# 零件颜色 -> HSV 范围 (红色在色环两端, 需要两段范围)
COLOR_RANGES = {
    "红色零件": [((0, 100, 80), (10, 255, 255)), ((160, 100, 80), (180, 255, 255))],
    "蓝色零件": [((100, 100, 80), (130, 255, 255))],
    "绿色零件": [((40, 80, 80), (85, 255, 255))],
}
MIN_AREA = 100  # 最小色块面积(像素), 过滤噪声


class VisionNode(Node):
    """视觉节点: 相机图像 -> 颜色识别 -> 记忆"""

    def __init__(self):
        super().__init__("vision_node")
        self.bridge = CvBridge()
        self.memory = memory_mod.MemoryStore(DB_PATH)
        self.sub = self.create_subscription(
            Image, "/camera/image_raw", self.on_image, 5
        )
        self.pub_vision = self.create_publisher(String, "/ai_robot/vision", 5)
        self.last_detections = None
        self.frame_count = 0
        self.get_logger().info("Vision Node 启动 (OpenCV 颜色识别)")

    def on_image(self, msg):
        # 相机 5fps, 每 15 帧处理一次(~3秒), 避免频繁写库
        self.frame_count += 1
        if self.frame_count % 15 != 0:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as exc:
            self.get_logger().warn(f"图像转换失败: {exc}")
            return

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detections = {}
        h, w = frame.shape[:2]
        for name, ranges in COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in ranges:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            best = max(contours, key=cv2.contourArea, default=None)
            if best is not None and cv2.contourArea(best) > MIN_AREA:
                x, y, bw, bh = cv2.boundingRect(best)
                cx = x + bw / 2
                if cx < w / 3:
                    zone = "左侧区域"
                elif cx < 2 * w / 3:
                    zone = "中间区域"
                else:
                    zone = "右侧区域"
                detections[name] = zone

        # 检测结果变化时才发布并写记忆
        if detections != self.last_detections:
            self.last_detections = detections
            text = json.dumps({"parts": detections}, ensure_ascii=False)
            self.pub_vision.publish(String(data=text))
            self.get_logger().info(f"[视觉] {text}")
            for name, zone in detections.items():
                self.memory.remember(name, f"{zone}（视觉识别）", "物体信息")
            self.get_logger().info("检测结果已写入记忆")


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
