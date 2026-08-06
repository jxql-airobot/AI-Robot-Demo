# -*- coding: utf-8 -*-
"""RWSManager 与 RecoveryManager 集成的单元测试（Mock RWS 服务端）。"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from agent.recovery.manager import RecoveryManager
from agent.recovery.rws_manager import RWSManager


class MockRWSHandler(BaseHTTPRequestHandler):
    """模拟 RWS 服务端：状态查询 + set-entrypoint + resetpp + start。"""

    exec_state = "stopped"
    events = []

    def log_message(self, *args):  # 静默
        pass

    def do_GET(self):
        if "/rw/rapid/execution" in self.path:
            body = (
                '<html><body><div class="state">'
                f'<span class="ctrlexecstate">{self.exec_state}</span>'
                "</div></body></html>"
            )
            self._send(200, body.encode())
        elif "/rw/elog/0" in self.path:
            body = (
                '<html><body><div class="state"><ul>'
                '<li class="elog-message-li"><span class="code">10125</span>'
                '<span class="src-name">MC0</span>'
                '<span class="tstamp">2026-08-06 T 12:00:01</span></li>'
                '<li class="elog-message-li"><span class="code">10020</span>'
                '<span class="src-name">MC0</span>'
                '<span class="tstamp">2026-08-06 T 12:00:00</span></li>'
                '<li class="elog-message-li"><span class="code">50050</span>'
                '<span class="src-name">MC0</span>'
                '<span class="tstamp">2026-08-06 T 11:59:59</span></li>'
                "</ul></div></body></html>"
            )
            self._send(200, body.encode())
        else:
            self._send(404, b"not found")

    def do_POST(self):
        if "set-entrypoint" in self.path:
            self._send(204, b"")
        elif "action=resetpp" in self.path:
            self._send(204, b"")
        elif "action=start" in self.path:
            type(self).events.append("start")
            self.exec_state = "running"
            self._send(204, b"")
        elif "action=stop" in self.path:
            self.exec_state = "stopped"
            self._send(204, b"")
        else:
            self._send(404, b"not found")

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockUnavailableHandler(BaseHTTPRequestHandler):
    """模拟 RWS 未启用（/rw/ 全部 404）。"""

    def log_message(self, *args):
        pass

    def do_GET(self):
        self._send404()

    def do_POST(self):
        self._send404()

    def _send404(self):
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class MockBackend:
    """可注入 RecoveryManager 的假后端（记录 recover_error 调用）。"""

    def __init__(self):
        self.recover_calls = 0
        self.recoverable = True

    def recover_error(self, error_code=None):
        self.recover_calls += 1
        return {"recover": self.recoverable, "message": "backend recovered"}


def start_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def start_tcp_listener():
    """供 wait_for_socket 探测的 TCP 监听端口。"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    return s, s.getsockname()[1]


def test_check_connection_unavailable():
    server, port = start_server(MockUnavailableHandler)
    try:
        mgr = RWSManager(base_url=f"http://127.0.0.1:{port}")
        assert mgr.check_connection()["controller_available"] is False
        assert mgr.get_controller_state()["state"] == "unknown"
    finally:
        server.shutdown()


def test_state_parsing_running_and_error():
    server, port = start_server(MockRWSHandler)
    try:
        mgr = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        assert mgr.get_controller_state()["state"] == "stopped"
        # 带控制器错误状态块时，应解析为 error 并提取错误码
        body = (
            '<html><body><div class="status">'
            '<span class="code">50050</span></div>'
            '<div class="state"><span class="ctrlexecstate">stopped</span>'
            "</div></body></html>"
        )
        exec_state, error_code = RWSManager._parse_execution(body)
        assert exec_state == "stopped"
        assert error_code == "50050"
    finally:
        server.shutdown()


def test_get_controller_error_from_elog():
    server, port = start_server(MockRWSHandler)
    try:
        mgr = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        result = mgr.get_controller_error()
        # LIFO 顺序下应跳过 10125/10020，返回根因码 50050
        assert result["error_code"] == "50050"
        assert result["timestamp"] == "2026-08-06 T 11:59:59"
    finally:
        server.shutdown()


def test_recover_controller_success():
    MockRWSHandler.events.clear()
    server, port = start_server(MockRWSHandler)
    sock, sock_port = start_tcp_listener()
    try:
        mgr = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        result = mgr.recover_controller(
            {"error_code": "50050", "error_type": "execution"},
            port=sock_port,
            socket_timeout_seconds=5,
        )
        assert result["status"] == "success"
        assert result["controller_state_before"] == "stopped"
        assert result["recover_time"] >= 0
        assert result["socket_reconnect_time"] >= 0
        assert "start" in MockRWSHandler.events
        step_names = [s["step"] for s in result["steps"]]
        assert step_names == ["set_entry", "reset_pp", "start"]
    finally:
        server.shutdown()
        sock.close()


def test_recover_controller_safety_error_manual():
    server, port = start_server(MockRWSHandler)
    try:
        mgr = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        result = mgr.recover_controller(
            {"error_code": "50050", "error_message": "急停"})
        assert result["status"] == "need_manual"
        assert result["recoverable"] is False
    finally:
        server.shutdown()


def test_recovery_manager_uses_rws_when_available():
    server, port = start_server(MockRWSHandler)
    sock, sock_port = start_tcp_listener()
    try:
        backend = MockBackend()
        rws = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        # 避免 wait_for_socket 轮询真实 30000 端口：直接判定恢复成功
        with mock.patch.object(rws, "wait_for_socket", return_value=True):
            mgr = RecoveryManager(backend=backend, recoverer=rws)
            plan = mgr.recover({
                "error_code": "50050",
                "error_type": "execution",
                "error_message": "position_unreachable",
            })
        assert plan.get("recovery_source") == "rws"
        assert plan["status"] == "success"
        assert backend.recover_calls == 0
    finally:
        server.shutdown()
        sock.close()


def test_recovery_manager_fallback_when_rws_unavailable():
    server, port = start_server(MockUnavailableHandler)
    try:
        backend = MockBackend()
        rws = RWSManager(base_url=f"http://127.0.0.1:{port}", timeout=2.0)
        mgr = RecoveryManager(backend=backend, recoverer=rws)
        plan = mgr.recover({
            "error_code": "50050",
            "error_type": "execution",
        })
        # RWS 不可用 → 回退到 backend.recover_error，原流程不受影响
        assert plan["status"] == "success"
        assert plan.get("recovery_source") != "rws"
        assert backend.recover_calls == 1
    finally:
        server.shutdown()


def test_recovery_manager_without_recoverer_unchanged():
    backend = MockBackend()
    mgr = RecoveryManager(backend=backend)
    plan = mgr.recover({
        "error_code": "50050",
        "error_type": "execution",
    })
    assert plan["status"] == "success"
    assert backend.recover_calls == 1
