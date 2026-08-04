# -*- coding: utf-8 -*-
"""
config.py — GUI 全局配置 (V5.1)
===============================
集中管理路径和话题名，避免散落在各文件里。
"""

import os

# 项目根目录（gui 的上一级）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 记忆数据库路径：
#   ROS2 模式 -> WSL 工作区里的库（brain_node / vision_node 实际使用的）
#   本地模式 -> Windows 仓库根目录的库
ROS2_DB_PATH = os.path.expanduser("~/ros2_ws/database.db")
LOCAL_DB_PATH = os.path.join(REPO_ROOT, "database.db")


def resolve_gui_db_path():
    """按运行环境选择 GUI 记忆库。

    - WSL（存在 ~/ros2_ws 目录）：使用 ROS2 工作区库（与 brain_node /
      vision_node 一致）；
    - Windows（无 ~/ros2_ws）：回退到仓库根目录的本地库，避免
      “unable to open database file”。
    """
    if os.path.isdir(os.path.expanduser("~/ros2_ws")):
        return ROS2_DB_PATH
    return LOCAL_DB_PATH

# ROS2 话题（与 V3/V4 现有节点完全一致，只做客户端，不修改节点）
TOPIC_TASK = "/ai_robot/task"        # 用户任务（String）-> ai_brain
TOPIC_ACTION = "/ai_robot/action"    # JSON 动作（String）-> robot_controller
TOPIC_STATUS = "/ai_robot/status"    # 状态反馈（String）<- robot_controller
TOPIC_VISION = "/ai_robot/vision"    # 视觉识别结果（String JSON）<- vision_node
TOPIC_ODOM = "/odom"                 # 里程计（Odometry）<- Gazebo 差速驱动

# GUI 节点名
GUI_NODE_NAME = "gui_client"

# 发送任务后等待状态反馈的静默判定时间（秒），与 task_cli 的行为一致
STATUS_QUIET_SECONDS = 1.5
STATUS_WAIT_TIMEOUT_SECONDS = 20.0
