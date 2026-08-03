# -*- coding: utf-8 -*-
"""
robot.py — 模拟机器人
======================
目前是一个"仿真器": 用字典记录零件在工位上的位置，
并模拟机械臂的移动、抓取、放置动作。

未来升级: 本模块会被 ROS2 机器人控制程序替代，
只要保持 execute(action) 接口不变，上层代码无需改动。

动作指令格式(JSON):
    {"action": "move", "object": "红色零件", "target": "检测区"}
    {"action": "pick", "object": "红色零件"}
    {"action": "place", "target": "成品区"}
    {"action": "scan"}
    {"action": "status"}
"""

# 工作台布局: 工位 -> 该工位上摆放的零件
INITIAL_WORKSPACE = {
    "上料区": ["红色零件", "蓝色零件", "绿色零件"],
    "检测区": [],
    "成品区": [],
}


class SimRobot:
    """模拟机器人: 机械臂 + 夹爪 + 工作台状态"""

    def __init__(self):
        # 每个工位上摆放的零件(用列表表示)
        self.workspace = {k: list(v) for k, v in INITIAL_WORKSPACE.items()}
        # 机械臂当前所在工位
        self.arm_position = "上料区"
        # 机械臂夹爪当前抓取的零件(None 表示空夹爪)
        self.gripper = None

    # ---------- 基础动作 ----------

    def _move_arm(self, station):
        """移动机械臂到指定工位"""
        if station not in self.workspace:
            raise ValueError(
                f"未知工位: {station}，可用工位: {list(self.workspace)}"
            )
        print(f"  [机械臂] 移动到 {station}")
        self.arm_position = station

    def _pick(self, part):
        """在当前工位抓取零件"""
        if self.gripper is not None:
            raise ValueError(f"夹爪已抓取 {self.gripper}，请先放置")
        if part not in self.workspace[self.arm_position]:
            raise ValueError(
                f"{self.arm_position} 上没有 {part}，"
                f"当前零件: {self.workspace[self.arm_position]}"
            )
        self.workspace[self.arm_position].remove(part)
        self.gripper = part
        print(f"  [机械臂] 抓取 {part}")

    def _place(self, station):
        """把夹爪中的零件放到指定工位"""
        if self.gripper is None:
            raise ValueError("夹爪为空，没有零件可放置")
        self._move_arm(station)
        self.workspace[station].append(self.gripper)
        print(f"  [机械臂] 放置 {self.gripper} 到 {station}")
        self.gripper = None

    # ---------- 对外动作接口(与未来 ROS2 控制接口对齐) ----------

    def execute(self, action):
        """执行一条 JSON 动作指令(模拟机器人控制)"""
        act = action.get("action")
        try:
            if act == "move":
                # 一步到位: 查找零件 -> 移动 -> 抓取 -> 移动 -> 放置
                part = action["object"]
                target = action["target"]
                src = self._find_part(part)
                self._move_arm(src)
                self._pick(part)
                self._place(target)
                print(f"  完成: {part} 已从 {src} 移动到 {target}")
            elif act == "pick":
                self._move_arm(self._find_part(action["object"]))
                self._pick(action["object"])
            elif act == "place":
                self._place(action.get("target"))
            elif act == "scan":
                self._scan()
            elif act == "status":
                self._scan()
            elif act == "error":
                print(f"  无法执行: {action.get('message', '未知错误')}")
            else:
                print(f"  不支持的指令: {act}")
        except (KeyError, ValueError) as exc:
            print(f"  执行失败: {exc}")

    # ---------- 辅助方法 ----------

    def _find_part(self, part):
        """返回零件所在的工位"""
        for station, parts in self.workspace.items():
            if part in parts:
                return station
        if self.gripper == part:
            return self.arm_position
        raise ValueError(f"工作台找不到零件: {part}")

    def _scan(self):
        """扫描工作台，报告各工位零件分布与机械臂状态"""
        print("  [扫描] 当前工作台状态:")
        for station, parts in self.workspace.items():
            text = "、".join(parts) if parts else "(空)"
            print(f"    {station}: {text}")
        print(f"    机械臂位置: {self.arm_position}，夹爪: {self.gripper or '(空)'}")
