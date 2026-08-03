#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robot_controller.py — 机器人控制器节点 (ROS2)
============================================
V3 新增: 把 V1/V2 的模拟机器人变成 ROS2 节点。
V4 增强: 同时发布 /cmd_vel, 让 Gazebo 仿真机器人物理上开往目标位置。

流程:
    订阅 /ai_robot/action (JSON 动作指令)
      -> 用世界模型 (robot.py) 执行
      -> 发布 /ai_robot/status (工作台状态)

未来: 本节点的 robot.execute() 可以换成真实的机械臂驱动
(例如发布到 ROS2 的 /arm_joint_commands 话题), 上层代码不变。
"""

import json
import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

from ai_robot.robot import SimRobot

# 工位坐标 (Gazebo 世界坐标): 让仿真机器人物理开过去
STATION_COORDS = {
    "上料区": (0.0, -0.4),
    "检测区": (0.0, 0.5),
    "成品区": (0.0, 1.4),
}
DEFAULT_COORDS = (0.0, 0.5)  # 记忆中新学的位置默认开向中间


class RobotController(Node):
    """机器人控制器: 订阅动作 -> 执行 -> 发布状态"""

    def __init__(self):
        super().__init__("robot_controller")
        self.robot = SimRobot()
        self.sub = self.create_subscription(
            String, "/ai_robot/action", self.on_action, 10
        )
        self.pub_status = self.create_publisher(String, "/ai_robot/status", 10)
        # V4: 物理移动 (Gazebo 差速机器人)
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.pose = None          # (x, y, yaw)
        self.drive_target = None  # 当前要开往的目标坐标
        self.drive_timeout = 0    # 超时保护
        self._dbg_count = 0
        self.create_timer(0.1, self._drive_tick)
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
        # V4: 让仿真机器人开往目标工位
        if action.get("action") == "move":
            target = action.get("target", "")
            self._start_drive(target)
        state = {k: list(v) for k, v in self.robot.workspace.items()}
        self._publish_status("工作台: " + json.dumps(state, ensure_ascii=False))

    def _part_exists(self, obj):
        """判断零件是否在工作台或夹爪中"""
        if self.robot.gripper == obj or any(
            obj in parts for parts in self.robot.workspace.values()
        ):
            return True
        return False

    # ---------- V4: Gazebo 物理移动 ----------

    def on_odom(self, msg):
        """记录机器人当前位置 (来自差速驱动插件的里程计)"""
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        self.pose = (p.x, p.y, yaw)

    def _start_drive(self, station):
        """设置要开往的工位坐标"""
        if station in STATION_COORDS:
            self.drive_target = STATION_COORDS[station]
        else:
            self.drive_target = DEFAULT_COORDS
        self.drive_timeout = self.get_clock().now().nanoseconds + 45 * 1_000_000_000
        self.get_logger().info(f"开始开往: {station} {self.drive_target}")

    def _drive_tick(self):
        """10Hz 导航控制: 先转向目标方向, 再直行, 到达后停止"""
        if self.drive_target is None:
            return
        if self.pose is None:
            return  # 还没收到里程计, 等待
        if self.get_clock().now().nanoseconds > self.drive_timeout:
            self._stop_drive("导航超时, 已停止")
            return

        x, y, yaw = self.pose
        tx, ty = self.drive_target
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        desired_yaw = math.atan2(dy, dx)
        yaw_err = (desired_yaw - yaw + math.pi) % (2 * math.pi) - math.pi

        twist = Twist()
        if abs(yaw_err) > 0.10:
            # 先转向(带阻尼, 防止来回摆动)
            twist.angular.z = max(-0.8, min(0.8, yaw_err * 1.5))
        elif dist > 0.25:
            # 再直行(速度随距离减小, 保持最低速度避免爬行)
            twist.linear.x = max(0.15, min(0.45, dist * 0.9))
        else:
            self._stop_drive("已到达目标位置")
            return
        self._dbg_count += 1
        if self._dbg_count % 20 == 0:  # 每 2 秒打一条调试日志
            self.get_logger().info(
                f"[导航] pose=({x:.2f},{y:.2f}) yaw={yaw:.2f} "
                f"err={yaw_err:.2f} dist={dist:.2f} "
                f"twist=({twist.linear.x:.2f},{twist.angular.z:.2f})"
            )
        self.cmd_vel_pub.publish(twist)

    def _stop_drive(self, reason):
        """停止并清理导航状态"""
        self.cmd_vel_pub.publish(Twist())
        self.drive_target = None
        self.get_logger().info(reason)

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
