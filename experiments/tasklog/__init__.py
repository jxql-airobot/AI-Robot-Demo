# -*- coding: utf-8 -*-
"""统一实验日志系统 (V6.2)"""

__all__ = ["TaskLogger", "clear_runtime_log"]


def __getattr__(name):
    """惰性导入，避免 `python -m` 时重复导入告警"""
    if name in __all__:
        from experiments.tasklog.task_logger import clear_runtime_log, TaskLogger

        return {"TaskLogger": TaskLogger, "clear_runtime_log": clear_runtime_log}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
