# -*- coding: utf-8 -*-
"""
base.py — 工具接口 (V5.2)
=========================
所有 Agent 工具统一实现 BaseTool 接口。
"""


class BaseTool:
    """工具基类：name / description / run(args) -> dict"""

    name = "base"
    description = ""

    def run(self, args):
        """执行工具。args 为 dict，返回 {"ok": bool, "result": ..., "message": str}"""
        raise NotImplementedError
