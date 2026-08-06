# -*- coding: utf-8 -*-
"""
manager.py — RecoveryManager (V6.6)
====================================
针对工业机器人执行异常进行错误分级与恢复决策，接入闭环 Agent 的
Observation → Reflection → Recovery → Replanning 链路。

错误等级：
  Level 1 普通执行异常：自动修正并重新执行（重新规划）；
  Level 2 控制器停止级异常（50050/50027/41595 等）：尝试自动恢复
          （停止任务、重置 RAPID、恢复 Socket 监听、通知重新规划）；
  Level 3 安全相关异常（急停、安全保护触发）：禁止自动恢复，返回人工确认。

安全边界：本机制只针对可恢复异常执行恢复动作，不绕过机器人安全保护，
不自动解除安全限制。
"""


class ErrorLevel:
    LEVEL1 = 1  # 普通执行异常
    LEVEL2 = 2  # 控制器停止级异常
    LEVEL3 = 3  # 安全相关异常


# 控制器停止级错误码（来自真实 RobotStudio 事件）
LEVEL2_CODES = {
    "50050",  # 位置超出范围
    "50027",  # 关节超出范围
    "50501",  # 短距离运动
    "10020",  # 执行错误状态
    "40195",  # 限制错误
    "41595",  # 套接字错误
    "10125",  # 程序已停止
}

# 安全相关异常提示词（Level 3）
LEVEL3_HINTS = ("急停", "安全保护", "安全限位", "emergency", "safety_guard",
                "estop", "安全停止")


class RecoveryManager:
    """错误分级与恢复决策器

    参数:
        backend: 可选的机器人后端（用于执行恢复动作）；
        recoverer: 可选的控制器级恢复器（RWSManager）。Level 2 停止级
            异常时优先尝试 recoverer（如 RWS 自动恢复）；recoverer 不可用
            或恢复失败时回退到 backend.recover_error 的原有人工重启 +
            自动重连流程。
    """

    def __init__(self, backend=None, recoverer=None):
        self.backend = backend  # 可选的机器人后端（用于执行恢复动作）
        self.recoverer = recoverer  # 可选的 RWS 控制器级恢复器

    def classify(self, error):
        """把错误信息映射为错误等级（1/2/3）"""
        code = str(error.get("error_code") or "")
        text = str(error.get("error_message") or "") + str(
            error.get("raw_message") or ""
        )
        if code in LEVEL2_CODES:
            return ErrorLevel.LEVEL2
        if any(h in text for h in LEVEL3_HINTS):
            return ErrorLevel.LEVEL3
        return ErrorLevel.LEVEL1

    def analyze(self, error):
        """错误分级并给出恢复决策（不执行）"""
        level = self.classify(error)
        code = error.get("error_code")
        if level == ErrorLevel.LEVEL3:
            return {
                "recoverable": False,
                "action": "manual",
                "level": 3,
                "status": "need_manual",
                "reason": "安全相关异常，禁止自动恢复，需要人工确认",
            }
        if level == ErrorLevel.LEVEL2:
            return {
                "recoverable": True,
                "action": "restart_rapid",
                "level": 2,
                "status": "pending",
                "reason": f"控制器停止级错误 {code}，尝试自动恢复",
            }
        return {
            "recoverable": True,
            "action": "replan",
            "level": 1,
            "status": "pending",
            "reason": "普通执行异常，自动修正并重新执行",
        }

    def recover(self, error):
        """执行恢复决策：Level 2 优先 recoverer（RWS），否则 backend 恢复，
        Level 1 转重规划，Level 3 返回人工处理。"""
        plan = self.analyze(error)
        if plan["action"] == "restart_rapid":
            if self.recoverer is not None:
                try:
                    rws_result = self.recoverer.recover_controller(error)
                    if rws_result.get("status") == "success":
                        plan["status"] = "success"
                        plan["recovery_source"] = "rws"
                        plan["recovery_detail"] = (
                            rws_result.get("reason") or "RWS 自动恢复成功"
                        )
                        plan["rws_result"] = rws_result
                        return plan
                    # rws_not_enabled / failed / socket_timeout：记录后回退
                    plan["rws_result"] = rws_result
                except Exception as exc:  # noqa: BLE001
                    plan["rws_result"] = {"status": "error",
                                          "reason": f"RWS 调用异常: {exc}"}
            backend = self.backend
            if backend is not None and hasattr(backend, "recover_error"):
                try:
                    result = backend.recover_error(error.get("error_code"))
                    plan["status"] = (
                        "success" if result.get("recover") else "failed"
                    )
                    plan["recovery_detail"] = result.get("message", "")
                except Exception as exc:
                    plan["status"] = "failed"
                    plan["recovery_detail"] = f"恢复动作异常: {exc}"
            else:
                plan["status"] = "skipped"
                plan["recovery_detail"] = "后端不支持自动恢复，转重规划"
        elif plan["action"] == "replan":
            plan["status"] = "replanned"
        return plan
