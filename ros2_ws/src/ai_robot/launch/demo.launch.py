from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """一键启动: AI 大脑 + 机器人控制器"""
    return LaunchDescription(
        [
            Node(
                package="ai_robot",
                executable="robot_controller",
                name="robot_controller",
                output="screen",
            ),
            Node(
                package="ai_robot",
                executable="brain_node",
                name="ai_brain",
                output="screen",
            ),
        ]
    )
