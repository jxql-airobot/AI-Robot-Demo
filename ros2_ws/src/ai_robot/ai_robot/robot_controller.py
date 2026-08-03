#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robot_controller.py — 机器人控制器节点 (ROS2)
============================================
V3 新增: 把 V1/V2 的模拟机器人变成 ROS2 节点。

流程:
    订阅 /ai_robot/action (JSON 动作指令)
      -> 用世界模型 (robot.py) 执行
      -> 发布 /ai_robot/status (工作台状态)

未来: 本节点的 robot.execute() 可以换成真实的机械臂驱动
(例如发布到 ROS2 的 /arm_joint_commands 话题), 上层代码不变。
"""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from ai_robot.robot import SimRobot


class RobotController(Node):
    """机器人控制器: 订阅动作 -> 执行 -> 发布状态"""

    def __init__(self):
        super().__init__("robot_controller")
        self.robot = SimRobot()
        self.sub = self.create_subscription(
            String, "/ai_robot/action", self.on_action, 10
        )
        self.pub_status = self.create_publisher(String, "/ai_robot/status", 10)
        self.get_logger().info("Robot Controller 启动")

    def on_action(self, msg):
        try:
            action = json.loads(msg.data)
        except json.JSONDecodeError:
            self._publish_status(f"动作解析失败: {msg.data}")
            return

        self.get_logger().info(f"[动作] {action}")

        # 特殊动作: 从记忆中学到新位置
        if action.get("action") == "learn_station":
            name = action.get("name", "")
            desc = action.get("description", "")
            self.robot.add_station(name, description=desc)
            self._publish_status(f"学会新位置: {name} ({desc})")
            return

        # V3 兜底: 用户只说"零件"没指定颜色时, 自动选第一个可用零件
        obj = action.get("object", "")
        if obj and "零件" in obj and not self._part_exists(obj):
            for parts in self.robot.workspace.values():
                if parts:
                    action["object"] = parts[0]
                    self.get_logger().info(
                        f"  零件未指定具体颜色, 自动选择: {parts[0]}"
                    )
                    break

        # 普通动作: 世界模型执行 (move/pick/place/scan/status)
        self.robot.execute(action)
        state = {k: list(v) for k, v in self.robot.workspace.items()}
        self._publish_status("工作台: " + json.dumps(state, ensure_ascii=False))

    def _part_exists(self, obj):
        """判断零件是否在工作台或夹爪中"""
        if self.robot.gripper == obj or any(
            obj in parts for parts in self.robot.workspace.values()
        ):
            return True
        return False

    def _publish_status(self, text):
        self.pub_status.publish(String(data=text))


def main(args=None):
    rclpy.init(args=args)
    node = RobotController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
