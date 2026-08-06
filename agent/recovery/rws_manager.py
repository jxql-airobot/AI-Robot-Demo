# -*- coding: utf-8 -*-
"""
rws_manager.py — 基于 RobotWebServices (RWS) 的控制器级自动恢复 (V6.7)
=====================================================================
设计目标：在 50050 等停止级异常导致 RAPID 程序停止后，通过控制器标准
Web 服务接口（RWS 1.0，IRC5 / RobotWare 6 支持）自动执行：

    错误产生
      ↓
    RWS 查询控制器状态（/rw/rapid/execution）
      ↓
    判断是否可恢复（RecoveryManager 错误分级）
      ↓
    RWS 清除错误状态（/rw/panel/actions?action=reset）
      ↓
    RWS 设置 PP 到 main（/rw/rapid/pp?action=setpp）
      ↓
    RWS 启动 RAPID 执行（/rw/rapid/execution?action=start）
      ↓
    轮询 30000 端口恢复 → Agent 重连继续任务

边界与安全：
- 本模块只对“可恢复异常”（Level 1/2）执行自动恢复，Level 3 安全相关
  异常（急停、安全保护）返回人工确认，绝不自动解除安全限制；
- 若虚拟控制器未启用 RWS（探测失败），recover() 返回
  status="rws_not_enabled"，保持现有“人工重启 + 自动重连”流程不变；
- 不修改现有 RecoveryManager：本模块作为可选的控制器级恢复器，由
  上层按需注入，旧流程保持向后兼容。

启用 RWS（一次性配置，RobotStudio 侧）：
    控制器 → 配置 → Communication → Firewall Manager →
    RobotWebServices → EnableOnPublicNet/EnableOnPrivateNet = Yes

RWS 默认地址：http://<控制器IP>（虚拟控制器通常为本机 127.0.0.1:80）。
"""

import socket
import time
import urllib.error
import urllib.request


class RWSManager:
    """基于 RWS REST API 的控制器状态查询与自动恢复器。

    参数:
        base_url: RWS 根地址，如 "http://127.0.0.1/rws"。
        username / password: RWS 认证（默认 "Default User" / "robotics"）。
        timeout: HTTP 请求超时（秒）。
    """

    def __init__(self, base_url="http://127.0.0.1/rws",
                 username="Default User", password="robotics",
                 timeout=3.0):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

    # ---------- 基础请求 ----------

    def _request(self, method, path, data=None):
        """发送 RWS 请求，返回 (status, body_text)；异常时返回 (None, err)。"""
        url = self.base_url + path
        req = urllib.request.Request(url, method=method, data=data)
        req.add_header("User-Agent", "ai-robot-demo-rws")
        if self.username:
            import base64
            token = base64.b64encode(
                f"{self.username}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read(2000).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(500).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    # ---------- 状态查询 ----------

    def probe(self):
        """探测 RWS 是否启用。RWS 启用时 /rw/ 系列接口返回 200/401。"""
        status, _ = self._request("GET", "/rw/rapid/execution")
        return status is not None and status != 404

    def get_controller_status(self):
        """查询 RAPID 执行状态与控制器错误状态。"""
        status, body = self._request("GET", "/rw/rapid/execution")
        if status is None or status == 404:
            return {
                "available": False,
                "reason": "rws_not_enabled",
                "detail": body,
            }
        return {
            "available": True,
            "http_status": status,
            "execution_state": body[:300],
        }

    # ---------- 恢复判定 ----------

    LEVEL2_CODES = {"50050", "50027", "50501", "10020", "40195",
                    "41595", "10125"}

    def is_recoverable(self, error):
        """按错误码判断是否允许自动恢复（与 RecoveryManager 分级一致）。

        Level 3 安全相关异常（急停、安全保护）一律不可自动恢复。
        """
        code = str(error.get("error_code") or "")
        text = str(error.get("error_message") or "") + str(
            error.get("raw_message") or "")
        if any(h in text for h in ("急停", "安全保护", "安全限位",
                                   "emergency", "safety_guard", "estop")):
            return False, "安全相关异常，禁止自动恢复"
        if code in self.LEVEL2_CODES:
            return True, f"停止级异常 {code}，可尝试 RWS 自动恢复"
        return True, "普通执行异常，直接重规划即可"

    # ---------- 恢复动作 ----------

    def reset_error(self):
        """RWS 清除控制器错误状态（等效于 FlexPendant 的 Reset）。"""
        return self._request("POST", "/rw/panel/actions?action=reset")

    def set_pp_to_main(self):
        """RWS 把程序指针设置到 main。"""
        data = b"pp=main"
        return self._request("POST", "/rw/rapid/pp?action=setpp", data=data)

    def start_execution(self):
        """RWS 启动 RAPID 执行（单次运行）。"""
        return self._request(
            "POST", "/rw/rapid/execution?action=start&cycle=once")

    def wait_for_socket(self, host="127.0.0.1", port=30000,
                        timeout_seconds=60):
        """轮询 TCP 端口，等待 SocketServer 恢复监听。"""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1.0):
                    return True
            except OSError:
                time.sleep(2)
        return False

    def recover(self, error, host="127.0.0.1", port=30000):
        """执行完整的 RWS 自动恢复流程。"""
        recoverable, reason = self.is_recoverable(error)
        if not recoverable:
            return {
                "recoverable": False,
                "action": "manual",
                "status": "need_manual",
                "reason": reason,
            }
        if not self.probe():
            return {
                "recoverable": True,
                "action": "rws",
                "status": "rws_not_enabled",
                "reason": "虚拟控制器未启用 RobotWebServices，"
                          "保持人工重启 + 自动重连流程",
            }
        steps = []
        for name, fn in (("reset", self.reset_error),
                         ("set_pp", self.set_pp_to_main),
                         ("start", self.start_execution)):
            status, body = fn()
            steps.append({"step": name, "http_status": status,
                          "detail": body[:120]})
            if status is None or status >= 400:
                return {
                    "recoverable": True,
                    "action": "rws",
                    "status": "failed",
                    "reason": f"RWS {name} 失败",
                    "steps": steps,
                }
        socket_ok = self.wait_for_socket(host, port)
        return {
            "recoverable": True,
            "action": "rws",
            "status": "success" if socket_ok else "socket_timeout",
            "reason": "RWS 已清除错误并重启 RAPID"
                      if socket_ok else "RWS 动作完成但端口未恢复",
            "steps": steps,
            "socket_ok": socket_ok,
        }


def build_rws_manager(base_url="http://127.0.0.1/rws"):
    """工厂函数：构造 RWSManager（可选注入 RecoveryManager 使用）。"""
    return RWSManager(base_url=base_url)
