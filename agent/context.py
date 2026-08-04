# -*- coding: utf-8 -*-
"""
context.py — Agent 会话上下文 (V5.2)
====================================
维护多轮对话历史、上一计划/结果、当前工作台状态，并做简单的指代消解。
"""


class AgentContext:
    """Agent 会话状态"""

    def __init__(self, max_history=10):
        self.max_history = max_history
        self.history = []        # [{"role": "user"/"agent", "content": str}]
        self.last_plan = None    # 上一个 Plan
        self.last_summary = None  # 上一轮结果汇总文本
        self.current_state = None  # 当前工作台状态文本
        self.last_object = None  # 上一个操作对象（指代消解用）

    def update_task(self, task):
        """记录用户任务"""
        self.history.append({"role": "user", "content": task})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def update_result(self, plan, summary, current_state):
        """记录本轮计划、结果与当前状态"""
        self.last_plan = plan
        self.last_summary = summary
        if current_state:
            self.current_state = current_state
        self.history.append({"role": "agent", "content": summary})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        # 从本轮 Plan 中提取操作对象（指代消解用）
        for step in plan.get("steps", []):
            obj = step.get("args", {}).get("object")
            if obj:
                self.last_object = obj

    def resolve_reference(self, task):
        """把 '它/那个零件' 等指代替换成上一个操作对象"""
        if not self.last_object:
            return task
        for word in ("它", "那个零件", "这个零件", "该零件", "这个东西"):
            if word in task:
                task = task.replace(word, self.last_object)
        return task

    def format_for_planner(self):
        """把会话上下文格式化成给规划器的文本"""
        lines = ["近期对话："]
        for h in self.history[-6:]:
            lines.append(f"- {h['role']}: {h['content']}")
        if self.current_state:
            lines.append(f"当前状态：{self.current_state}")
        return "\n".join(lines)
