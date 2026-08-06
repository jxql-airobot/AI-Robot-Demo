# -*- coding: utf-8 -*-
"""
rws_manager.py - 基于 RobotWebServices (RWS) 的控制器级自动恢复 (V6.8)
=====================================================================
在 50050 等停止级异常导致 RAPID 程序停止后，通过控制器标准 Web 服务
接口（RWS 1.0，IRC5 / RobotWare 6 支持）自动执行：

    错误产生
      ↓
    RWS 查询控制器状态（GET /rw/rapid/execution）
      ↓
    判断是否可恢复（RecoveryManager 错误分级）
      ↓
    RWS 设置任务入口（set-entrypoint，本系统入口为 socket_main）
      ↓
    RWS 重置程序指针（action=resetpp）
      ↓
    RWS 启动 RAPID（action=start）
      ↓
    轮询 30000 端口等待 SocketServer 恢复
      ↓
    Agent 重连继续任务

真实端点说明（RobotWare 6.08 实测确认）：
  - RWS 根地址为 http://<控制器 IP>（80 端口，无 /rws 前缀）；
  - 认证方式为 HTTP Digest（默认账号 "Default User" / "robotics"）；
  - 任务入口须与模块实际入口一致（本系统为 socket_server.socket_main），
    否则 resetpp 会因找不到符号 main 返回 SYS_CTRL_E_NO_SUCH_SYMBOL；
  - POST 表单请求必须携带 Content-Type: application/x-www-form-urlencoded。

边界与安全：
- 本模块只对"可恢复异常"（Level 1/2）执行自动恢复，Level 3 安全相关
  异常（急停、安全保护）返回人工确认，绝不自动解除安全限制；
- 若虚拟控制器未启用 RWS（探测失败），recover() 返回
  status="rws_not_enabled"，保持现有"人工重启 + 自动重连"流程不变；
- 不修改现有 RecoveryManager：本模块作为可选的控制器级恢复器，
  由上层按需注入，旧流程保持向后兼容。
"""

import re
import socket
import time

import requests
from requests.auth import HTTPDigestAuth


class RWSManager:
    """基于 RWS REST API 的控制器状态查询与自动恢复器。

    参数:
        base_url: RWS 根地址，默认 "http://127.0.0.1"（80 端口，无 /rws 前缀）；
        username / password: RWS 认证（默认 "Default User" / "robotics"）；
        timeout: HTTP 请求超时（秒）；
        task: RAPID 任务名（默认 T_ROB1）；
        entry_routine: 任务入口例程（默认 socket_main）。
    """

    def __init__(self, base_url="http://127.0.0.1",
                 username="Default User", password="robotics",
                 timeout=3.0, task="T_ROB1", entry_routine="socket_main"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.task = task
        self.entry_routine = entry_routine
        self._auth = HTTPDigestAuth(username, password)
        # 复用同一个 HTTP 会话：RWS 通过 ABBCX cookie 维持会话，
        # 每次新建连接都会占用控制器会话槽（上限约 70），
        # 持久 Session 可避免会话泄漏导致 RWS 拒绝服务。
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ai-robot-demo-rws"})

    # ---------- 基础请求 ----------

    def _request(self, method, path, data=None):
        """发送 RWS 请求（HTTP Digest 认证），返回 (status, body_text)。
        网络异常时返回 (None, err)。"""
        url = self.base_url + path
        headers = {"User-Agent": "ai-robot-demo-rws"}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            resp = self._session.request(
                method, url, auth=self._auth, data=data,
                headers=headers, timeout=self.timeout)
            return resp.status_code, resp.text
        except requests.exceptions.RequestException as exc:
            return None, f"{type(exc).__name__}: {exc}"

    def logout(self):
        """注销当前 RWS 会话，释放控制器会话槽（失败静默）。"""
        try:
            self._session.post(self.base_url + "/logout",
                               auth=self._auth, timeout=self.timeout)
        except requests.exceptions.RequestException:
            pass

    # ---------- 状态查询 ----------

    def check_connection(self):
        """连接测试：探测 RWS 是否可达且已启用。
        返回: {"controller_available": bool, "detail": str}
        """
        status, body = self._request("GET", "/rw/rapid/execution")
        if status is None:
            return {"controller_available": False,
                    "detail": f"RWS 不可达: {body}"}
        if status == 404:
            return {"controller_available": False,
                    "detail": "RWS 未启用（/rw/ 返回 404），请先在 RobotStudio "
                              "Firewall Manager 中启用 RobotWebServices"}
        if status == 401:
            return {"controller_available": False,
                    "detail": "RWS 认证失败（HTTP 401），请检查用户名/密码"}
        if status != 200:
            return {"controller_available": False,
                    "detail": f"RWS 响应异常（HTTP {status}）"}
        return {"controller_available": True,
                "detail": f"RWS 可达（HTTP {status}）"}

    def probe(self):
        """兼容旧接口：探测 RWS 是否启用。"""
        return self.check_connection()["controller_available"]

    @staticmethod
    def _parse_execution(body):
        """解析 /rw/rapid/execution 响应。
        返回: (exec_state, error_code)
            exec_state: running / stopped / unknown
            error_code: 控制器错误码；无错误时为空字符串。
        """
        exec_state = "unknown"
        m = re.search(r'class="ctrlexecstate">([^<]+)<', body or "")
        if m:
            exec_state = m.group(1).strip().lower()
        error_code = ""
        status_div = re.search(r'<div class="status">(.*?)</div>',
                               body or "", re.DOTALL)
        if status_div:
            cm = re.search(r'<span class="code">([^<]*)</span>',
                           status_div.group(1))
            if cm and cm.group(1).strip() not in ("", "0"):
                error_code = cm.group(1).strip()
        return exec_state, error_code

    def get_controller_state(self):
        """查询控制器 RAPID 执行状态。
        返回: {"state": "running"|"stopped"|"error"|"unknown",
               "error_code": str, "raw": 原始响应}
        """
        status, body = self._request("GET", "/rw/rapid/execution")
        if status is None or status != 200:
            return {"state": "unknown", "error_code": "",
                    "raw": f"RWS 不可用(http={status}): {body[:120]}"}
        exec_state, error_code = self._parse_execution(body)
        if error_code:
            state = "error"
        else:
            state = exec_state if exec_state in ("running", "stopped") \
                else "unknown"
        return {"state": state, "error_code": error_code,
                "raw": body[:300]}

    def get_controller_status(self):
        """查询 RAPID 执行状态与控制器错误状态。"""
        st = self.get_controller_state()
        return {"available": st["state"] != "unknown",
                "execution_state": st["state"],
                "error_code": st["error_code"],
                "detail": st["raw"]}

    # ---------- 恢复判定 ----------

    LEVEL2_CODES = {"50050", "50027", "50501", "10020", "40195",
                    "41595", "10125"}

    def is_recoverable(self, error):
        """按错误码判断是否允许自动恢复（与 RecoveryManager 分级一致）。
        Level 3 安全相关异常（急停、安全保护）一律不可自动恢复。"""
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

    def request_mastership(self):
        """请求 RWS mastership（部分操作要求；失败不阻塞后续步骤）。"""
        return self._request("POST", "/rw/mastership?action=request")

    def release_mastership(self):
        """释放 RWS mastership。"""
        return self._request("POST", "/rw/mastership?action=release")

    def set_entry_point(self, routine=None):
        """设置 RAPID 任务入口例程（本系统为 socket_main）。
        入口与模块实际入口一致后，resetpp 才能正确定位程序指针。"""
        routine = routine or self.entry_routine
        return self._request(
            "POST",
            f"/rw/rapid/tasks/{self.task}/program?action=set-entrypoint",
            data=f"routine={routine}")

    def reset_pp_to_main(self):
        """RWS 重置程序指针到任务入口（action=resetpp）。"""
        return self._request("POST", "/rw/rapid/execution?action=resetpp")

    def start_execution(self):
        """RWS 启动 RAPID 执行（单任务连续运行）。"""
        data = ("regain=continue&execmode=continue&cycle=forever"
                "&condition=none&stopatbp=disabled&alltaskbytsp=false")
        return self._request(
            "POST", "/rw/rapid/execution?action=start", data=data)

    def stop_execution(self):
        """RWS 停止 RAPID 执行（用于规范化执行状态）。"""
        return self._request(
            "POST", "/rw/rapid/execution?action=stop", data="stopmode=stop")

    # 兼容旧接口：RWS 1.0 没有独立的"清除错误"端点，
    # 错误清除等价于 resetpp + start 序列。
    def reset_error(self):
        return self.reset_pp_to_main()

    def set_pp_to_main(self):
        return self.reset_pp_to_main()

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
        """兼容旧接口：执行完整 RWS 自动恢复流程。"""
        return self.recover_controller(error, host=host, port=port)

    def recover_controller(self, error, host="127.0.0.1", port=30000,
                           socket_timeout_seconds=60):
        """错误恢复：状态检查 → 设置入口 → resetpp → start → 等 Socket 恢复。
        返回:
            {
                "controller_state_before": str,
                "recoverable": bool,
                "status": "success"|"rws_not_enabled"|"failed"
                          |"socket_timeout"|"need_manual",
                "recover_time": 秒,
                "socket_reconnect_time": 秒,
                "steps": [...],
                "reason": str,
                "socket_ok": bool,
            }
        """
        recoverable, reason = self.is_recoverable(error)
        if not recoverable:
            return {
                "recoverable": False,
                "action": "manual",
                "status": "need_manual",
                "reason": reason,
            }
        conn = self.check_connection()
        if not conn["controller_available"]:
            return {
                "recoverable": True,
                "action": "rws",
                "status": "rws_not_enabled",
                "controller_state_before": "unknown",
                "recover_time": 0.0,
                "socket_reconnect_time": 0.0,
                "reason": conn["detail"] + "；保持人工重启 + 自动重连流程",
                "steps": [],
            }
        state_before = self.get_controller_state()["state"]
        t0 = time.monotonic()
        steps = []

        # 1) 设置任务入口（失败不致命，resetpp 若已可定位则跳过）
        st, body = self.set_entry_point()
        steps.append({"step": "set_entry", "http_status": st,
                      "detail": body[:120]})

        # 2) 重置程序指针到入口
        st, body = self.reset_pp_to_main()
        steps.append({"step": "reset_pp", "http_status": st,
                      "detail": body[:120]})
        if st is None or st >= 400:
            return {
                "recoverable": True,
                "action": "rws",
                "status": "failed",
                "controller_state_before": state_before,
                "recover_time": round(time.monotonic() - t0, 3),
                "socket_reconnect_time": 0.0,
                "reason": f"RWS reset_pp 失败(HTTP {st})",
                "steps": steps,
            }

        # 3) 启动 RAPID 执行
        st, body = self.start_execution()
        steps.append({"step": "start", "http_status": st,
                      "detail": body[:120]})
        if st is None or st >= 400:
            return {
                "recoverable": True,
                "action": "rws",
                "status": "failed",
                "controller_state_before": state_before,
                "recover_time": round(time.monotonic() - t0, 3),
                "socket_reconnect_time": 0.0,
                "reason": f"RWS start 失败(HTTP {st})",
                "steps": steps,
            }

        t_recover = round(time.monotonic() - t0, 3)
        t_sock0 = time.monotonic()
        socket_ok = self.wait_for_socket(host, port, socket_timeout_seconds)
        t_sock = round(time.monotonic() - t_sock0, 3)
        return {
            "recoverable": True,
            "action": "rws",
            "status": "success" if socket_ok else "socket_timeout",
            "controller_state_before": state_before,
            "recover_time": t_recover,
            "socket_reconnect_time": t_sock,
            "reason": ("RWS 已重置程序指针并重启 RAPID，"
                       "SocketServer 恢复监听"
                       if socket_ok
                       else "RWS 动作完成但端口未恢复"),
            "steps": steps,
            "socket_ok": socket_ok,
        }


def build_rws_manager(base_url="http://127.0.0.1"):
    """工厂函数：构造 RWSManager（可选注入 RecoveryManager 使用）。"""
    return RWSManager(base_url=base_url)
