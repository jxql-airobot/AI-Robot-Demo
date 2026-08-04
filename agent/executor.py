# -*- coding: utf-8 -*-
"""
executor.py — Plan 执行器 (V5.2)
================================
按步骤依次调用工具，收集每步结果；某步失败时默认停止。
"""


class PlanExecutor:
    """计划执行器"""

    def __init__(self, registry, stop_on_error=True):
        self.registry = registry
        self.stop_on_error = stop_on_error

    def execute(self, plan):
        """执行 Plan 的所有步骤，返回结果列表"""
        results = []
        for index, step in enumerate(plan.get("steps", []), 1):
            tool_name = step.get("tool")
            tool = self.registry.get(tool_name)
            if tool is None:
                results.append(
                    {
                        "step": index,
                        "tool": tool_name,
                        "purpose": step.get("purpose", ""),
                        "ok": False,
                        "message": f"未知工具: {tool_name}",
                        "result": None,
                    }
                )
                if self.stop_on_error:
                    break
                continue
            try:
                out = tool.run(step.get("args", {}))
            except Exception as exc:
                out = {"ok": False, "message": f"工具异常: {exc}"}
            results.append(
                {
                    "step": index,
                    "tool": tool_name,
                    "purpose": step.get("purpose", ""),
                    "ok": out.get("ok", False),
                    "message": out.get("message", ""),
                    "result": out.get("result"),
                }
            )
            if not out.get("ok", False) and self.stop_on_error:
                break
        return results
