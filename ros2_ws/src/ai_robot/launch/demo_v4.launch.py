import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory("ai_robot")
    gazebo_share = get_package_share_directory("gazebo_ros")

    robot_urdf = os.path.join(pkg_share, "models", "ai_robot.urdf")

    # 零件: 模型名 -> (标签, x, y)
    parts = {
        "red_part": (0.0, -0.4),
        "blue_part": (0.0, 0.5),
        "green_part": (0.0, 1.4),
    }

    gui = LaunchConfiguration("gui", default="true")

    actions = [
        DeclareLaunchArgument("gui", default_value="true"),
        # 1. 启动 Gazebo
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(gazebo_share, "launch", "gazebo.launch.py")
            ),
            launch_arguments={"gui": gui}.items(),
        ),
        # 2. 发布机器人模型 (URDF -> robot_description)
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            parameters=[{"robot_description": open(robot_urdf).read()}],
            output="screen",
        ),
        # 3. 把机器人放进 Gazebo
        Node(
            package="gazebo_ros",
            executable="spawn_entity.py",
            arguments=[
                "-topic", "robot_description",
                "-entity", "ai_robot",
                "-x", "0", "-y", "0", "-z", "0.15",
            ],
            output="screen",
        ),
    ]

    # 4. 放 3 个彩色零件
    for name, (x, y) in parts.items():
        actions.append(
            Node(
                package="gazebo_ros",
                executable="spawn_entity.py",
                arguments=[
                    "-file", os.path.join(pkg_share, "models", f"{name}.sdf"),
                    "-entity", name,
                    "-x", str(x), "-y", str(y), "-z", "0",
                ],
                output="screen",
            )
        )

    # 5. AI 大脑 + 机器人控制器 + 视觉节点
    actions += [
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
        Node(
            package="ai_robot",
            executable="vision_node",
            name="vision_node",
            output="screen",
        ),
    ]

    return LaunchDescription(actions)
