from glob import glob
import os

from setuptools import setup

package_name = "ai_robot"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "models"), glob("models/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="zlx06",
    maintainer_email="zlx06@example.com",
    description="AI Robot Demo V3: ROS2 robot framework",
    license="MIT",
    entry_points={
        "console_scripts": [
            "brain_node = ai_robot.brain_node:main",
            "robot_controller = ai_robot.robot_controller:main",
            "task_cli = ai_robot.task_cli:main",
            "vision_node = ai_robot.vision_node:main",
        ],
    },
)
