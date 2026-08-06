# -*- coding: utf-8 -*-
"""
manager.py — ObservationManager (V6.4 闭环 Agent)
==================================================
在执行器完成一轮步骤后，收集执行结果与机器人状态，输出统一的观察
（Observation）JSON，供 Reflection 模块分析。

统一格式：
    {
      "success": bool,
      "status": "completed" | "failed",
      "robot_state": {...},
      "error": str | None,
      "need_replan": bool,
      "timestamp": "ISO 时间",
    }

不直接绑定具体机器人后端：机器人状态从各后端统一的
{ok, success, error, stage, workspace, joints} 返回格式中提取。
"""

import datetime


class ObservationManager:
    """执行结果 → 统一 Observation"""

    def get_observation(self, plan=None, step_results=None, robot_state=None):
        """根据一轮执行结果生成 Observation。

        参数:
            plan: 当前计划（dict，可空）
            step_results: 执行器返回的步骤结果列表
            robot_state: 可选的机器人状态 dict（workspace/joints 等）
        """
        step_results = step_results or []
        failed = [
            r for r in step_results if not r.get("ok")
        ]
        success = len(step_results) > 0 and len(failed) == 0
        error = None
        error_code = None
        error_source = None
        raw_message = None
        if failed:
            first = failed[0]
            error = first.get("message") or f"步骤 {first.get('step')} 执行失败"
            # 结构化错误（RobotStudio 运动错误等）：result.error 为 dict
            result = first.get("result")
            structured = result.get("error") if isinstance(result, dict) else None
            if isinstance(structured, dict):
                error_code = structured.get("code")
                raw_message = structured.get("raw_message") or error
                stage = structured.get("stage") or (result or {}).get("stage")
                error_source = (
                    "RobotStudio"
                    if stage == "motion" or (raw_message or "").find("RAPID") >= 0
                    else "backend"
                )
            else:
                raw_message = error
                error_source = "backend"
        status = "completed" if success else "failed"
        return {
            "success": success,
            "status": status,
            "robot_state": robot_state or self._extract_robot_state(step_results),
            "error": error,
            "error_code": error_code,
            "error_source": error_source,
            "raw_message": raw_message,
            "need_replan": not success,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def _extract_robot_state(step_results):
        """从步骤结果中提取最后一份 workspace/joints 作为机器人状态快照"""
        for r in reversed(step_results):
            result = r.get("result")
            if isinstance(result, dict):
                state = {}
                if result.get("workspace") is not None:
                    state["workspace"] = result["workspace"]
                if result.get("joints") is not None:
                    state["joints"] = result["joints"]
                if result.get("gripper") is not None:
                    state["gripper"] = result["gripper"]
                if state:
                    return state
        return {}
