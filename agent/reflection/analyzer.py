# -*- coding: utf-8 -*-
"""
analyzer.py — ReflectionAnalyzer (V6.4 闭环 Agent)
===================================================
分析原始任务、当前计划、动作结果与 Observation，输出：
    {
      "task_completed": bool,
      "need_replan": bool,
      "reason": str,
      "error_type": "action_param" | "execution" | "communication" | "unknown",
    }

判断规则为确定性规则（不依赖 LLM），保证可复现、可测试：
  - 全部步骤成功 → 任务完成；
  - 存在失败步骤 → 提取失败原因并分类，建议重新规划。
"""

PARAM_HINTS = ("参数", "超出范围", "超范围", "非法", "不支持", "无法解析", "未知工位")
COMM_HINTS = ("连接", "超时", "socket", "Socket", "通信", "重连")


class ReflectionAnalyzer:
    """执行结果反思器"""

    def analyze(self, task, plan=None, step_results=None, observation=None):
        """判断任务完成情况与是否需要重规划。

        参数:
            task: 原始任务文本
            plan: 当前计划（dict，可空）
            step_results: 执行器步骤结果列表
            observation: ObservationManager 输出的 Observation dict
        """
        step_results = step_results or []
        observation = observation or {}
        failed = [r for r in step_results if not r.get("ok")]

        if observation.get("success") and not failed:
            return {
                "task_completed": True,
                "need_replan": False,
                "reason": "",
                "error_type": "none",
            }

        reason, error_type = self._diagnose(failed, observation)
        return {
            "task_completed": False,
            "need_replan": True,
            "reason": reason,
            "error_type": error_type,
        }

    @staticmethod
    def _map_rapid_code(error_code):
        """把 RobotStudio RAPID 错误码映射为 (原因, 错误类型)"""
        mapping = {
            "50050": ("robot_unreachable", "execution"),
            "50027": ("joint_out_of_range", "execution"),
            "50501": ("short_distance", "execution"),
            "10020": ("execution_error_state", "execution"),
            "40195": ("limit_error", "execution"),
            "41595": ("socket_error", "communication"),
        }
        if error_code and error_code in mapping:
            return mapping[error_code]
        if error_code:
            return ("motion_failed", "execution")
        return None, None

    @classmethod
    def _diagnose(cls, failed, observation):
        """从失败步骤与 Observation 中提取失败原因并分类"""
        # 1) 优先使用结构化错误码（真实机器人错误）
        error_code = observation.get("error_code")
        code_reason, code_type = cls._map_rapid_code(error_code)
        if code_reason:
            return f"[RobotStudio] {code_reason} (error {error_code})", code_type

        for r in failed:
            result = r.get("result")
            structured = result.get("error") if isinstance(result, dict) else None
            if isinstance(structured, dict) and structured.get("code"):
                reason, etype = cls._map_rapid_code(str(structured["code"]))
                if reason:
                    return (
                        f"[RobotStudio] {reason} (error {structured['code']})",
                        etype,
                    )

        error_type = "unknown"
        reason_parts = []
        for r in failed:
            tool = r.get("tool", "")
            message = r.get("message") or ""
            if message:
                reason_parts.append(f"[{tool}] {message}")
            text = f"{message} {r.get('result') or ''}"
            if any(h in text for h in COMM_HINTS):
                error_type = "communication"
            elif any(h in text for h in PARAM_HINTS):
                error_type = "action_param"
            else:
                error_type = "execution"

        obs_error = observation.get("error")
        if obs_error and any(h in str(obs_error) for h in COMM_HINTS):
            error_type = "communication"
        elif obs_error and any(h in str(obs_error) for h in PARAM_HINTS):
            error_type = "action_param"

        if not reason_parts and obs_error:
            reason_parts.append(str(obs_error))
        reason = "；".join(reason_parts) if reason_parts else "任务执行失败"
        return reason, error_type
